# Real-Time Inventory Reservation System

A high-throughput flash-sale backend built with **FastAPI**, **PostgreSQL**, **Redis**, and **Docker** — designed to handle thousands of concurrent reservation requests without overselling.

---

## High-Level Architecture

```
                         ┌──────────────────────────────────────────┐
                         │             CLIENTS (Browser / App)       │
                         └──────────────────┬───────────────────────┘
                                            │  POST /reservations
                                            ▼
                         ┌──────────────────────────────────────────┐
                         │            FastAPI  (uvicorn × 4)        │
                         │                                          │
                         │  ① Redis DECRBY stock:{product_id}       │
                         │     → Atomic, in-memory, single-threaded │
                         │     → If result < 0 → 409 Insufficient   │
                         │                                          │
                         │  ② Postgres UPDATE products               │
                         │     SET available_inventory = avail - qty │
                         │     WHERE available_inventory >= qty      │
                         │     → Belt-and-suspenders DB guard        │
                         │                                          │
                         │  ③ INSERT reservation (status=reserved)   │
                         │     expires_at = now + 5 min              │
                         │                                          │
                         │  ④ ZADD reservations:expiry               │
                         │     score = expires_at timestamp          │
                         └──────────┬────────────────┬──────────────┘
                                    │                │
                         ┌──────────▼──┐      ┌──────▼──────────────┐
                         │  PostgreSQL  │      │       Redis         │
                         │  (Source of  │      │  • stock:{pid}      │
                         │   Truth)     │      │  • reservations:    │
                         │              │      │    expiry  (ZSET)   │
                         └──────────────┘      └─────────┬──────────┘
                                                         │
                         ┌───────────────────────────────▼──────────┐
                         │         Background Worker (asyncio)       │
                         │                                           │
                         │  Expiration Loop (every 2s):              │
                         │    ZRANGEBYSCORE(-inf, now) → expired IDs │
                         │    For each:                              │
                         │      • UPDATE reservation → 'expired'     │
                         │      • Restore available_inventory (PG)   │
                         │      • INCRBY stock:{pid} (Redis)         │
                         │                                           │
                         │  Stock Sync Loop (every 60s):             │
                         │    Re-seed Redis counters from Postgres   │
                         └───────────────────────────────────────────┘
```

### Request Flow: `POST /reservations`

1. **JWT validation** – the `Authorization: Bearer <token>` header is decoded; the user ID is extracted.
2. **Redis fast-path** – `DECRBY stock:{product_id} quantity`. Redis is single-threaded so this is atomic. If the new value is `< 0`, immediately rollback (`INCRBY`) and return **409 Insufficient Stock**. This rejects the vast majority of late-comers in **microseconds** without touching Postgres.
3. **Postgres slow-path** – `UPDATE products SET available_inventory = available_inventory - :qty WHERE id = :pid AND available_inventory >= :qty`. The `WHERE` guard is the final safety net preventing double-spend at the DB level.
4. **Reservation insert** – a row with `status = 'reserved'` and `expires_at = now + 5 min` is persisted.
5. **ZSET registration** – `ZADD reservations:expiry {reservation_id: expires_at_timestamp}` gives the background worker a time-indexed view of pending expirations — no full-table scans.

---

## Database Schema

```sql
-- Users
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Products
CREATE TABLE products (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(255) NOT NULL,
    price               NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    total_inventory     INT NOT NULL CHECK (total_inventory >= 0),
    available_inventory INT NOT NULL CHECK (available_inventory >= 0),
    CONSTRAINT chk_inventory_bounds CHECK (available_inventory <= total_inventory)
);

-- Reservations
CREATE TYPE reservation_status AS ENUM
    ('pending','reserved','completed','expired','cancelled');

CREATE TABLE reservations (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id  UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity    INT NOT NULL CHECK (quantity > 0),
    status      reservation_status NOT NULL DEFAULT 'pending',
    expires_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Key indexes
CREATE INDEX idx_reservations_expires ON reservations (expires_at)
    WHERE status = 'reserved';
CREATE INDEX idx_products_available ON products (available_inventory)
    WHERE available_inventory > 0;
```

The `CHECK (available_inventory >= 0)` constraint is the **last line of defence** — even if application logic has a bug, the DB will reject an update that would make inventory negative.

---

## Concurrency Strategy: Preventing Double-Spend

### Layer 1 — Redis Atomic Decrement (microseconds)

```python
async def atomic_decrement_stock(product_id: str, quantity: int) -> int:
    r = await get_redis()
    new_val = await r.decrby(f"stock:{product_id}", quantity)
    if new_val < 0:
        await r.incrby(f"stock:{product_id}", quantity)  # rollback
        return -1  # signal: insufficient stock
    return new_val
```

Redis is single-threaded — `DECRBY` is guaranteed atomic. If two users request the last item at the same instant, only **one** `DECRBY` will see `>= 0`; the other sees `< 0` and is rejected.

### Layer 2 — Postgres WHERE Guard (milliseconds)

```python
result = await db.execute(
    update(Product)
    .where(Product.id == product_id)
    .where(Product.available_inventory >= quantity)
    .values(available_inventory=Product.available_inventory - quantity)
)
if result.rowcount == 0:
    # Redis rollback + return 409
```

Even if Redis fails over, this atomic SQL update prevents overselling at the DB level.

### Layer 3 — CHECK Constraint (absolute safety net)

```sql
CHECK (available_inventory >= 0)
```

---

## Expiration Worker

Uses a **Redis Sorted Set** (`ZSET`) instead of polling the database:

```python
async def expire_reservations_tick() -> int:
    now_ts = datetime.now(timezone.utc).timestamp()
    # Pull only reservations whose score <= now (O(log N + M))
    expired_ids = await redis_client.pop_expired_reservations(now_ts)

    for rid in expired_ids:
        reservation = await res_repo.mark_expired(rid)
        if reservation:  # wasn't already checked out
            await prod_repo.restore_inventory(reservation.product_id, reservation.quantity)
            await redis_client.restore_stock(str(reservation.product_id), reservation.quantity)
```

The `mark_expired` uses `WHERE status = 'reserved'` — if a concurrent checkout already transitioned the row, it returns `None` and we skip the restore: **idempotent by design**.

---

## Project Structure (Clean Architecture)

```
backend/
├── docker-compose.yml
├── Dockerfile                     # API image
├── Dockerfile.worker              # Worker image
├── requirements.txt
├── .env / .env.example
├── sql/
│   └── init.sql                   # DDL + seed data
├── app/
│   ├── main.py                    # FastAPI app factory + lifespan
│   ├── config.py                  # Pydantic settings
│   ├── dependencies.py            # JWT extraction dependency
│   │
│   ├── api/                       # ── Presentation Layer ──
│   │   └── v1/
│   │       ├── router.py          # Aggregated v1 router
│   │       ├── auth.py            # POST /auth/register, /login
│   │       ├── products.py        # GET /products
│   │       ├── reservations.py    # POST /reservations, /checkout
│   │       └── schemas/           # Pydantic request/response models
│   │
│   ├── services/                  # ── Business Logic Layer ──
│   │   ├── auth_service.py
│   │   ├── product_service.py
│   │   └── reservation_service.py # Core reservation + checkout logic
│   │
│   ├── repositories/              # ── Data Access Layer ──
│   │   ├── user_repo.py
│   │   ├── product_repo.py
│   │   └── reservation_repo.py
│   │
│   ├── models/                    # ── Domain Models (SQLAlchemy) ──
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── product.py
│   │   └── reservation.py
│   │
│   ├── core/                      # ── Cross-Cutting Concerns ──
│   │   ├── security.py            # JWT + password hashing
│   │   ├── exceptions.py          # Custom error hierarchy
│   │   ├── middleware.py          # Error handler
│   │   └── redis_client.py       # Redis pool + stock buffer + ZSET
│   │
│   ├── db/
│   │   └── session.py             # Async engine + session factory
│   │
│   └── worker/                    # ── Background Workers ──
│       ├── main.py                # Worker entry-point (asyncio)
│       ├── expiration_worker.py   # ZSET-based reservation expiration
│       └── stock_sync.py          # Periodic Redis ↔ Postgres sync
│
└── tests/
    ├── conftest.py
    ├── test_auth.py
    ├── test_reservations.py
    └── test_expiration.py
```

### Layer boundaries

| Layer | Depends on | Never depends on |
|---|---|---|
| API (routes, schemas) | Services | Repositories, Models, DB |
| Services | Repositories, Redis client | API, raw SQL |
| Repositories | Models, SQLAlchemy session | Services, API |
| Models | SQLAlchemy Base | Everything else |
| Worker | Repositories, Redis client | API |

---

## Docker Compose

```yaml
services:
  postgres:   # PostgreSQL 16 – source of truth
  redis:      # Redis 7 – stock buffer + ZSET + keyspace notifications
  api:        # FastAPI (uvicorn × 4 workers)
  worker:     # Background asyncio worker (expiration + stock-sync)
```

**Start everything:**

```bash
cd backend
docker compose up --build
```

The API is available at `http://localhost:8000`.  
Swagger UI at `http://localhost:8000/docs`.

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | No | Create account, get JWT |
| POST | `/api/v1/auth/login` | No | Authenticate, get JWT |
| GET | `/api/v1/products` | No | List available products |
| GET | `/api/v1/products/{id}` | No | Product detail |
| POST | `/api/v1/reservations` | JWT | Reserve stock (5-min window) |
| GET | `/api/v1/reservations` | JWT | List my reservations |
| GET | `/api/v1/reservations/{id}` | JWT | Reservation detail |
| POST | `/api/v1/reservations/{id}/checkout` | JWT | Complete purchase |
| GET | `/health` | No | Health check |

---

## Checkout Flow

```
reserved ──POST /checkout──▶ completed
    │                            │
    │  (5 min TTL)               │  total_inventory -= qty
    ▼                            │  removed from expiry ZSET
  expired                        ▼
    │                         SOLD ✓
    │  available_inventory += qty
    ▼
  Stock restored
```

1. User calls `POST /reservations/{id}/checkout`
2. Service verifies `status == 'reserved'` (rejects expired/completed)
3. Atomic transition: `reserved → completed`
4. `total_inventory -= quantity` (the item is permanently sold)
5. Reservation removed from ZSET (worker won't expire it)

---

## Quick-Start

```bash
# Clone and enter
cd backend

# Copy env (change JWT_SECRET_KEY for production!)
cp .env.example .env

# Launch
docker compose up --build

# Register a user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@flash.sale","password":"s3cureP@ss"}'

# Reserve stock (use the JWT from register response)
curl -X POST http://localhost:8000/api/v1/reservations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"product_id":"<product-uuid>","quantity":1}'

# Checkout within 5 minutes
curl -X POST http://localhost:8000/api/v1/reservations/<reservation-uuid>/checkout \
  -H "Authorization: Bearer <token>"
```
# Ray_backend_fastapi

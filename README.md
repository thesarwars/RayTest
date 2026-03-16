# RayTest — Real-Time Inventory Reservation System

A full-stack flash-sale platform that handles thousands of concurrent reservation requests without overselling. Built with **FastAPI**, **PostgreSQL**, **Redis**, **Next.js 15**, **TanStack Query**, and **Tailwind CSS** — all orchestrated with **Docker Compose**.

---

## Architecture Overview

```
┌─────────────────────────────────┐
│       Next.js 15 Frontend       │  :3000
│  (TanStack Query, Tailwind CSS) │
└──────────────┬──────────────────┘
               │  REST + JWT
┌──────────────▼──────────────────┐
│       FastAPI Backend           │  :8000
│  (uvicorn × 4 workers)         │
└──────┬───────────────┬──────────┘
       │               │
┌──────▼──────┐  ┌─────▼──────────┐
│ PostgreSQL  │  │     Redis      │
│ (Source of  │  │ • stock buffer │
│  Truth)     │  │ • expiry ZSET  │
└─────────────┘  └──────┬─────────┘
                        │
               ┌────────▼─────────┐
               │  Background      │
               │  Worker (asyncio)│
               │ • Expiration     │
               │ • Stock sync     │
               └──────────────────┘
```

### Concurrency Strategy (3-Layer Defence)

| Layer | Where | Speed | Mechanism |
|---|---|---|---|
| 1 | Redis `DECRBY` | μs | Atomic in-memory decrement; rejects if stock < 0 |
| 2 | Postgres `UPDATE … WHERE available_inventory >= qty` | ms | Row-level atomic guard |
| 3 | `CHECK (available_inventory >= 0)` | DB constraint | Absolute safety net |

---

## Project Structure

```
RayTest/
├── backend/                          ── FastAPI + Worker
│   ├── docker-compose.yml            All services (PG, Redis, API, Worker, Frontend)
│   ├── Dockerfile                    API image
│   ├── Dockerfile.worker             Worker image
│   ├── requirements.txt              Python dependencies
│   ├── .env / .env.example           Environment config
│   ├── sql/
│   │   └── init.sql                  DDL, constraints, indexes, seed data
│   ├── app/
│   │   ├── main.py                   FastAPI app factory + CORS + lifespan
│   │   ├── config.py                 Pydantic settings
│   │   ├── dependencies.py           JWT extraction dependency
│   │   ├── api/v1/                   ── Presentation Layer
│   │   │   ├── router.py             Aggregated v1 router
│   │   │   ├── auth.py               POST /auth/register, /login
│   │   │   ├── products.py           GET /products
│   │   │   ├── reservations.py       POST /reservations, /checkout
│   │   │   └── schemas/              Pydantic request/response models
│   │   ├── services/                 ── Business Logic Layer
│   │   │   ├── auth_service.py       Register/login + JWT
│   │   │   ├── product_service.py    Product listing
│   │   │   └── reservation_service.py Core reserve + checkout logic
│   │   ├── repositories/             ── Data Access Layer
│   │   │   ├── user_repo.py
│   │   │   ├── product_repo.py       atomic_decrement, restore, finalize
│   │   │   └── reservation_repo.py   mark_expired, mark_completed
│   │   ├── models/                   ── SQLAlchemy ORM Models
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   └── reservation.py
│   │   ├── core/                     ── Cross-Cutting Concerns
│   │   │   ├── security.py           JWT + bcrypt hashing
│   │   │   ├── exceptions.py         Custom error hierarchy
│   │   │   ├── middleware.py         Error handler
│   │   │   └── redis_client.py       Stock buffer + ZSET helpers
│   │   ├── db/
│   │   │   └── session.py            Async engine + session factory
│   │   └── worker/                   ── Background Workers
│   │       ├── main.py               Worker entry-point (asyncio)
│   │       ├── expiration_worker.py   ZSET-based reservation expiry
│   │       └── stock_sync.py         Periodic Redis ↔ Postgres sync
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_reservations.py
│       └── test_expiration.py
│
└── frontend/                         ── Next.js 15 (App Router)
    ├── Dockerfile                    Multi-stage build (standalone)
    ├── package.json                  React 19, TanStack Query, Tailwind 4
    ├── .env.local                    NEXT_PUBLIC_API_URL
    ├── src/
    │   ├── middleware.ts             Security headers
    │   ├── app/                      ── Pages
    │   │   ├── layout.tsx            Root layout + Providers + Navbar
    │   │   ├── page.tsx              Product catalog (home)
    │   │   ├── providers.tsx         TanStack Query + Auth + Toast
    │   │   ├── login/page.tsx        Login form
    │   │   ├── register/page.tsx     Registration form
    │   │   └── reservations/page.tsx Auth-guarded reservation dashboard
    │   ├── components/               ── UI Components
    │   │   ├── Navbar.tsx            Auth-aware navigation bar
    │   │   ├── ProductCard.tsx       Product card + optimistic Reserve
    │   │   ├── ProductGrid.tsx       Product list with skeletons
    │   │   ├── ReservationCard.tsx   Countdown timer + checkout
    │   │   ├── ReservationList.tsx   User's reservations
    │   │   └── ui/
    │   │       ├── Button.tsx        Reusable button with spinner
    │   │       ├── Countdown.tsx     5-min countdown (survives refresh)
    │   │       ├── Skeleton.tsx      Loading skeletons
    │   │       └── StatusBadge.tsx   Coloured status pills
    │   ├── hooks/                    ── React Hooks
    │   │   ├── useAuth.tsx           Auth context + JWT localStorage
    │   │   ├── useProducts.ts        Queries + optimistic reserve mutation
    │   │   └── useReservations.ts    Polling + checkout mutation
    │   └── lib/
    │       ├── types.ts              Shared TypeScript interfaces
    │       └── api/client.ts         Typed fetch wrapper for FastAPI
    └── public/
```

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | — | Create account, returns JWT |
| POST | `/api/v1/auth/login` | — | Authenticate, returns JWT |
| GET | `/api/v1/products` | — | List available products |
| GET | `/api/v1/products/{id}` | — | Product detail |
| POST | `/api/v1/reservations` | JWT | Reserve stock (5-min window) |
| GET | `/api/v1/reservations` | JWT | List user's reservations |
| GET | `/api/v1/reservations/{id}` | JWT | Reservation detail (polled by frontend) |
| POST | `/api/v1/reservations/{id}/checkout` | JWT | Complete purchase |
| GET | `/health` | — | Health check |

---

## Reservation Flow

```
User clicks "Reserve"
        │
        ▼
  ┌─ Redis DECRBY ──┐    Instant (μs)
  │  stock < 0?      │──── Yes ──▶ 409 Insufficient Stock
  │  No ▼            │
  └──────────────────┘
        │
        ▼
  ┌─ Postgres UPDATE ┐    Atomic (ms)
  │  WHERE avail >= q │──── Fail ──▶ Rollback Redis → 409
  │  OK ▼             │
  └───────────────────┘
        │
        ▼
  INSERT reservation (status=reserved, expires_at=now+5min)
  ZADD expiry ZSET
        │
        ▼
  Return 201 { reservation_id, expires_at }
        │
  ┌─────▼──────────────────────────┐
  │  Frontend: Countdown Timer     │
  │  Polls while status=pending    │
  │  Checkout button enabled       │
  └─────┬──────────────────────────┘
        │
   User clicks "Checkout"          Timer hits 0:00
        │                                │
        ▼                                ▼
  reserved → completed             Worker: reserved → expired
  total_inventory -= qty           available_inventory += qty
  Remove from ZSET                 Redis INCRBY (stock restored)
```

---

## Frontend Features

| Feature | Implementation |
|---|---|
| **Auth** | `useAuth` context — JWT stored in localStorage, login/register/logout, route protection |
| **Optimistic Updates** | `useReserveProduct` decrements inventory in cache immediately; rolls back on error |
| **Queue Polling** | `usePollReservation` polls `GET /reservations/{id}` every 2s while `status === "pending"` |
| **Countdown Timer** | Derives remaining time from `expires_at` vs `Date.now()` — survives page refresh. Color shifts: green → yellow (< 60s) → red (< 15s). Disables checkout at zero. |
| **Loading States** | Skeleton components during data fetch; spinner on Reserve/Checkout buttons |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 4 |
| Data Fetching | TanStack Query (React Query) v5 |
| Backend | FastAPI, Pydantic, SQLAlchemy 2 (async) |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 (stock buffer, ZSET expiry tracking) |
| Auth | JWT (HS256) + bcrypt |
| Infra | Docker Compose (5 services) |

---

## Quick Start

```bash
# Clone the repo
git clone <repo-url> && cd RayTest

# Copy environment config (change JWT_SECRET_KEY for production!)
cp backend/.env.example backend/.env

# Launch all services
cd backend
docker compose up --build

# ──────────────────────────────
# Backend API  → http://localhost:8000
# Swagger UI   → http://localhost:8000/docs
# Frontend     → http://localhost:3000
# ──────────────────────────────
```

### Manual testing with curl

```bash
# Register
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@flash.sale","password":"s3cureP@ss"}'

# Reserve (use token from register response)
curl -s -X POST http://localhost:8000/api/v1/reservations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"product_id":"<uuid>","quantity":1}'

# Checkout within 5 minutes
curl -s -X POST http://localhost:8000/api/v1/reservations/<reservation-uuid>/checkout \
  -H "Authorization: Bearer <token>"
```

---

## Database Schema

Three tables with safety constraints:

- **users** — UUID PK, unique email, bcrypt password
- **products** — `CHECK (available_inventory >= 0)`, `CHECK (available_inventory <= total_inventory)`
- **reservations** — status ENUM (`pending`, `reserved`, `completed`, `expired`, `cancelled`), `expires_at` indexed

Seed data: 3 demo products (Sneakers, Earbuds, Smartwatch) pre-loaded via `sql/init.sql`.

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://…` | Async Postgres connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `JWT_SECRET_KEY` | `CHANGE-ME…` | **Must change in production** |
| `JWT_EXPIRATION_MINUTES` | `60` | Token lifetime |
| `RESERVATION_TTL_SECONDS` | `300` | 5-minute reservation window |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Frontend → Backend URL |

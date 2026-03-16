-- =============================================================
-- Real-Time Inventory Reservation System – Database Schema
-- =============================================================

-- ─── EXTENSIONS ──────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── USERS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email         VARCHAR(255) NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users (email);

-- ─── PRODUCTS ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    price               NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
    total_inventory     INT NOT NULL CHECK (total_inventory >= 0),
    available_inventory INT NOT NULL CHECK (available_inventory >= 0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- available can never exceed total
    CONSTRAINT chk_inventory_bounds
        CHECK (available_inventory <= total_inventory)
);

CREATE INDEX idx_products_available ON products (available_inventory)
    WHERE available_inventory > 0;

-- ─── RESERVATIONS ────────────────────────────────────────────
CREATE TYPE reservation_status AS ENUM ('pending', 'reserved', 'completed', 'expired', 'cancelled');

CREATE TABLE IF NOT EXISTS reservations (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id    UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity      INT NOT NULL CHECK (quantity > 0),
    status        reservation_status NOT NULL DEFAULT 'pending',
    expires_at    TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_reservations_status   ON reservations (status);
CREATE INDEX idx_reservations_expires  ON reservations (expires_at)
    WHERE status = 'reserved';
CREATE INDEX idx_reservations_user     ON reservations (user_id);
CREATE INDEX idx_reservations_product  ON reservations (product_id);

-- ─── SEED DATA (demo products for flash sale) ───────────────
INSERT INTO products (name, description, price, total_inventory, available_inventory)
VALUES
    ('Flash-Sale Sneakers',   'Limited edition sneakers',      129.99, 500, 500),
    ('Wireless Earbuds Pro',  'Noise-cancelling earbuds',       79.99, 300, 300),
    ('Smart Watch Ultra',     'Flagship smartwatch',           349.99, 200, 200)
ON CONFLICT DO NOTHING;

-- =====================================================
-- FaidaYetu Test Data for Supabase (PostgreSQL)
-- Password kwa users wote: password123
-- Hash format: pbkdf2_sha256$720000${salt}${hash}
-- =====================================================

-- 0. CREATE TABLES IF NOT EXISTS
-- =====================================================

CREATE TABLE IF NOT EXISTS auth_user (
    id              SERIAL PRIMARY KEY,
    password        VARCHAR(128) NOT NULL,
    last_login      TIMESTAMPTZ,
    is_superuser    BOOLEAN NOT NULL,
    username        VARCHAR(150) NOT NULL UNIQUE,
    first_name      VARCHAR(150) NOT NULL,
    last_name       VARCHAR(150) NOT NULL,
    email           VARCHAR(254) NOT NULL,
    is_staff        BOOLEAN NOT NULL,
    is_active       BOOLEAN NOT NULL,
    date_joined     TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts_profile (
    id      SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE,
    role    VARCHAR(20) NOT NULL,
    phone   VARCHAR(20) NOT NULL,
    lat     DOUBLE PRECISION NOT NULL,
    lng     DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts_supplier (
    id              SERIAL PRIMARY KEY,
    profile_id      INTEGER NOT NULL UNIQUE REFERENCES accounts_profile(id) ON DELETE CASCADE,
    business_name   VARCHAR(255) NOT NULL,
    business_email  VARCHAR(254) NOT NULL,
    description     TEXT NOT NULL,
    address         VARCHAR(255) NOT NULL,
    rating          DOUBLE PRECISION NOT NULL,
    image           TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts_customer (
    id                SERIAL PRIMARY KEY,
    profile_id        INTEGER NOT NULL UNIQUE REFERENCES accounts_profile(id) ON DELETE CASCADE,
    default_address   VARCHAR(255) NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts_deliveryperson (
    id              SERIAL PRIMARY KEY,
    profile_id      INTEGER NOT NULL UNIQUE REFERENCES accounts_profile(id) ON DELETE CASCADE,
    vehicle_type    VARCHAR(100) NOT NULL,
    status          VARCHAR(20) NOT NULL,
    total_earnings  DOUBLE PRECISION NOT NULL,
    rating          DOUBLE PRECISION NOT NULL,
    total_routes    INTEGER NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts_product (
    id          SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES accounts_supplier(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    category    VARCHAR(20) NOT NULL,
    price       DOUBLE PRECISION NOT NULL,
    unit        VARCHAR(50) NOT NULL,
    stock       INTEGER NOT NULL,
    min_stock   INTEGER NOT NULL,
    image       TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts_order (
    id                SERIAL PRIMARY KEY,
    customer_id       INTEGER NOT NULL REFERENCES accounts_customer(id) ON DELETE CASCADE,
    supplier_id       INTEGER NOT NULL REFERENCES accounts_supplier(id) ON DELETE CASCADE,
    delivery_id       INTEGER,
    status            VARCHAR(20) NOT NULL,
    total             DOUBLE PRECISION NOT NULL,
    delivery_lat      DOUBLE PRECISION NOT NULL,
    delivery_lng      DOUBLE PRECISION NOT NULL,
    delivery_address  VARCHAR(255) NOT NULL,
    notes             TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL,
    updated_at        TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts_orderitem (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES accounts_order(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL REFERENCES accounts_product(id) ON DELETE CASCADE,
    quantity    INTEGER NOT NULL,
    price       DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS deliveries_delivery (
    id                SERIAL PRIMARY KEY,
    delivery_person_id INTEGER NOT NULL REFERENCES accounts_deliveryperson(id) ON DELETE CASCADE,
    status            VARCHAR(20) NOT NULL,
    started_at        TIMESTAMPTZ,
    completed_at      TIMESTAMPTZ,
    distance_km       DOUBLE PRECISION NOT NULL,
    earnings          DOUBLE PRECISION NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS deliveries_deliverylog (
    id          SERIAL PRIMARY KEY,
    delivery_id INTEGER NOT NULL REFERENCES deliveries_delivery(id) ON DELETE CASCADE,
    lat         DOUBLE PRECISION NOT NULL,
    lng         DOUBLE PRECISION NOT NULL,
    timestamp   TIMESTAMPTZ NOT NULL
);

-- Add FK for accounts_order.delivery_id (after deliveries_delivery exists)
DO $$ BEGIN
    ALTER TABLE accounts_order ADD CONSTRAINT fk_order_delivery
        FOREIGN KEY (delivery_id) REFERENCES deliveries_delivery(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- =====================================================
-- 1. DELETE existing data (clean slate)
-- =====================================================
-- Clear FKs first to avoid constraint violations
UPDATE accounts_order SET delivery_id = NULL;
DELETE FROM deliveries_deliverylog;
DELETE FROM deliveries_delivery;
DELETE FROM accounts_orderitem;
DELETE FROM accounts_order;
DELETE FROM accounts_product;
DELETE FROM accounts_deliveryperson;
DELETE FROM accounts_customer;
DELETE FROM accounts_supplier;
DELETE FROM accounts_profile;
DELETE FROM auth_user;

-- Reset sequences
ALTER SEQUENCE IF EXISTS auth_user_id_seq                 RESTART WITH 1;
ALTER SEQUENCE IF EXISTS accounts_profile_id_seq          RESTART WITH 1;
ALTER SEQUENCE IF EXISTS accounts_supplier_id_seq         RESTART WITH 1;
ALTER SEQUENCE IF EXISTS accounts_customer_id_seq         RESTART WITH 1;
ALTER SEQUENCE IF EXISTS accounts_deliveryperson_id_seq  RESTART WITH 1;
ALTER SEQUENCE IF EXISTS accounts_product_id_seq          RESTART WITH 1;
ALTER SEQUENCE IF EXISTS accounts_order_id_seq            RESTART WITH 1;
ALTER SEQUENCE IF EXISTS accounts_orderitem_id_seq        RESTART WITH 1;
ALTER SEQUENCE IF EXISTS deliveries_delivery_id_seq       RESTART WITH 1;
ALTER SEQUENCE IF EXISTS deliveries_deliverylog_id_seq   RESTART WITH 1;

-- =====================================================
-- 2. USERS (auth_user)
-- =====================================================
INSERT INTO auth_user (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined) VALUES
(1,  'pbkdf2_sha256$720000$adminSalt2026$IItf7cKnbuaU8BmVgmOHBVuFNvfTLtDoEP573sTh3H0=', NOW(), TRUE,  'admin',     'Admin',   'FaidaYetu', 'admin@faidayetu.co.tz',     TRUE,  TRUE, NOW() - INTERVAL '90 days'),
(2,  'pbkdf2_sha256$720000$supplier1Salt2026$JEjxFtxRbID94+cjYROHk8gl2UV6vfVVjsA1zxy8FEs=', NOW(), FALSE, 'supplier1', 'Premium', 'Poultry',   'supplier@faidayetu.co.tz',  FALSE, TRUE, NOW() - INTERVAL '60 days'),
(3,  'pbkdf2_sha256$720000$supplier2Salt2026$RptlGfDbZBjhJJNspKpcqd5Wr47WAIRYQkBo/c471RA=', NOW(), FALSE, 'supplier2', 'Mbezi',   'Fresh',     'mbezi@faidayetu.co.tz',     FALSE, TRUE, NOW() - INTERVAL '60 days'),
(4,  'pbkdf2_sha256$720000$supplier3Salt2026$Y/DgMOY2Ax59aBYr1vVownN39IpjAjKpkfmvYaBI8E8=', NOW(), FALSE, 'supplier3', 'City',    'Chickens',  'city@faidayetu.co.tz',      FALSE, TRUE, NOW() - INTERVAL '60 days'),
(5,  'pbkdf2_sha256$720000$delivery1Salt2026$6YxgfdYMtyn8SwOUqD4UIQr778ChnfJSsebc7EjWAaI=', NOW(), FALSE, 'delivery1', 'John',    'Driver',    'john@faidayetu.co.tz',      FALSE, TRUE, NOW() - INTERVAL '45 days'),
(6,  'pbkdf2_sha256$720000$delivery2Salt2026$BuBU27dVaGWqIFbHturwTR7k7Xtuatq6FrGJwBfEMsc=', NOW(), FALSE, 'delivery2', 'Ali',     'Rider',     'ali@faidayetu.co.tz',       FALSE, TRUE, NOW() - INTERVAL '45 days'),
(7,  'pbkdf2_sha256$720000$juma_cSalt2026$+sRi91FES5BazQ4rNjgt3sIuacUCaZt2wid28bvDfSk=', NOW(), FALSE, 'juma_c',    'Juma',    'Mussa',     'juma@example.com',          FALSE, TRUE, NOW() - INTERVAL '30 days'),
(8,  'pbkdf2_sha256$720000$asha_cSalt2026$Wm8qNnpnQawSZZHA7hvRM8bo1YEJu8nl+Obi+5hSmEo=', NOW(), FALSE, 'asha_c',    'Asha',    'Salum',     'asha@example.com',          FALSE, TRUE, NOW() - INTERVAL '28 days'),
(9,  'pbkdf2_sha256$720000$baraka_cSalt2026$0D5p4D0lgmJMqE1nKw4t57rZT26Qj21wqTk634nR6FI=', NOW(), FALSE, 'baraka_c',  'Baraka',  'Mfinanga',  'baraka@example.com',        FALSE, TRUE, NOW() - INTERVAL '25 days'),
(10, 'pbkdf2_sha256$720000$fatuma_cSalt2026$71KyYZFFbXzi22iNMi4GBfpny5HgP49eZ4eyPA7R1JI=', NOW(), FALSE, 'fatuma_c',  'Fatuma',  'Said',      'fatuma@example.com',        FALSE, TRUE, NOW() - INTERVAL '22 days'),
(11, 'pbkdf2_sha256$720000$hassan_cSalt2026$z3an0gNq/lSbJM9CM1dHnTj4OhYpfgIogfR2+v/03tU=', NOW(), FALSE, 'hassan_c',  'Hassan',  'Abdallah',  'hassan@example.com',        FALSE, TRUE, NOW() - INTERVAL '20 days'),
(12, 'pbkdf2_sha256$720000$mary_cSalt2026$Zf6xWjJsXxqFuYnfIHlKAlkey1e9c5vUHvNbYe5cqBY=', NOW(), FALSE, 'mary_c',    'Mary',    'John',      'mary@example.com',          FALSE, TRUE, NOW() - INTERVAL '18 days'),
(13, 'pbkdf2_sha256$720000$james_cSalt2026$Bxjqa4C41bTS2H75BsB9ABbDZ3ishgAeDySWdB8i7uQ=', NOW(), FALSE, 'james_c',   'James',   'Mushi',     'james@example.com',         FALSE, TRUE, NOW() - INTERVAL '15 days'),
(14, 'pbkdf2_sha256$720000$anna_cSalt2026$UaMUt5N36Ly6687iRjPmEfCNlZut3YPgHrvGOYxgdKg=', NOW(), FALSE, 'anna_c',    'Anna',    'Nkya',      'anna@example.com',          FALSE, TRUE, NOW() - INTERVAL '14 days'),
(15, 'pbkdf2_sha256$720000$peter_cSalt2026$DsZ7gP7/WWOcbssxKvUlBnCyoKeIfS79OKBNvWcnYZs=', NOW(), FALSE, 'peter_c',   'Peter',   'Mkude',     'peter@example.com',         FALSE, TRUE, NOW() - INTERVAL '10 days'),
(16, 'pbkdf2_sha256$720000$sarah_cSalt2026$xo6xwrH47T52WhgOrvLAztzlCKGkpcDjDtP75QWNtIk=', NOW(), FALSE, 'sarah_c',   'Sarah',   'Kiswaga',   'sarah@example.com',         FALSE, TRUE, NOW() - INTERVAL '7 days');

-- =====================================================
-- 3. PROFILES (accounts_profile)
-- =====================================================
INSERT INTO accounts_profile (id, user_id, role, phone, lat, lng) VALUES
(1,  1,  'admin',    '+255 712 000 000', -6.7924, 39.2083),
(2,  2,  'supplier', '+255 712 345 678', -6.8000, 39.2700),
(3,  3,  'supplier', '+255 713 456 789', -6.7400, 39.2000),
(4,  4,  'supplier', '+255 714 567 890', -6.8200, 39.2800),
(5,  5,  'delivery', '+255 715 000 001', -6.7800, 39.2500),
(6,  6,  'delivery', '+255 715 000 002', -6.8000, 39.2600),
(7,  7,  'customer', '+255 715 678 901', -6.8194, 39.2802),
(8,  8,  'customer', '+255 715 678 902', -6.8150, 39.2750),
(9,  9,  'customer', '+255 715 678 903', -6.8100, 39.2850),
(10, 10, 'customer', '+255 715 678 904', -6.8050, 39.2900),
(11, 11, 'customer', '+255 715 678 905', -6.7950, 39.2700),
(12, 12, 'customer', '+255 715 678 906', -6.7750, 39.2550),
(13, 13, 'customer', '+255 715 678 907', -6.7600, 39.2400),
(14, 14, 'customer', '+255 715 678 908', -6.7500, 39.2200),
(15, 15, 'customer', '+255 715 678 909', -6.7700, 39.2600),
(16, 16, 'customer', '+255 715 678 910', -6.7900, 39.2450);

-- =====================================================
-- 4. SUPPLIERS (accounts_supplier)
-- =====================================================
INSERT INTO accounts_supplier (id, profile_id, business_name, business_email, description, address, rating, image, created_at) VALUES
(1, 2, 'Premium Poultry Co.',    'premium@faidayetu.co.tz', 'Premium quality poultry products from industrial-scale farms. Specializing in eggs, broilers, and poultry feed.', 'Industrial Zone B, Dar es Salaam', 4.8, 'https://images.unsplash.com/photo-1599839575945-a9e5af0c3fa5?w=400', NOW() - INTERVAL '60 days'),
(2, 3, 'Mbezi Fresh Farms',     'mbezi@faidayetu.co.tz',   'Fresh free-range chicken and organic eggs from Mbezi Beach. Family-owned since 2010.', 'Mbezi Beach, Dar es Salaam',        4.9, 'https://images.unsplash.com/photo-1566498721760-090b6ae82a60?w=400', NOW() - INTERVAL '60 days'),
(3, 4, 'City Chickens Ltd',     'city@faidayetu.co.tz',    'Your neighborhood poultry supplier in the city center. Wide range of chicken products and local brew ingredients.', 'City Center, Dar es Salaam',        4.7, 'https://images.unsplash.com/photo-1548550023-2bdb3c5beed7?w=400', NOW() - INTERVAL '60 days');

-- =====================================================
-- 5. CUSTOMERS (accounts_customer)
-- =====================================================
INSERT INTO accounts_customer (id, profile_id, default_address, created_at) VALUES
(1,  7,  'Kariakoni, Dar es Salaam',     NOW() - INTERVAL '30 days'),
(2,  8,  'Mchafukoge, Dar es Salaam',    NOW() - INTERVAL '28 days'),
(3,  9,  'Kisutu, Dar es Salaam',        NOW() - INTERVAL '25 days'),
(4,  10, 'Kivukoni, Dar es Salaam',      NOW() - INTERVAL '22 days'),
(5,  11, 'Upanga, Dar es Salaam',        NOW() - INTERVAL '20 days'),
(6,  12, 'Mwananyamala, Dar es Salaam',  NOW() - INTERVAL '18 days'),
(7,  13, 'Kinondoni, Dar es Salaam',     NOW() - INTERVAL '15 days'),
(8,  14, 'Kawe, Dar es Salaam',          NOW() - INTERVAL '14 days'),
(9,  15, 'Mikocheni, Dar es Salaam',     NOW() - INTERVAL '10 days'),
(10, 16, 'Tandale, Dar es Salaam',       NOW() - INTERVAL '7 days');

-- =====================================================
-- 6. DELIVERY PERSONS (accounts_deliveryperson)
-- =====================================================
INSERT INTO accounts_deliveryperson (id, profile_id, vehicle_type, status, total_earnings, rating, total_routes, created_at) VALUES
(1, 5,  'Pickup Truck', 'online', 450000, 4.7, 45, NOW() - INTERVAL '45 days'),
(2, 6,  'Motorcycle',   'online', 220000, 4.5, 28, NOW() - INTERVAL '45 days');

-- =====================================================
-- 7. PRODUCTS (accounts_product)
-- =====================================================
INSERT INTO accounts_product (id, supplier_id, name, category, price, unit, stock, min_stock, image, created_at, updated_at) VALUES
(1,  1, 'Grade A Eggs (Large 30pk)',  'eggs',        12000, 'tray',  1240, 50,  'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400', NOW() - INTERVAL '60 days', NOW()),
(2,  1, 'Organic Broiler (whole)',    'chicken',     18500, 'kg',    84,   10,  'https://images.unsplash.com/photo-1587593810167-a84920ea0781?w=400', NOW() - INTERVAL '60 days', NOW()),
(3,  1, 'Kienyeji Chicken (1kg)',     'chicken',     14000, 'kg',    45,   15,  'https://images.unsplash.com/photo-1567620832903-9fc6debc209f?w=400', NOW() - INTERVAL '60 days', NOW()),
(4,  1, 'Poultry Feed (50kg bag)',    'feed',        45000, 'bag',   320,  20,  'https://images.unsplash.com/photo-1622021142947-da7dedc7c524?w=400', NOW() - INTERVAL '60 days', NOW()),
(5,  2, 'Free Range Eggs (12pk)',     'eggs',         6500, 'pack',  500,  30,  'https://images.unsplash.com/photo-1498654077810-5c6e5f2117d9?w=400', NOW() - INTERVAL '60 days', NOW()),
(6,  2, 'Dressed Chicken (2kg)',      'chicken',     22000, 'kg',    60,   10,  'https://images.unsplash.com/photo-1604503468506-a8da13d82791?w=400', NOW() - INTERVAL '60 days', NOW()),
(7,  3, 'Local Brew Ingredients',     'supplements',  8500, 'pack',  200,  25,  'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=400', NOW() - INTERVAL '60 days', NOW()),
(8,  2, 'Layers Mash (50kg bag)',     'feed',        38000, 'bag',   250,  15,  'https://images.unsplash.com/photo-1622021142947-da7dedc7c524?w=400', NOW() - INTERVAL '60 days', NOW()),
(9,  3, 'Day-Old Chicks (box of 50)',  'chicken',    25000, 'box',   100,  5,   'https://images.unsplash.com/photo-1563250630-4c4975e85ce2?w=400', NOW() - INTERVAL '60 days', NOW()),
(10, 1, 'Vitamin Premix (1kg)',       'supplements', 12000, 'kg',    500,  20,  'https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=400', NOW() - INTERVAL '60 days', NOW());

-- =====================================================
-- 8. ORDERS (accounts_order)
-- 35 orders across 30 days with various statuses
-- =====================================================
INSERT INTO accounts_order (id, customer_id, supplier_id, delivery_id, status, total, delivery_lat, delivery_lng, delivery_address, notes, created_at, updated_at) VALUES
-- Delivered orders (siku 30-20 zilizopita)
(1,  1, 1, NULL, 'delivered',  34000, -6.8194, 39.2802, 'Kariakoo, Dar es Salaam',        'Asante!',              NOW() - INTERVAL '30 days', NOW() - INTERVAL '29 days'),
(2,  2, 2, NULL, 'delivered',  28500, -6.8150, 39.2750, 'Mchafukoge, Dar es Salaam',      '',                     NOW() - INTERVAL '28 days', NOW() - INTERVAL '27 days'),
(3,  3, 3, NULL, 'delivered',  25500, -6.8100, 39.2850, 'Kisutu, Dar es Salaam',          'Piga kabla ya kuja',   NOW() - INTERVAL '27 days', NOW() - INTERVAL '26 days'),
(4,  4, 1, NULL, 'delivered',  12000, -6.8050, 39.2900, 'Kivukoni, Dar es Salaam',        '',                     NOW() - INTERVAL '25 days', NOW() - INTERVAL '24 days'),
(5,  5, 2, NULL, 'delivered',  65000, -6.7950, 39.2700, 'Upanga, Dar es Salaam',          '2 bags of feed',       NOW() - INTERVAL '24 days', NOW() - INTERVAL '23 days'),
(6,  6, 3, NULL, 'delivered',  34000, -6.7750, 39.2550, 'Mwananyamala, Dar es Salaam',    '',                     NOW() - INTERVAL '22 days', NOW() - INTERVAL '21 days'),
(7,  1, 2, NULL, 'delivered',  13000, -6.8194, 39.2802, 'Kariakoo, Dar es Salaam',        'Free range eggs',      NOW() - INTERVAL '21 days', NOW() - INTERVAL '20 days'),
(8,  7, 1, NULL, 'delivered',  30500, -6.7600, 39.2400, 'Kinondoni, Dar es Salaam',       '',                     NOW() - INTERVAL '20 days', NOW() - INTERVAL '19 days'),
(9,  8, 3, NULL, 'delivered',  8500,  -6.7500, 39.2200, 'Kawe, Dar es Salaam',            'Brew ingredients',     NOW() - INTERVAL '19 days', NOW() - INTERVAL '18 days'),
(10, 3, 1, NULL, 'delivered',  59000, -6.8100, 39.2850, 'Kisutu, Dar es Salaam',          'Kienyeji + feed',      NOW() - INTERVAL '18 days', NOW() - INTERVAL '17 days'),

-- In-transit orders (siku 14-10 zilizopita)
(11, 9,  1, NULL, 'in_transit', 18500, -6.7700, 39.2600, 'Mikocheni, Dar es Salaam',       'Broiler',              NOW() - INTERVAL '14 days', NOW() - INTERVAL '13 days'),
(12, 10, 2, NULL, 'in_transit', 44000, -6.7900, 39.2450, 'Tandale, Dar es Salaam',         'Dressed chicken x2',   NOW() - INTERVAL '13 days', NOW() - INTERVAL '12 days'),
(13, 4,  3, NULL, 'in_transit', 33500, -6.8050, 39.2900, 'Kivukoni, Dar es Salaam',        '',                     NOW() - INTERVAL '12 days', NOW() - INTERVAL '11 days'),

-- Ready orders
(14, 5, 1, NULL, 'ready',      24000, -6.7950, 39.2700, 'Upanga, Dar es Salaam',           '2 trays eggs',         NOW() - INTERVAL '10 days', NOW() - INTERVAL '9 days'),
(15, 2, 2, NULL, 'ready',      28500, -6.8150, 39.2750, 'Mchafukoge, Dar es Salaam',      '',                     NOW() - INTERVAL '9 days',  NOW() - INTERVAL '8 days'),

-- Processing orders
(16, 6,  3, NULL, 'processing', 8500,  -6.7750, 39.2550, 'Mwananyamala, Dar es Salaam',    '',                     NOW() - INTERVAL '7 days',  NOW() - INTERVAL '6 days'),
(17, 7,  1, NULL, 'processing', 45000, -6.7600, 39.2400, 'Kinondoni, Dar es Salaam',       '1 bag feed',           NOW() - INTERVAL '6 days',  NOW() - INTERVAL '5 days'),
(18, 10, 2, NULL, 'processing', 6500,  -6.7900, 39.2450, 'Tandale, Dar es Salaam',         '',                     NOW() - INTERVAL '5 days',  NOW() - INTERVAL '4 days'),

-- Paid orders
(19, 8,  1, NULL, 'paid',      12000, -6.7500, 39.2200, 'Kawe, Dar es Salaam',             'Vitamin premix',       NOW() - INTERVAL '4 days',  NOW() - INTERVAL '3 days'),
(20, 3,  2, NULL, 'paid',      38000, -6.8100, 39.2850, 'Kisutu, Dar es Salaam',           'Layers mash',          NOW() - INTERVAL '3 days',  NOW() - INTERVAL '2 days'),

-- New orders
(21, 1, 3, NULL, 'new',        8500,  -6.8194, 39.2802, 'Kariakoo, Dar es Salaam',         '',                     NOW() - INTERVAL '2 days',  NOW()),
(22, 4, 1, NULL, 'new',        30500, -6.8050, 39.2900, 'Kivukoni, Dar es Salaam',         'Chicken and eggs',     NOW() - INTERVAL '1 day',   NOW()),
(23, 9, 2, NULL, 'new',        22000, -6.7700, 39.2600, 'Mikocheni, Dar es Salaam',        '',                     NOW(), NOW()),

-- Cancelled orders
(24, 2, 1, NULL, 'cancelled',  34000, -6.8150, 39.2750, 'Mchafukoge, Dar es Salaam',       'Changed mind',         NOW() - INTERVAL '15 days', NOW() - INTERVAL '14 days'),
(25, 5, 3, NULL, 'cancelled',  8500,  -6.7950, 39.2700, 'Upanga, Dar es Salaam',           'Not needed',           NOW() - INTERVAL '8 days',  NOW() - INTERVAL '7 days'),

-- Extra orders za kutosha kwa analytics (siku tofauti)
(26, 6,  1, NULL, 'delivered', 56500, -6.7750, 39.2550, 'Mwananyamala, Dar es Salaam',     'Weekly supply',        NOW() - INTERVAL '26 days', NOW() - INTERVAL '25 days'),
(27, 10, 3, NULL, 'delivered', 17000, -6.7900, 39.2450, 'Tandale, Dar es Salaam',          '',                     NOW() - INTERVAL '23 days', NOW() - INTERVAL '22 days'),
(28, 7,  2, NULL, 'delivered', 13000, -6.7600, 39.2400, 'Kinondoni, Dar es Salaam',        'Free range eggs x2',   NOW() - INTERVAL '16 days', NOW() - INTERVAL '15 days'),
(29, 8,  1, NULL, 'delivered', 74000, -6.7500, 39.2200, 'Kawe, Dar es Salaam',             'Broiler + Kienyeji + eggs', NOW() - INTERVAL '11 days', NOW() - INTERVAL '10 days'),
(30, 9,  3, NULL, 'delivered', 25000, -6.7700, 39.2600, 'Mikocheni, Dar es Salaam',        'Day-old chicks',       NOW() - INTERVAL '6 days',  NOW() - INTERVAL '5 days'),
(31, 3,  1, NULL, 'paid',      12000, -6.8100, 39.2850, 'Kisutu, Dar es Salaam',           'Vitamin premix',       NOW() - INTERVAL '1 day',   NOW()),
(32, 1,  2, NULL, 'new',        6500, -6.8194, 39.2802, 'Kariakoo, Dar es Salaam',         '',                     NOW(), NOW()),
(33, 5,  1, NULL, 'processing', 45000, -6.7950, 39.2700, 'Upanga, Dar es Salaam',           'Feed 50kg',            NOW() - INTERVAL '3 days',  NOW() - INTERVAL '2 days'),
(34, 4,  2, NULL, 'ready',      6500,  -6.8050, 39.2900, 'Kivukoni, Dar es Salaam',         '',                     NOW() - INTERVAL '2 days',  NOW() - INTERVAL '1 day'),
(35, 6,  1, NULL, 'new',       18500, -6.7750, 39.2550, 'Mwananyamala, Dar es Salaam',     'Broiler chicken',      NOW(), NOW());

-- =====================================================
-- 9. ORDER ITEMS (accounts_orderitem)
-- =====================================================
INSERT INTO accounts_orderitem (id, order_id, product_id, quantity, price) VALUES
(1,   1,  1, 2, 12000), (2,   1,  3, 1, 14000),       -- Order 1: 2 trays eggs + 1 Kienyeji
(3,   2,  5, 1, 6500),  (4,   2,  6, 1, 22000),       -- Order 2: Free range eggs + Dressed chicken
(5,   3,  7, 3, 8500),                                -- Order 3: Brew ingredients x3
(6,   4,  1, 1, 12000),                               -- Order 4: 1 tray eggs
(7,   5,  4, 1, 45000), (8,   5,  5, 1, 6500), (9,   5,  10, 1, 12000), -- Order 5: Feed + eggs + premix
(10,  6,  6, 1, 22000), (11,  6,  10, 1, 12000),     -- Order 6: Chicken + premix
(12,  7,  5, 2, 6500),                                -- Order 7: Free range eggs x2
(13,  8,  2, 1, 18500), (14,  8,  10, 1, 12000),     -- Order 8: Broiler + premix
(15,  9,  7, 1, 8500),                                -- Order 9: Brew ingredients
(16,  10, 3, 1, 14000), (17,  10, 4, 1, 45000),      -- Order 10: Kienyeji + feed
(18,  11, 2, 1, 18500),                               -- Order 11: Broiler
(19,  12, 6, 2, 22000),                               -- Order 12: Dressed chicken x2
(20,  13, 7, 3, 8500),  (21,  13, 5, 1, 6500),       -- Order 13: Brew x3 + eggs
(22,  14, 1, 2, 12000),                               -- Order 14: Eggs x2 trays
(23,  15, 6, 1, 22000), (24,  15, 5, 1, 6500),       -- Order 15: Chicken + eggs
(25,  16, 7, 1, 8500),                                -- Order 16: Brew
(26,  17, 4, 1, 45000),                               -- Order 17: Feed
(27,  18, 5, 1, 6500),                                -- Order 18: Eggs
(28,  19, 10, 1, 12000),                              -- Order 19: Vitamin premix
(29,  20, 8, 1, 38000),                               -- Order 20: Layers mash
(30,  21, 7, 1, 8500),                                -- Order 21: Brew
(31,  22, 2, 1, 18500), (32,  22, 1, 1, 12000),      -- Order 22: Broiler + eggs
(33,  23, 6, 1, 22000),                               -- Order 23: Dressed chicken
(34,  24, 1, 2, 12000), (35,  24, 5, 1, 6500),       -- Order 24 (cancelled): Eggs x2 + free range
(36,  25, 7, 1, 8500),                                -- Order 25 (cancelled): Brew
(37,  26, 3, 1, 14000), (38,  26, 4, 1, 45000),      -- Order 26: Kienyeji + feed
(39,  27, 7, 2, 8500),                                -- Order 27: Brew x2
(40,  28, 5, 2, 6500),                                -- Order 28: Free range eggs x2
(41,  29, 2, 2, 18500), (42,  29, 3, 1, 14000), (43, 29, 1, 1, 12000), -- Order 29: Broiler x2 + Kienyeji + eggs
(44,  30, 9, 1, 25000),                               -- Order 30: Day-old chicks
(45,  31, 10, 1, 12000),                              -- Order 31: Vitamin premix
(46,  32, 5, 1, 6500),                                -- Order 32: Free range eggs
(47,  33, 4, 1, 45000),                               -- Order 33: Feed
(48,  34, 5, 1, 6500),                                -- Order 34: Free range eggs
(49,  35, 2, 1, 18500);                               -- Order 35: Broiler

-- =====================================================
-- 10. DELIVERIES (deliveries_delivery)
-- =====================================================
INSERT INTO deliveries_delivery (id, delivery_person_id, status, started_at, completed_at, distance_km, earnings, created_at) VALUES
(1, 1, 'completed', NOW() - INTERVAL '30 days', NOW() - INTERVAL '29 days 4 hours', 12.4, 5000, NOW() - INTERVAL '30 days'),
(2, 2, 'completed', NOW() - INTERVAL '28 days', NOW() - INTERVAL '27 days 3 hours', 8.1,  3500, NOW() - INTERVAL '28 days'),
(3, 1, 'completed', NOW() - INTERVAL '27 days', NOW() - INTERVAL '26 days 3 hours', 6.5,  2800, NOW() - INTERVAL '27 days'),
(4, 2, 'completed', NOW() - INTERVAL '25 days', NOW() - INTERVAL '24 days 2 hours', 10.2, 4200, NOW() - INTERVAL '25 days'),
(5, 1, 'completed', NOW() - INTERVAL '24 days', NOW() - INTERVAL '23 days 5 hours', 15.0, 6000, NOW() - INTERVAL '24 days'),
(6, 2, 'completed', NOW() - INTERVAL '22 days', NOW() - INTERVAL '21 days 3 hours', 7.8,  3200, NOW() - INTERVAL '22 days'),
(7, 1, 'completed', NOW() - INTERVAL '21 days', NOW() - INTERVAL '20 days 4 hours', 9.3,  3800, NOW() - INTERVAL '21 days'),
(8, 1, 'completed', NOW() - INTERVAL '20 days', NOW() - INTERVAL '19 days 3 hours', 11.5, 4800, NOW() - INTERVAL '20 days'),
(9, 2, 'completed', NOW() - INTERVAL '19 days', NOW() - INTERVAL '18 days 2 hours', 5.2,  2200, NOW() - INTERVAL '19 days'),
(10, 1, 'completed', NOW() - INTERVAL '18 days', NOW() - INTERVAL '17 days 4 hours', 14.2, 5500, NOW() - INTERVAL '18 days'),
(11, 2, 'completed', NOW() - INTERVAL '16 days', NOW() - INTERVAL '15 days 3 hours', 6.8,  2900, NOW() - INTERVAL '16 days'),
(12, 1, 'completed', NOW() - INTERVAL '11 days', NOW() - INTERVAL '10 days 4 hours', 13.6, 5200, NOW() - INTERVAL '11 days'),
(13, 2, 'completed', NOW() - INTERVAL '6 days', NOW() - INTERVAL '5 days 2 hours',   7.0,  3000, NOW() - INTERVAL '6 days'),
(14, 1, 'in_transit', NOW() - INTERVAL '14 days', NULL, 8.5,  3600, NOW() - INTERVAL '14 days'),
(15, 2, 'in_transit', NOW() - INTERVAL '13 days', NULL, 6.2,  2600, NOW() - INTERVAL '13 days'),
(16, 1, 'in_transit', NOW() - INTERVAL '12 days', NULL, 9.8,  4000, NOW() - INTERVAL '12 days');

-- Link deliveries to orders (update the delivery_id in orders)
UPDATE accounts_order SET delivery_id = 1  WHERE id = 1;
UPDATE accounts_order SET delivery_id = 2  WHERE id = 2;
UPDATE accounts_order SET delivery_id = 3  WHERE id = 3;
UPDATE accounts_order SET delivery_id = 4  WHERE id = 4;
UPDATE accounts_order SET delivery_id = 5  WHERE id = 5;
UPDATE accounts_order SET delivery_id = 6  WHERE id = 6;
UPDATE accounts_order SET delivery_id = 7  WHERE id = 7;
UPDATE accounts_order SET delivery_id = 8  WHERE id = 8;
UPDATE accounts_order SET delivery_id = 9  WHERE id = 9;
UPDATE accounts_order SET delivery_id = 10 WHERE id = 10;
UPDATE accounts_order SET delivery_id = 11 WHERE id = 28;
UPDATE accounts_order SET delivery_id = 12 WHERE id = 29;
UPDATE accounts_order SET delivery_id = 13 WHERE id = 30;
UPDATE accounts_order SET delivery_id = 14 WHERE id = 11;
UPDATE accounts_order SET delivery_id = 15 WHERE id = 12;
UPDATE accounts_order SET delivery_id = 16 WHERE id = 13;

-- =====================================================
-- 11. DELIVERY LOGS (deliveries_deliverylog)
-- GPS tracking points along routes
-- =====================================================
INSERT INTO deliveries_deliverylog (id, delivery_id, lat, lng, timestamp) VALUES
-- Delivery 1: Premium Poultry (Ind. Zone B) → Kariakoo
(1,  1, -6.8000, 39.2700, NOW() - INTERVAL '30 days'),
(2,  1, -6.8050, 39.2720, NOW() - INTERVAL '30 days' + INTERVAL '10 minutes'),
(3,  1, -6.8100, 39.2750, NOW() - INTERVAL '30 days' + INTERVAL '20 minutes'),
(4,  1, -6.8150, 39.2780, NOW() - INTERVAL '30 days' + INTERVAL '30 minutes'),
(5,  1, -6.8194, 39.2802, NOW() - INTERVAL '30 days' + INTERVAL '40 minutes'),

-- Delivery 2: Mbezi Fresh → Mchafukoge
(6,  2, -6.7400, 39.2000, NOW() - INTERVAL '28 days'),
(7,  2, -6.7500, 39.2100, NOW() - INTERVAL '28 days' + INTERVAL '15 minutes'),
(8,  2, -6.7700, 39.2300, NOW() - INTERVAL '28 days' + INTERVAL '30 minutes'),
(9,  2, -6.7900, 39.2500, NOW() - INTERVAL '28 days' + INTERVAL '45 minutes'),
(10, 2, -6.8150, 39.2750, NOW() - INTERVAL '28 days' + INTERVAL '60 minutes'),

-- Delivery 14: In-transit, Mikocheni bound
(11, 14, -6.8000, 39.2700, NOW() - INTERVAL '14 days'),
(12, 14, -6.7900, 39.2650, NOW() - INTERVAL '14 days' + INTERVAL '10 minutes'),
(13, 14, -6.7800, 39.2620, NOW() - INTERVAL '14 days' + INTERVAL '20 minutes'),
(14, 14, -6.7700, 39.2600, NOW() - INTERVAL '14 days' + INTERVAL '30 minutes'),

-- Delivery 15: In-transit, Tandale bound
(15, 15, -6.7400, 39.2000, NOW() - INTERVAL '13 days'),
(16, 15, -6.7500, 39.2100, NOW() - INTERVAL '13 days' + INTERVAL '12 minutes'),
(17, 15, -6.7600, 39.2200, NOW() - INTERVAL '13 days' + INTERVAL '25 minutes'),
(18, 15, -6.7700, 39.2300, NOW() - INTERVAL '13 days' + INTERVAL '37 minutes'),
(19, 15, -6.7900, 39.2450, NOW() - INTERVAL '13 days' + INTERVAL '50 minutes'),

-- Delivery 16: In-transit, Kivukoni bound
(20, 16, -6.8200, 39.2800, NOW() - INTERVAL '12 days'),
(21, 16, -6.8150, 39.2830, NOW() - INTERVAL '12 days' + INTERVAL '8 minutes'),
(22, 16, -6.8100, 39.2860, NOW() - INTERVAL '12 days' + INTERVAL '16 minutes'),
(23, 16, -6.8050, 39.2900, NOW() - INTERVAL '12 days' + INTERVAL '25 minutes');

-- =====================================================
-- Reset sequences to max IDs (safe)
-- =====================================================
SELECT setval('auth_user_id_seq',                  (SELECT MAX(id) FROM auth_user));
SELECT setval('accounts_profile_id_seq',           (SELECT MAX(id) FROM accounts_profile));
SELECT setval('accounts_supplier_id_seq',          (SELECT MAX(id) FROM accounts_supplier));
SELECT setval('accounts_customer_id_seq',          (SELECT MAX(id) FROM accounts_customer));
SELECT setval('accounts_deliveryperson_id_seq',   (SELECT MAX(id) FROM accounts_deliveryperson));
SELECT setval('accounts_product_id_seq',           (SELECT MAX(id) FROM accounts_product));
SELECT setval('accounts_order_id_seq',             (SELECT MAX(id) FROM accounts_order));
SELECT setval('accounts_orderitem_id_seq',         (SELECT MAX(id) FROM accounts_orderitem));
SELECT setval('deliveries_delivery_id_seq',        (SELECT MAX(id) FROM deliveries_delivery));
SELECT setval('deliveries_deliverylog_id_seq',    (SELECT MAX(id) FROM deliveries_deliverylog));

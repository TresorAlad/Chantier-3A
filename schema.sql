-- Extension pour la génération des UUID (Identifiants uniques et anonymes des billets pour le QR Code)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- CATALOGUE & INFRASTRUCTURE

CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TYPE event_status AS ENUM ('brouillon', 'publié', 'annulé');

CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    organization_id INT NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    status event_status DEFAULT 'brouillon',
    start_date TIMESTAMP
    WITH
        TIME ZONE NOT NULL,
        created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ticket_types (
    id SERIAL PRIMARY KEY,
    event_id INT NOT NULL REFERENCES events (id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL, -- Formules (Standard, VIP) & Options payantes
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    capacity INT NOT NULL CHECK (capacity >= 0), -- Jauge maximale (Anti-survente)
    is_option BOOLEAN DEFAULT FALSE, -- TRUE si c'est une option payante (Nexus Night, Cocktail VIP, etc.)
    sales_start TIMESTAMP
    WITH
        TIME ZONE,
        sales_end TIMESTAMP
    WITH
        TIME ZONE,
        created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- TRANSACTIONNEL (Fidèle à la Figure 7 avec order_items)

CREATE TYPE order_status AS ENUM ('en_attente', 'payé', 'échoué');

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    status order_status DEFAULT 'en_attente',
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table intermédiaire / Pivot imposée par le schéma officiel de l'architecture
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders (id) ON DELETE CASCADE,
    ticket_type_id INT NOT NULL REFERENCES ticket_types (id) ON DELETE RESTRICT,
    quantity INT NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10, 2) NOT NULL, -- Prix figé au moment de l'achat
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders (id) ON DELETE RESTRICT,
    gateway_name VARCHAR(50) NOT NULL, -- FedaPay, KKiaPay, PayGate, Mobile Money
    transaction_reference VARCHAR(255) NOT NULL UNIQUE,
    gateway_response JSONB, -- Payload brut du webhook pour traçabilité
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

--BILLETS SÉCURISÉS

CREATE TYPE ticket_usage_status AS ENUM ('non_utilise', 'utilise');

CREATE TABLE tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4 (),
    order_item_id INT NOT NULL REFERENCES order_items (id) ON DELETE RESTRICT,
    signature_reference TEXT NOT NULL UNIQUE, -- Hash HMAC géré contre la falsification
    status ticket_usage_status DEFAULT 'non_utilise',
    created_at TIMESTAMP
    WITH
        TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- INDEXATION DE PERFORMANCE (Exigence de traitement sous quelques ms)

CREATE INDEX idx_ticket_types_lookup ON ticket_types (event_id, is_option);

CREATE INDEX idx_order_items_join ON order_items (order_id, ticket_type_id);

CREATE INDEX idx_orders_analytics ON orders (status, created_at DESC);

CREATE INDEX idx_tickets_security ON tickets (signature_reference);
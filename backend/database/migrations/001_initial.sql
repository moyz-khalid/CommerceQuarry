-- Initial migration: core tables for CommerceQuarry

-- Users (Supabase Auth table not created here; placeholder)
CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY,
    email text NOT NULL UNIQUE,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE scans (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES users(id) ON DELETE CASCADE,
    mode text NOT NULL,
    config jsonb NOT NULL,
    status text NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

CREATE TABLE scan_logs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id uuid REFERENCES scans(id) ON DELETE CASCADE,
    level text NOT NULL,
    message text NOT NULL,
    timestamp timestamp with time zone DEFAULT now()
);

CREATE TABLE amazon_products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    asin text NOT NULL UNIQUE,
    title text,
    brand text,
    price numeric,
    data jsonb,
    fetched_at timestamp with time zone DEFAULT now()
);

CREATE TABLE supplier_products (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_name text NOT NULL,
    supplier_sku text NOT NULL,
    title text,
    price numeric,
    data jsonb,
    fetched_at timestamp with time zone DEFAULT now()
);

CREATE TABLE product_matches (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id uuid REFERENCES scans(id) ON DELETE CASCADE,
    amazon_product_id uuid REFERENCES amazon_products(id),
    supplier_product_id uuid REFERENCES supplier_products(id),
    deterministic_score numeric,
    ai_score numeric,
    final_confidence numeric,
    match_type text,
    explanation text,
    manual_review boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE scan_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id uuid REFERENCES product_matches(id) ON DELETE CASCADE,
    profit numeric,
    roi numeric,
    margin numeric,
    best_fulfillment_method text,
    calculation_status text,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE fee_profiles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL UNIQUE,
    description text,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE fee_profile_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id uuid REFERENCES fee_profiles(id) ON DELETE CASCADE,
    type text NOT NULL,
    amount numeric NOT NULL,
    unit text,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE marketplace_fee_schedules (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace text NOT NULL,
    fee_data jsonb NOT NULL,
    effective_date date NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE supplier_integrations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_name text NOT NULL,
    config jsonb,
    enabled boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now()
);

CREATE TABLE user_settings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES users(id) ON DELETE CASCADE,
    settings jsonb,
    updated_at timestamp with time zone DEFAULT now()
);

-- Add indexes for common lookups
CREATE INDEX IF NOT EXISTS idx_scans_user ON scans(user_id);
CREATE INDEX IF NOT EXISTS idx_amazon_asin ON amazon_products(asin);
CREATE INDEX IF NOT EXISTS idx_supplier_sku ON supplier_products(supplier_sku);

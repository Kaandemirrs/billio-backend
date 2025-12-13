-- ===================================================
-- MIGRATION: 003_create_services_and_plans.sql
-- AMAÇ: 'predefined_bills' yerine 'services' ve 'service_plans' ekler.
-- BU, "AI/Cache Hibrit Modeli" için temel altyapıdır.
-- ===================================================

-- 1. Tablo: services (Eski predefined_bills'in yerini alır)
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN (
        'entertainment', 'utilities', 'productivity', 'health', 'finance', 'education', 'other'
    )),
    logo_url TEXT,
    primary_color TEXT DEFAULT '#6366f1',
    secondary_color TEXT DEFAULT '#ffffff',
    is_popular BOOLEAN DEFAULT FALSE,
    keywords TEXT[], -- Arama için (örn: ['netflix', 'dizi', 'film'])
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index'ler (services)
CREATE INDEX idx_services_name ON services(name);
CREATE INDEX idx_services_category ON services(category);
CREATE INDEX idx_services_is_popular ON services(is_popular);

-- updated_at trigger (services)
CREATE TRIGGER update_services_updated_at
BEFORE UPDATE ON services
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 2. Tablo: service_plans (AI'ın dolduracağı "Mühendislik Harikası" kalbi)
CREATE TABLE service_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    -- 'services' tablosuna bağlantı
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    plan_name TEXT NOT NULL, -- Örn: "Premium Plan", "Aile Planı"
    plan_identifier TEXT NOT NULL, -- AI sorgusu için (örn: "netflix-premium-tr")
    -- AI Cron Job tarafından doldurulacak kritik alanlar
    cached_price DECIMAL(10, 2), -- AI'ın bulduğu fiyat (örn: 229.99)
    currency TEXT CHECK (currency IN ('TRY', 'USD', 'EUR')),
    last_updated_ai TIMESTAMPTZ, -- AI'ın bu fiyatı en son güncellediği tarih
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index'ler (service_plans)
CREATE INDEX idx_service_plans_service_id ON service_plans(service_id);
CREATE INDEX idx_service_plans_plan_identifier ON service_plans(plan_identifier);
CREATE UNIQUE INDEX idx_service_plans_service_id_plan_identifier ON service_plans(service_id, plan_identifier);

-- updated_at trigger (service_plans)
CREATE TRIGGER update_service_plans_updated_at
BEFORE UPDATE ON service_plans
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Yorumlar
COMMENT ON TABLE services IS 'AI tarafından taranacak ana servisler (Netflix, Spotify vb.)';
COMMENT ON TABLE service_plans IS 'Servislerin planları ve AI tarafından önbelleğe alınan fiyatları.';
COMMENT ON COLUMN service_plans.cached_price IS 'Arka plan RAG Cron Job''u tarafından doldurulur.';
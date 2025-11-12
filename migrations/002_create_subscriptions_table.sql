-- ===================================================
-- MIGRATION: 002_create_subscriptions_table.sql
-- (Proje bütünlüğü için sonradan eklendi)
-- ===================================================
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN (
        'entertainment', 'utilities', 'productivity', 'health', 'finance', 'education', 'other'
    )),
    amount DECIMAL(10,2) NOT NULL CHECK (amount >= 0),
    currency TEXT DEFAULT 'TRY' CHECK (currency IN ('TRY', 'USD', 'EUR')),
    billing_cycle TEXT NOT NULL DEFAULT 'monthly' CHECK (billing_cycle IN (
        'daily', 'weekly', 'monthly', 'yearly'
    )),
    billing_day INTEGER CHECK (billing_day >= 1 AND billing_day <= 31),
    start_date DATE NOT NULL,
    next_payment_date DATE,
    logo_url TEXT,
    color TEXT DEFAULT '#6366f1',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_is_active ON subscriptions(is_active);
CREATE INDEX idx_subscriptions_category ON subscriptions(category);
CREATE INDEX idx_subscriptions_next_payment_date ON subscriptions(next_payment_date);
CREATE INDEX idx_subscriptions_user_active ON subscriptions(user_id, is_active);

CREATE TRIGGER update_subscriptions_updated_at
BEFORE UPDATE ON subscriptions
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE FUNCTION calculate_next_payment_date()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.next_payment_date IS NULL THEN
        CASE NEW.billing_cycle
            WHEN 'daily' THEN NEW.next_payment_date := NEW.start_date + INTERVAL '1 day';
            WHEN 'weekly' THEN NEW.next_payment_date := NEW.start_date + INTERVAL '1 week';
            WHEN 'monthly' THEN NEW.next_segment_date := NEW.start_date + INTERVAL '1 month';
            WHEN 'yearly' THEN NEW.next_payment_date := NEW.start_date + INTERVAL '1 year';
        END CASE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_next_payment_date
BEFORE INSERT ON subscriptions
FOR EACH ROW
EXECUTE FUNCTION calculate_next_payment_date();
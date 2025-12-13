-- ===================================================
-- MIGRATION: 004_link_subscriptions_to_plans.sql
-- AMAÇ: "Zam Uyarısı" (Senaryo 2) için "Kayıp Parça"yı ekler.
-- 'subscriptions' tablosunu 'service_plans' tablosuna bağlar.
-- ===================================================
ALTER TABLE subscriptions ADD COLUMN service_plan_id UUID REFERENCES service_plans(id) ON DELETE SET NULL;

-- Bu sütun null olabilir (NULLABLE), çünkü kullanıcı
-- "AI Robotu"nda olmayan özel bir fatura da (örn: "Ev Kirası") ekleyebilir.

CREATE INDEX idx_subscriptions_service_plan_id ON subscriptions(service_plan_id);

COMMENT ON COLUMN subscriptions.service_plan_id IS 'AI fiyat takibi için service_plans.id''ye bağlanır (Nullable)';
-- 1. CRÉATION DU CACHE ANALYTIQUE (Vue Matérialisée)

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_dashboard_financial_report AS
SELECT 
    o.id AS order_id,
    o.user_email AS participant_email,
    o.status AS order_status,
    COALESCE(p.gateway_name, 'Non spécifié') AS payment_gateway,
    COALESCE(p.transaction_reference, 'Aucune') AS transaction_ref,
    tt.name AS product_name,
    CASE 
        WHEN tt.is_option THEN 'Option Payante'
        ELSE 'Formule Pass'
    END AS product_category,
    oi.quantity AS ordered_quantity,
    oi.unit_price AS unit_price_fcfa,
    (oi.quantity * oi.unit_price) AS line_total_fcfa,
    o.created_at AS purchase_date
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
JOIN ticket_types tt ON oi.ticket_type_id = tt.id
LEFT JOIN payments p ON p.order_id = o.id
WHERE o.status::text IN ('payé', 'paye', 'ordered');

-- 2. INDEXATION DE LA VUE MATÉRIALISÉE
-- L'index unique est obligatoire pour permettre un rafraîchissement concurrent (sans bloquer les lectures).
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_dashboard_unique ON mv_dashboard_financial_report (order_id, product_name);

-- 3. PROCÉDURE DE RAFRAÎCHISSEMENT DU DASHBOARD
-- Cette fonction sera appelée par l'API Go ou par un worker en tâche de fond.
CREATE OR REPLACE FUNCTION refresh_dashboard_analytics()
RETURNS VOID AS $$
BEGIN
    -- CONCURRENTLY permet aux administrateurs de continuer à lire le dashboard 
    -- et d'exporter les CSV pendant que les données se mettent à jour.
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_dashboard_financial_report;
END;
$$ LANGUAGE plpgsql;
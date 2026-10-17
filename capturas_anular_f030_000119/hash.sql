SELECT 'todo=' || md5(string_agg(t, '' ORDER BY t)) FROM (
  SELECT 's'||row_to_json(x)::text t FROM sale x UNION ALL SELECT 'l'||row_to_json(x)::text FROM sale_line x
  UNION ALL SELECT 'm'||row_to_json(x)::text FROM inventory_movement x UNION ALL SELECT 'j'||row_to_json(x)::text FROM journal_entry x
  UNION ALL SELECT 'jl'||row_to_json(x)::text FROM journal_entry_line x UNION ALL SELECT 'a'||row_to_json(x)::text FROM audit_log x
  UNION ALL SELECT 'p'||row_to_json(x)::text FROM fiscal_period x UNION ALL SELECT 'pl'||row_to_json(x)::text FROM payment_line x
  UNION ALL SELECT 'w'||row_to_json(x)::text FROM sales_workflow x) q;
SELECT 'F030-000120+asiento=' || md5(string_agg(t, '' ORDER BY t)) FROM (
  SELECT row_to_json(x)::text t FROM sale x WHERE id='af-s120' UNION ALL SELECT row_to_json(x)::text FROM sale_line x WHERE sale_id='af-s120'
  UNION ALL SELECT row_to_json(x)::text FROM journal_entry x WHERE id='af-j120' UNION ALL SELECT row_to_json(x)::text FROM journal_entry_line x WHERE entry_id='af-j120'
  UNION ALL SELECT row_to_json(x)::text FROM inventory_movement x WHERE reference_id='af-s120') q;

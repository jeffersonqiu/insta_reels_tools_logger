-- Read-only checks to run in the production Supabase SQL Editor after migration 005.
-- The first result must contain eight rows with ok = true.
WITH item_table AS (
    SELECT to_regclass('public.knowledge_items') AS oid
), video_column AS (
    SELECT attnum FROM pg_attribute
    WHERE attrelid = to_regclass('public.knowledge_items') AND attname = 'video_id'
), item_id_column AS (
    SELECT attnum FROM pg_attribute
    WHERE attrelid = to_regclass('public.knowledge_items') AND attname = 'id'
), source_id_column AS (
    SELECT attnum FROM pg_attribute
    WHERE attrelid = to_regclass('public.videos') AND attname = 'id'
)
SELECT 'table exists' AS check_name, oid IS NOT NULL AS ok FROM item_table
UNION ALL
SELECT 'primary key on id', EXISTS (
    SELECT 1 FROM pg_constraint, item_table
    WHERE conrelid = item_table.oid AND contype = 'p'
      AND conkey = ARRAY[(SELECT attnum FROM item_id_column)]::smallint[]
)
UNION ALL
SELECT 'one item per video', EXISTS (
    SELECT 1 FROM pg_constraint, item_table
    WHERE conrelid = item_table.oid AND contype = 'u'
      AND conkey = ARRAY[(SELECT attnum FROM video_column)]::smallint[]
)
UNION ALL
SELECT 'video foreign key cascades', EXISTS (
    SELECT 1 FROM pg_constraint, item_table
    WHERE conrelid = item_table.oid AND contype = 'f'
      AND confrelid = to_regclass('public.videos') AND confdeltype = 'c' AND convalidated
      AND conkey = ARRAY[(SELECT attnum FROM video_column)]::smallint[]
      AND confkey = ARRAY[(SELECT attnum FROM source_id_column)]::smallint[]
)
UNION ALL
SELECT 'row security enabled', EXISTS (
    SELECT 1 FROM pg_class, item_table WHERE pg_class.oid = item_table.oid AND relrowsecurity
)
UNION ALL
SELECT 'no client row policies', NOT EXISTS (
    SELECT 1 FROM pg_policy, item_table WHERE polrelid = item_table.oid
)
UNION ALL
SELECT 'newest-first index', EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'knowledge_items'
      AND indexname = 'knowledge_items_created_at_idx' AND indexdef LIKE '%(created_at DESC)%'
)
UNION ALL
SELECT 'service role can read and write', COALESCE((
    SELECT bool_and(has_table_privilege('service_role', oid, privilege))
    FROM item_table CROSS JOIN unnest(ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']) AS privileges(privilege)
), false);

-- Expect 14 columns. Confirm their types, nullability and defaults against migration 005.
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND table_name = 'knowledge_items'
ORDER BY ordinal_position;

-- Expect zero rows: uniqueness is also enforced by the schema.
SELECT video_id, count(*) AS item_count
FROM public.knowledge_items
GROUP BY video_id HAVING count(*) > 1;

-- Empty results/count zero immediately after migration are fine: there is no automatic backfill.
SELECT count(*) AS knowledge_item_count FROM public.knowledge_items;

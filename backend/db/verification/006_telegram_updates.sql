-- Expect all five checks true; then five metadata columns and no message contents.
SELECT 'table exists' AS check_name, to_regclass('public.telegram_updates') IS NOT NULL AS ok
UNION ALL SELECT 'update ID primary key', EXISTS (
    SELECT 1 FROM pg_constraint c JOIN pg_attribute a ON a.attrelid=c.conrelid
    WHERE c.conrelid=to_regclass('public.telegram_updates') AND c.contype='p'
      AND a.attname='update_id' AND c.conkey=ARRAY[a.attnum]::smallint[])
UNION ALL SELECT 'row security enabled', EXISTS (
    SELECT 1 FROM pg_class WHERE oid=to_regclass('public.telegram_updates') AND relrowsecurity)
UNION ALL SELECT 'no client policies', NOT EXISTS (
    SELECT 1 FROM pg_policy WHERE polrelid=to_regclass('public.telegram_updates'))
UNION ALL SELECT 'service role can read and write', COALESCE((
    SELECT bool_and(has_table_privilege('service_role', to_regclass('public.telegram_updates'), privilege))
    FROM unnest(ARRAY['SELECT','INSERT','UPDATE']) AS privileges(privilege)), false);

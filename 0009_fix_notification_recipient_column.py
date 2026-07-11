from django.db import migrations


# The 0007_notification migration was recorded as applied in django_migrations,
# but the actual accounts_notification table on the production database is
# missing the recipient_id column (and its foreign key / index). This repair
# migration adds it back directly via SQL. It uses SeparateDatabaseAndState
# with empty state_operations because Django's migration STATE already
# believes the 'recipient' field exists (from 0007) - we only need to fix
# the real database schema to match that state.
#
# All statements are written to be safe to re-run (IF NOT EXISTS / guards),
# in case this migration is ever re-applied.

FORWARD_SQL = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'accounts_notification' AND column_name = 'recipient_id'
    ) THEN
        ALTER TABLE accounts_notification ADD COLUMN recipient_id bigint;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'accounts_notification_recipient_id_fk'
    ) THEN
        ALTER TABLE accounts_notification
            ADD CONSTRAINT accounts_notification_recipient_id_fk
            FOREIGN KEY (recipient_id) REFERENCES accounts_profile(id)
            ON DELETE CASCADE
            DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS accounts_notification_recipient_id_idx
    ON accounts_notification (recipient_id);

-- The model requires recipient to be NOT NULL. Any pre-existing rows
-- (from before this fix) would have NULL recipient_id and are unusable
-- broken data, so remove them before enforcing NOT NULL.
DELETE FROM accounts_notification WHERE recipient_id IS NULL;

ALTER TABLE accounts_notification ALTER COLUMN recipient_id SET NOT NULL;
"""

REVERSE_SQL = """
ALTER TABLE accounts_notification DROP CONSTRAINT IF EXISTS accounts_notification_recipient_id_fk;
DROP INDEX IF EXISTS accounts_notification_recipient_id_idx;
ALTER TABLE accounts_notification DROP COLUMN IF EXISTS recipient_id;
"""


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_order_delivery_area_order_delivery_city_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunSQL(sql=FORWARD_SQL, reverse_sql=REVERSE_SQL),
            ],
        ),
    ]

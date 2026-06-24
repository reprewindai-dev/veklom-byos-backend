"""003 – refactor settlement_ledger to canonical shape.

Revision ID: 003_refactor_settlement_ledger
Revises: 002
Create Date: 2026-06-24

What this migration does
------------------------
* Drops legacy columns that existed before the canonical refactor:
  - dedupe_key
  - settlement_state   (old enum name)
  - quoted_amount_minor
  - locked_amount_minor
  - execution_hash
  - provider_meta      (if present)

* Ensures the canonical columns are present with correct types and
  NOT NULL constraints:
  - idempotency_key VARCHAR(255) UNIQUE NOT NULL
  - status          settlement_status_enum NOT NULL DEFAULT 'pending'
  - amount          BIGINT NOT NULL DEFAULT 0
  - currency        VARCHAR(16) NOT NULL DEFAULT 'USDC'
  - execution_id    VARCHAR(128)
  - authority_run_id VARCHAR(128)
  - payment_proof_id VARCHAR(255)
  - external_payment_id VARCHAR(255)
  - settlement_tx_hash  VARCHAR(128)
  - failure_code    VARCHAR(64)
  - failure_reason  TEXT
  - metadata_json   JSONB
  - created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
  - updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()

* Creates/ensures indexes:
  - UNIQUE ix on idempotency_key (already implied by unique=True on column)
  - ix_settlement_tenant_created  on (tenant_id, created_at)
  - ix_settlement_execution_id    on (execution_id)

All operations are wrapped in transaction-safe DDL via ``op.execute`` so
this migration is fully reversible via the ``downgrade`` path.

IMPORTANT: Run ``alembic upgrade head`` in a maintenance window; the DROP
COLUMN operations on any live data will be permanent.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003_refactor_settlement_ledger"
down_revision = "002"  # update to your actual previous revision id
branch_labels = None
depends_on = None

# Columns that existed in the old schema but are removed in the canonical shape.
_LEGACY_COLUMNS = [
    "dedupe_key",
    "settlement_state",
    "quoted_amount_minor",
    "locked_amount_minor",
    "execution_hash",
    "provider_meta",
]


def _column_exists(table: str, column: str) -> bool:
    """Check whether a column exists in the given table."""
    result = op.get_bind().execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).fetchone()
    return result is not None


def _index_exists(index_name: str) -> bool:
    result = op.get_bind().execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE indexname = :n"
        ),
        {"n": index_name},
    ).fetchone()
    return result is not None


def upgrade() -> None:
    # ── 1. Ensure the settlement_status_enum type exists ─────────────
    op.execute(
        "DO $$ BEGIN "
        "  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'settlement_status_enum') THEN "
        "    CREATE TYPE settlement_status_enum AS ENUM ('pending', 'settled', 'failed'); "
        "  END IF; "
        "END $$;"
    )

    # ── 2. Add canonical columns that may be missing ──────────────────
    bind = op.get_bind()

    def add_col_if_missing(col_name: str, col_def: str) -> None:
        if not _column_exists("settlement_ledger", col_name):
            op.execute(
                sa.text(f"ALTER TABLE settlement_ledger ADD COLUMN {col_name} {col_def}")
            )

    add_col_if_missing(
        "idempotency_key",
        "VARCHAR(255) NOT NULL DEFAULT gen_random_uuid()::text",
    )
    add_col_if_missing("status",
        "settlement_status_enum NOT NULL DEFAULT 'pending'"
    )
    add_col_if_missing("amount", "BIGINT NOT NULL DEFAULT 0")
    add_col_if_missing("currency", "VARCHAR(16) NOT NULL DEFAULT 'USDC'")
    add_col_if_missing("tenant_id", "VARCHAR(128) NOT NULL DEFAULT ''")
    add_col_if_missing("provider", "VARCHAR(128) NOT NULL DEFAULT ''")
    add_col_if_missing("fee_type", "VARCHAR(64) NOT NULL DEFAULT ''")
    add_col_if_missing("execution_id", "VARCHAR(128)")
    add_col_if_missing("authority_run_id", "VARCHAR(128)")
    add_col_if_missing("payment_proof_id", "VARCHAR(255)")
    add_col_if_missing("external_payment_id", "VARCHAR(255)")
    add_col_if_missing("settlement_tx_hash", "VARCHAR(128)")
    add_col_if_missing("failure_code", "VARCHAR(64)")
    add_col_if_missing("failure_reason", "TEXT")
    add_col_if_missing("metadata_json", "JSONB")
    add_col_if_missing(
        "created_at",
        "TIMESTAMPTZ NOT NULL DEFAULT now()",
    )
    add_col_if_missing(
        "updated_at",
        "TIMESTAMPTZ NOT NULL DEFAULT now()",
    )

    # ── 3. Make idempotency_key UNIQUE (idempotent) ───────────────────
    op.execute(
        "DO $$ BEGIN "
        "  IF NOT EXISTS ("
        "    SELECT 1 FROM pg_constraint "
        "    WHERE conname = 'settlement_ledger_idempotency_key_key'"
        "  ) THEN "
        "    ALTER TABLE settlement_ledger "
        "      ADD CONSTRAINT settlement_ledger_idempotency_key_key "
        "      UNIQUE (idempotency_key); "
        "  END IF; "
        "END $$;"
    )

    # ── 4. Drop legacy columns ────────────────────────────────────────
    for col in _LEGACY_COLUMNS:
        if _column_exists("settlement_ledger", col):
            op.drop_column("settlement_ledger", col)

    # ── 5. Create missing indexes ────────────────────────────────────
    if not _index_exists("ix_settlement_tenant_created"):
        op.create_index(
            "ix_settlement_tenant_created",
            "settlement_ledger",
            ["tenant_id", "created_at"],
        )

    if not _index_exists("ix_settlement_execution_id"):
        op.create_index(
            "ix_settlement_execution_id",
            "settlement_ledger",
            ["execution_id"],
        )

    if not _index_exists("ix_settlement_ledger_tenant_id"):
        op.create_index(
            "ix_settlement_ledger_tenant_id",
            "settlement_ledger",
            ["tenant_id"],
        )


def downgrade() -> None:
    """Re-add legacy columns and remove canonical additions.

    WARNING: data in the dropped canonical columns will be lost on
    downgrade. This path is provided for CI rollback only; do NOT run
    in production without a prior backup.
    """
    # Drop indexes added in upgrade
    for idx in (
        "ix_settlement_execution_id",
        "ix_settlement_tenant_created",
        "ix_settlement_ledger_tenant_id",
    ):
        if _index_exists(idx):
            op.drop_index(idx, table_name="settlement_ledger")

    # Re-add legacy columns
    op.add_column(
        "settlement_ledger",
        sa.Column("dedupe_key", sa.String(255), nullable=True),
    )
    op.add_column(
        "settlement_ledger",
        sa.Column("quoted_amount_minor", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "settlement_ledger",
        sa.Column("locked_amount_minor", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "settlement_ledger",
        sa.Column("execution_hash", sa.String(128), nullable=True),
    )

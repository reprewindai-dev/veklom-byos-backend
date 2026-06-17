# Agent-002 — REFERRAL SYSTEM ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** CRITICAL — Growth Blocking
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Build the complete referral system from scratch. Zero referral infrastructure exists. This is the viral loop.

## First Actions

```bash
cat backend/db/models.py  # understand existing schema
cat backend/apps/api/routers/auth.py  # hook into registration
ls backend/db/migrations/  # latest migration number
```

## Alembic Migration

```python
# Create: backend/db/migrations/versions/XXXX_add_referrals_table.py
def upgrade():
    op.create_table('referrals',
        sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('referrer_user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('referee_user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('referral_code', sa.String(12), unique=True, nullable=False),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('clicked_at', sa.TIMESTAMPTZ(), nullable=True),
        sa.Column('converted_at', sa.TIMESTAMPTZ(), nullable=True),
        sa.Column('reward_type', sa.String(50), nullable=True),
        sa.Column('reward_value', sa.Numeric(10,2), nullable=True),
        sa.Column('created_at', sa.TIMESTAMPTZ(), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_referrals_referrer', 'referrals', ['referrer_user_id'])
    op.create_index('idx_referrals_code', 'referrals', ['referral_code'])
```

## API Endpoints

```python
# Create: backend/apps/api/routers/referrals.py

GET  /api/v1/referrals/my-link      # get your referral link + stats
GET  /api/v1/referrals/track/{code} # public — track click, redirect to signup
POST /api/v1/referrals/apply        # apply referral code on signup
GET  /api/v1/admin/referrals/stats  # admin analytics
```

## Reward Config

```python
REFERRAL_REWARDS = {
    "referrer": {"type": "credits", "value": 10.00},   # $10 wallet credits
    "referee":  {"type": "discount", "value": 20.00}   # 20% off first month
}
```

## Tasks
1. Write Alembic migration + run `alembic upgrade head`
2. Create `backend/apps/api/routers/referrals.py` with all 4 endpoints
3. Register router in `backend/apps/api/main.py`
4. Hook referral apply into auth registration flow
5. Write tests: `backend/tests/test_referrals.py`
6. Update PROGRESS.md + PR

## Dependencies
- Agent-051 (Referral Activation) activates this system on Day 7

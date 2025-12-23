"""add_user_tier_and_created_at_indexes

Revision ID: 9f1a74577453
Revises: 001_initial_schema
Create Date: 2025-12-23 17:51:22.771098

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f1a74577453'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes on users.tier and users.created_at for improved query performance."""
    # Add index on tier column for filtering users by subscription tier
    op.create_index("ix_users_tier", "users", ["tier"])

    # Add index on created_at column for sorting users by creation date
    op.create_index("ix_users_created_at", "users", ["created_at"])


def downgrade() -> None:
    """Remove indexes on users.tier and users.created_at."""
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_tier", table_name="users")

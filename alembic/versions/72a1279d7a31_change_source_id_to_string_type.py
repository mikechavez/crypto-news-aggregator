"""Change source.id to String type

Revision ID: 72a1279d7a31
Revises: 57b8d8a2e535
Create Date: 2025-06-24 17:07:10.028428

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "72a1279d7a31"
down_revision: Union[str, Sequence[str], None] = "57b8d8a2e535"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop the foreign key constraint first
    op.drop_constraint("articles_source_id_fkey", "articles", type_="foreignkey")

    # Change the column type in articles first
    op.alter_column(
        "articles",
        "source_id",
        existing_type=sa.INTEGER(),
        type_=sa.String(),
        existing_nullable=True,
    )

    # Then change the type in sources
    op.alter_column(
        "sources",
        "id",
        existing_type=sa.INTEGER(),
        type_=sa.String(),
        existing_nullable=False,
    )

    # Recreate the foreign key constraint
    op.create_foreign_key(
        "articles_source_id_fkey", "articles", "sources", ["source_id"], ["id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the foreign key constraint
    op.drop_constraint("articles_source_id_fkey", "articles", type_="foreignkey")

    # Change the type back in sources first
    op.alter_column(
        "sources",
        "id",
        existing_type=sa.String(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )

    # Then change the type back in articles
    op.alter_column(
        "articles",
        "source_id",
        existing_type=sa.String(),
        type_=sa.INTEGER(),
        existing_nullable=True,
    )

    # Recreate the foreign key constraint
    op.create_foreign_key(
        "articles_source_id_fkey", "articles", "sources", ["source_id"], ["id"]
    )

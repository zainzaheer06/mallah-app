"""D2 catalog baseline — sources, restaurants, menu_sections, menu_items, promotions

Revision ID: 0003_d2_catalog_baseline
Revises: 0002_add_gender_and_dob
Create Date: 2026-05-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003_d2_catalog_baseline"
down_revision: Union[str, None] = "0002_add_gender_and_dob"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "restaurants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False, index=True),
        sa.Column("external_id", sa.String(100), nullable=False, index=True),
        sa.Column("chain_id", sa.String(100), nullable=True, index=True),
        sa.Column("chain_name", sa.String(300), nullable=True),
        sa.Column("name_en", sa.String(300), nullable=False),
        sa.Column("name_ar", sa.String(300), nullable=True),
        sa.Column("vertical", sa.String(50), nullable=True),
        sa.Column("cuisines", JSONB, nullable=True),
        sa.Column("rating", sa.Numeric(3, 2), nullable=True),
        sa.Column("rate_count", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("city", sa.String(80), nullable=True, index=True),
        sa.Column("district", sa.String(80), nullable=True),
        sa.Column("delivery_fee", sa.Numeric(10, 2), nullable=True),
        sa.Column("minimum_order_sar", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_range", sa.Integer(), nullable=True),
        sa.Column("eta_min", sa.Integer(), nullable=True),
        sa.Column("eta_max", sa.Integer(), nullable=True),
        sa.Column("cover_photo_url", sa.String(1000), nullable=True),
        sa.Column("deep_link_url", sa.String(1000), nullable=True),
        sa.Column("supports_pickup", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_most_loved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("admin_disabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_id", "external_id", name="uq_restaurant_source_external"),
    )
    op.create_index("ix_restaurants_lat_lng", "restaurants", ["latitude", "longitude"])

    op.create_table(
        "menu_sections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("restaurant_id", sa.Uuid(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source_section_id", sa.String(100), nullable=True),
        sa.Column("name_en", sa.String(300), nullable=False),
        sa.Column("name_ar", sa.String(300), nullable=True),
        sa.Column("layout", sa.String(30), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "menu_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("section_id", sa.Uuid(), sa.ForeignKey("menu_sections.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("restaurant_id", sa.Uuid(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("external_id", sa.String(100), nullable=True, index=True),
        sa.Column("name_en", sa.String(300), nullable=False),
        sa.Column("name_ar", sa.String(300), nullable=True),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("item_type", sa.String(20), nullable=False, server_default="PRODUCT"),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("list_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("discounted_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("discount_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("calories", sa.Integer(), nullable=True),
        sa.Column("popularity_text", sa.String(50), nullable=True),
        sa.Column("image_url", sa.String(1000), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "promotions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("restaurant_id", sa.Uuid(), sa.ForeignKey("restaurants.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("promo_type", sa.String(50), nullable=False),
        sa.Column("name_en", sa.String(500), nullable=False),
        sa.Column("name_ar", sa.String(500), nullable=True),
        sa.Column("category", sa.String(10), nullable=True),
        sa.Column("minimum_order_sar", sa.Numeric(10, 2), nullable=True),
        sa.Column("discount_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("discount_fixed_sar", sa.Numeric(10, 2), nullable=True),
        sa.Column("free_delivery", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("promotions")
    op.drop_table("menu_items")
    op.drop_table("menu_sections")
    op.drop_index("ix_restaurants_lat_lng", table_name="restaurants")
    op.drop_table("restaurants")
    op.drop_table("sources")
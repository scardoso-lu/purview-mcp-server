"""SQLAlchemy 2.0 ORM models for the Purview cache database.

These tables mirror the domain models (`Asset`, `LineageGraph`, `GlossaryTerm`,
`DataProduct`) that the MCP tools serve. The ETL upserts into them; the
Postgres-backed repositories read from them. Schema lives under the ``purview``
namespace. ``search_doc`` columns are generated ``tsvector`` columns so the ORM
never has to maintain them.
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

SCHEMA = "purview"

# Generated tsvector expression shared by searchable tables.
_ASSET_TSV = (
    "to_tsvector('simple', "
    "coalesce(name, '') || ' ' || coalesce(description, '') || ' ' "
    "|| coalesce(qualified_name, ''))"
)
_TERM_TSV = "to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(definition, ''))"
_PRODUCT_TSV = "to_tsvector('simple', coalesce(name, '') || ' ' || coalesce(description, ''))"


class Base(DeclarativeBase):
    pass


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_search_doc", "search_doc", postgresql_using="gin"),
        Index(
            "ix_assets_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index(
            "ix_assets_description_trgm",
            "description",
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
        Index("ix_assets_asset_type", "asset_type"),
        Index("ix_assets_update_time", "update_time"),
        Index("ix_assets_last_seen_run_id", "last_seen_run_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    asset_type: Mapped[str] = mapped_column(String, nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    endorsement: Mapped[str | None] = mapped_column(String, nullable=True)
    domain: Mapped[str | None] = mapped_column(String, nullable=True)
    qualified_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    collection: Mapped[str | None] = mapped_column(String, nullable=True)
    update_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    raw_attributes: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    search_doc: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed(_ASSET_TSV, persisted=True), nullable=True
    )
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    owners: Mapped[list["AssetOwner"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", lazy="selectin"
    )
    classifications: Mapped[list["Classification"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", lazy="selectin"
    )
    tags: Mapped[list["Tag"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", lazy="selectin"
    )
    data_quality: Mapped[list["DataQualityMetric"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan", lazy="selectin"
    )


class AssetOwner(Base):
    __tablename__ = "asset_owners"
    __table_args__ = ({"schema": SCHEMA},)

    asset_id: Mapped[str] = mapped_column(
        ForeignKey(f"{SCHEMA}.assets.id", ondelete="CASCADE"), primary_key=True
    )
    owner_id: Mapped[str] = mapped_column(String, primary_key=True)
    contact_type: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    email: Mapped[str | None] = mapped_column(String, nullable=True)

    asset: Mapped[Asset] = relationship(back_populates="owners")


class Classification(Base):
    __tablename__ = "classifications"
    __table_args__ = ({"schema": SCHEMA},)

    asset_id: Mapped[str] = mapped_column(
        ForeignKey(f"{SCHEMA}.assets.id", ondelete="CASCADE"), primary_key=True
    )
    classification: Mapped[str] = mapped_column(String, primary_key=True)

    asset: Mapped[Asset] = relationship(back_populates="classifications")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = ({"schema": SCHEMA},)

    asset_id: Mapped[str] = mapped_column(
        ForeignKey(f"{SCHEMA}.assets.id", ondelete="CASCADE"), primary_key=True
    )
    tag: Mapped[str] = mapped_column(String, primary_key=True)

    asset: Mapped[Asset] = relationship(back_populates="tags")


class DataQualityMetric(Base):
    __tablename__ = "data_quality_metrics"
    __table_args__ = ({"schema": SCHEMA},)

    asset_id: Mapped[str] = mapped_column(
        ForeignKey(f"{SCHEMA}.assets.id", ondelete="CASCADE"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)

    asset: Mapped[Asset] = relationship(back_populates="data_quality")


class LineageNode(Base):
    __tablename__ = "lineage_nodes"
    __table_args__ = (
        Index("ix_lineage_nodes_last_seen_run_id", "last_seen_run_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    asset_type: Mapped[str] = mapped_column(String, nullable=False, default="")
    qualified_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    last_seen_run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class LineageRelation(Base):
    __tablename__ = "lineage_relations"
    __table_args__ = (
        # relation_type is nullable, so a generated key column gives the unique
        # constraint a non-null target usable as an ON CONFLICT element.
        UniqueConstraint("from_id", "to_id", "rel_type_key", name="uq_lineage_relation"),
        Index("ix_lineage_relations_from_id", "from_id"),
        Index("ix_lineage_relations_to_id", "to_id"),
        Index("ix_lineage_relations_last_seen_run_id", "last_seen_run_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    from_id: Mapped[str] = mapped_column(String, nullable=False)
    to_id: Mapped[str] = mapped_column(String, nullable=False)
    relation_type: Mapped[str | None] = mapped_column(String, nullable=True)
    rel_type_key: Mapped[str] = mapped_column(
        String, Computed("coalesce(relation_type, '')", persisted=True)
    )
    last_seen_run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class GlossaryTerm(Base):
    __tablename__ = "glossary_terms"
    __table_args__ = (
        Index("ix_glossary_terms_search_doc", "search_doc", postgresql_using="gin"),
        Index(
            "ix_glossary_terms_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index("ix_glossary_terms_last_seen_run_id", "last_seen_run_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    qualified_name: Mapped[str] = mapped_column(String, nullable=False, default="")
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    long_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    examples: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    synonyms: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    stewards: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    experts: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    search_doc: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed(_TERM_TSV, persisted=True), nullable=True
    )
    last_seen_run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)


class DataProduct(Base):
    __tablename__ = "data_products"
    __table_args__ = (
        Index("ix_data_products_search_doc", "search_doc", postgresql_using="gin"),
        Index(
            "ix_data_products_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index("ix_data_products_domain_id", "domain_id"),
        Index("ix_data_products_last_seen_run_id", "last_seen_run_id"),
        {"schema": SCHEMA},
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    domain_id: Mapped[str | None] = mapped_column(String, nullable=True)
    domain_name: Mapped[str | None] = mapped_column(String, nullable=True)
    asset_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_product_type: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    search_doc: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed(_PRODUCT_TSV, persisted=True), nullable=True
    )
    last_seen_run_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    owners: Mapped[list["DataProductOwner"]] = relationship(
        back_populates="data_product", cascade="all, delete-orphan", lazy="selectin"
    )


class DataProductOwner(Base):
    __tablename__ = "data_product_owners"
    __table_args__ = ({"schema": SCHEMA},)

    data_product_id: Mapped[str] = mapped_column(
        ForeignKey(f"{SCHEMA}.data_products.id", ondelete="CASCADE"), primary_key=True
    )
    owner_id: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)

    data_product: Mapped[DataProduct] = relationship(back_populates="owners")


class EtlRun(Base):
    __tablename__ = "etl_runs"
    __table_args__ = ({"schema": SCHEMA},)

    run_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # "full" | "incremental"
    status: Mapped[str] = mapped_column(String, nullable=False)  # running|success|failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assets_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    terms_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    products_upserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deletes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    high_watermark: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

"""Shared parsers that turn raw Purview API responses into domain models.

These functions are the single source of truth for mapping Purview/Atlas JSON
into the domain models. Both the live Purview repositories and the ETL extractor
import them so the database holds exactly the same models the live path produces.
"""

from typing import Any

from purview_mcp.domain.models.asset import Asset, AssetOwner, DataQualityMetric
from purview_mcp.domain.models.data_product import DataProduct, DataProductOwner
from purview_mcp.domain.models.glossary import GlossaryTerm
from purview_mcp.domain.models.lineage import LineageNode


def _parse_asset(raw: dict[str, Any]) -> Asset:
    """Parse an entity-detail response (rich shape incl. data quality)."""
    attrs = raw.get("attributes", {})
    contacts = raw.get("contacts", {})
    owners: list[AssetOwner] = []
    for contact_type in ("Expert", "Owner"):
        for contact in contacts.get(contact_type, []):
            owners.append(
                AssetOwner(
                    id=contact.get("id", ""),
                    display_name=contact.get("info", ""),
                    email=contact.get("email") or contact.get("mail") or None,
                    contact_type=contact_type,
                )
            )

    meanings = attrs.get("meanings", [])
    tags = [m.get("displayText", "") for m in meanings if m.get("displayText")]

    dq_raw = attrs.get("dataQualityScore", {})
    dq_metrics: list[DataQualityMetric] = []
    if isinstance(dq_raw, dict):
        for metric_name, metric_val in dq_raw.items():
            dq_metrics.append(DataQualityMetric(name=metric_name, value=metric_val))

    label_raw = raw.get("labels", [])

    return Asset(
        id=raw.get("guid", ""),
        name=attrs.get("name", raw.get("name", "")),
        asset_type=raw.get("typeName", raw.get("entityType", "")),
        description=attrs.get("userDescription") or attrs.get("description"),
        owners=owners,
        classification=[c.get("typeName", "") for c in raw.get("classifications", [])],
        endorsement=attrs.get("endorsement"),
        domain=attrs.get("domain"),
        tags=tags + (label_raw if isinstance(label_raw, list) else []),
        qualified_name=attrs.get("qualifiedName", ""),
        collection=raw.get("collectionId"),
        data_quality=dq_metrics,
    )


def _parse_search_result(hit: dict[str, Any]) -> Asset:
    """Parse a search result hit (different shape from entity detail)."""
    contact_list: list[AssetOwner] = []
    for c in hit.get("contact", []):
        contact_list.append(
            AssetOwner(
                id=c.get("id", ""),
                display_name=c.get("info", ""),
                email=c.get("email") or c.get("mail") or None,
                contact_type=c.get("contactType", "Owner"),
            )
        )
    return Asset(
        id=hit.get("id", ""),
        name=hit.get("name", ""),
        asset_type=hit.get("entityType", ""),
        description=hit.get("userDescription") or hit.get("description"),
        owners=contact_list,
        classification=hit.get("classification", []),
        endorsement=hit.get("endorsement"),
        domain=hit.get("domain"),
        tags=hit.get("label", []),
        qualified_name=hit.get("qualifiedName", ""),
        collection=hit.get("collectionId"),
    )


def _parse_glossary_term(raw: dict[str, Any]) -> GlossaryTerm:
    attrs: dict[str, Any] = raw.get("attributes", raw)
    return GlossaryTerm(
        id=raw.get("guid", raw.get("termGuid", "")),
        name=attrs.get("name", raw.get("displayText", "")),
        qualified_name=attrs.get("qualifiedName", ""),
        definition=attrs.get("shortDescription") or attrs.get("definition"),
        status=attrs.get("status"),
        long_description=attrs.get("longDescription"),
        examples=attrs.get("examples", []) or [],
        synonyms=[s.get("displayText", "") for s in (attrs.get("synonyms") or [])],
        stewards=[s.get("id", "") for s in (attrs.get("stewards") or [])],
        experts=[e.get("id", "") for e in (attrs.get("experts") or [])],
    )


def _parse_data_product(raw: dict[str, Any]) -> DataProduct:
    props: dict[str, Any] = raw.get("properties", raw)
    owners: list[DataProductOwner] = []
    for o in props.get("owners", []) or []:
        owners.append(
            DataProductOwner(
                id=o.get("id", ""),
                display_name=o.get("displayName"),
                email=o.get("email"),
            )
        )
    return DataProduct(
        id=raw.get("id", ""),
        name=props.get("name", raw.get("name", "")),
        description=props.get("description"),
        status=props.get("status"),
        owners=owners,
        domain_id=props.get("domainId"),
        domain_name=props.get("domainName"),
        asset_count=props.get("assetCount", 0) or 0,
        tags=props.get("tags", []) or [],
        data_product_type=props.get("dataProductType"),
    )


def _parse_node(node: dict[str, Any]) -> LineageNode:
    return LineageNode(
        id=node.get("guid", ""),
        name=node.get("displayText", node.get("attributes", {}).get("name", "")),
        asset_type=node.get("typeName", ""),
        qualified_name=node.get("attributes", {}).get("qualifiedName", ""),
    )

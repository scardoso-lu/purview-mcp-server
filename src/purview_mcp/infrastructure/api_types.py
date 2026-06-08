from typing import TypedDict


class EntityContactRaw(TypedDict, total=False):
    id: str
    info: str


class EntityContactsRaw(TypedDict, total=False):
    Expert: list[EntityContactRaw]
    Owner: list[EntityContactRaw]


class EntityMeaningRaw(TypedDict, total=False):
    displayText: str


class EntityClassificationRaw(TypedDict, total=False):
    typeName: str


class EntityAttributesRaw(TypedDict, total=False):
    name: str
    qualifiedName: str
    userDescription: str
    description: str
    endorsement: str
    domain: str
    meanings: list[EntityMeaningRaw]
    dataQualityScore: dict[str, float]


class EntityDetailRaw(TypedDict, total=False):
    guid: str
    typeName: str
    entityType: str
    name: str
    attributes: EntityAttributesRaw
    contacts: EntityContactsRaw
    classifications: list[EntityClassificationRaw]
    labels: list[str]
    collectionId: str


class SearchContactRaw(TypedDict, total=False):
    id: str
    info: str
    contactType: str


class SearchHitRaw(TypedDict, total=False):
    id: str
    name: str
    entityType: str
    userDescription: str
    description: str
    endorsement: str
    domain: str
    qualifiedName: str
    contact: list[SearchContactRaw]
    classification: list[str]
    label: list[str]
    collectionId: str


class GlossaryPersonRaw(TypedDict, total=False):
    id: str


class GlossarySynonymRaw(TypedDict, total=False):
    displayText: str


class GlossaryTermAttributesRaw(TypedDict, total=False):
    name: str
    qualifiedName: str
    shortDescription: str
    longDescription: str
    definition: str
    status: str
    examples: list[str]
    synonyms: list[GlossarySynonymRaw]
    stewards: list[GlossaryPersonRaw]
    experts: list[GlossaryPersonRaw]


class GlossaryTermRaw(TypedDict, total=False):
    guid: str
    termGuid: str
    displayText: str
    attributes: GlossaryTermAttributesRaw
    # Flat-layout fields present when the "attributes" wrapper is absent (direct-lookup endpoint)
    name: str
    qualifiedName: str
    shortDescription: str
    longDescription: str
    definition: str
    status: str
    examples: list[str]
    synonyms: list[GlossarySynonymRaw]
    stewards: list[GlossaryPersonRaw]
    experts: list[GlossaryPersonRaw]


class DataProductOwnerRaw(TypedDict, total=False):
    id: str
    displayName: str
    email: str


class DataProductPropertiesRaw(TypedDict, total=False):
    name: str
    description: str
    status: str
    owners: list[DataProductOwnerRaw]
    domainId: str
    domainName: str
    assetCount: int
    tags: list[str]
    dataProductType: str


class DataProductRaw(TypedDict, total=False):
    id: str
    name: str
    properties: DataProductPropertiesRaw


class LineageNodeAttributesRaw(TypedDict, total=False):
    name: str
    qualifiedName: str


class LineageNodeRaw(TypedDict, total=False):
    guid: str
    displayText: str
    typeName: str
    attributes: LineageNodeAttributesRaw


class LineageRelationRaw(TypedDict, total=False):
    fromEntityId: str
    toEntityId: str
    relationshipType: str


class LineageResponseRaw(TypedDict, total=False):
    guidEntityMap: dict[str, LineageNodeRaw]
    relations: list[LineageRelationRaw]

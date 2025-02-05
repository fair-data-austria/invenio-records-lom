# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2025 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Schemas for OAI."""

from copy import copy

from marshmallow import EXCLUDE, Schema, fields, pre_dump, validate, validates_schema

from ....services.schemas.metadata import validate_cc_license_lang
from ....utils import make_lom_vcard
from ....utils.util import vocabularify

LANGSTRING_LOM_V1 = {
    "langstring": {
        "#text": "LOMv1.0",
        "lang": "x-none",
    },
}

LANGSTRING_KIM_HCRT_SCHEME = {
    "langstring": {
        "#text": "https://w3id.org/kim/hcrt/scheme",
        "lang": "x-none",
    },
}

LANGSTRING_OEFOS = {
    "langstring": {
        "#text": "https://w3id.org/oerbase/vocabs/oefos2012",
        "lang": "x-none",
    },
}


class ExcludeUnknownOrderedSchema(Schema):
    """Schema configured to be ordered and exclude unknown."""

    class Meta:
        """Configuration."""

        ordered = True
        unknown = EXCLUDE


#
# schemas for langstrings (who are annoyingly subtly different)
#
class LangstringXNoneInnerSchema(ExcludeUnknownOrderedSchema):
    """Inner langstring-schema where `language` is set to "x-none"."""

    lang = fields.Constant("x-none")
    text = fields.Str(attribute="#text", data_key="#text", required=True)


class LangstringXNoneSchema(ExcludeUnknownOrderedSchema):
    """Langstring-schema where `langstring.language` is set to "x-none"."""

    langstring = fields.Nested(LangstringXNoneInnerSchema(), required=True)


class LangstringWithLangInnerSchema(ExcludeUnknownOrderedSchema):
    """Inner langstring-schema where `language` is given."""

    # same `lang`-validation as LOM-UIBK
    lang = fields.Str(required=True, validate=validate.Regexp("[a-z][a-z]"))
    text = fields.Str(attribute="#text", data_key="#text", required=True)


class LangstringWithLangSchema(ExcludeUnknownOrderedSchema):
    """Langstring-schema where `langstring.language` is given."""

    langstring = fields.Nested(LangstringWithLangInnerSchema(), required=True)


class LangstringRoleInnerSchema(ExcludeUnknownOrderedSchema):
    """Inner langstring-schema where `#text` is validated to be a LOM role."""

    lang = fields.Str(required=True)
    text = fields.Str(
        attribute="#text",
        data_key="#text",
        required=True,
        validate=validate.OneOf(
            [
                "Author",
                "Publisher",
                "Unknown",
                "Initiator",
                "Terminator",
                "Validator",
                "Editor",
                "Graphical Designer",
                "Technical Implementer",
                "Content Provider",
                "Technical Validator",
                "Educational Validator",
                "Script Writer",
                "Instructional Designer",
            ],
        ),
    )


class LangstringRoleSchema(ExcludeUnknownOrderedSchema):
    """Langstring-schema where `langstring.#text` is validated to be a LOM role."""

    langstring = fields.Nested(LangstringRoleInnerSchema(), required=True)


class LangstringLicenseInnerSchema(ExcludeUnknownOrderedSchema):
    """Inner langstring-schema where `lang` is set to "x-t-cc-url"."""

    lang = fields.Constant("x-t-cc-url")
    text = fields.Str(attribute="#text", data_key="#text", required=True)

    @validates_schema
    def validate_cc_license_text_fits_lang(self, obj: dict, **__: dict) -> None:
        """Validate that license-url fits with `lang`."""
        validate_cc_license_lang(obj)


class LangstringLicenseSchema(ExcludeUnknownOrderedSchema):
    """Langstring-schema where `langstring.lang` is set to "x-t-cc-url"."""

    langstring = fields.Nested(LangstringLicenseInnerSchema(), required=True)


#
# schemas for `general` category
#
class IdentifierSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `general.identifier`."""

    catalog = fields.Str()
    entry = fields.Nested(LangstringXNoneSchema())


class AggregationLevelSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `general.aggregationlevel`."""

    source = fields.Raw(
        required=True,
        validate=validate.Equal(LANGSTRING_LOM_V1),
        dump_default=LANGSTRING_LOM_V1,
    )
    value = fields.Nested(LangstringXNoneSchema(), required=True)

    @classmethod
    def dump_default(cls) -> dict:
        """Dump default."""
        aggregation_level = {"value": {"langstring": {"lang": "x-none", "#text": "4"}}}
        aggregation_level |= {"source": LANGSTRING_LOM_V1}
        return aggregation_level


class GeneralSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `general` category."""

    identifier = fields.List(
        fields.Nested(IdentifierSchema()),
        required=True,
        validate=validate.Length(min=1),
    )
    title = fields.Nested(LangstringWithLangSchema(), required=True)
    language = fields.List(fields.Str(), required=True, dump_default=["N/A"])
    description = fields.List(fields.Nested(LangstringWithLangSchema()))
    keyword = fields.List(fields.Nested(LangstringWithLangSchema()))
    aggregationlevel = fields.Nested(
        AggregationLevelSchema(),
        required=True,
        dump_default=AggregationLevelSchema.dump_default,
    )


#
# schemas for `lifecycle` category
#
class RoleSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `lifecycle.contribute.role`."""

    # pylint: disable=duplicate-code
    source = fields.Raw(
        required=True,
        validate=validate.Equal(LANGSTRING_LOM_V1),
        dump_default=LANGSTRING_LOM_V1,
    )
    value = fields.Nested(LangstringRoleSchema(), required=True)


class DateSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `lifecycle.contribute.date` category."""

    datetime = fields.Str()
    description = fields.Nested(LangstringWithLangSchema(), required=True)


class ContributeSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `lifecycle.contribute`."""

    role = fields.Nested(RoleSchema(), required=True)
    date = fields.Nested(DateSchema())
    centity = fields.Method(
        "get_centity",  # dump
        None,  # load
    )

    def get_centity(self, contributors: dict) -> list:
        """Get vcard."""
        role = contributors["role"]["value"]["langstring"]["#text"]
        entity = contributors["entity"]
        entities = entity if isinstance(entity, list) else [entity]

        return [{"vcard": make_lom_vcard(fn=e, role=role)} for e in entities]


class LifecycleSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `lifecycle` category."""

    datetime = fields.String()
    version = fields.Raw()
    status = fields.Raw()
    contribute = fields.List(fields.Nested(ContributeSchema()))

    @pre_dump
    def group_contributes_by_role(self, data: dict, **__: dict) -> dict:
        """Group contributes by role."""
        contributions_by_role = {}
        for contribute in data.get("contribute", []):
            role = (  # pylint: disable=duplicate-code
                contribute.get("role", {})
                .get("value", {})
                .get("langstring", {})
                .get("#text")
            )
            if not role:
                continue

            if role not in contributions_by_role:
                contributions_by_role[role] = {"role": vocabularify(role), "entity": []}
            entities_of_role = contributions_by_role[role]["entity"]

            entities_from_contribute = contribute.get("entity", [])
            if not isinstance(entities_from_contribute, list):
                entities_from_contribute = [entities_from_contribute]

            for entity in entities_from_contribute:
                if entity not in entities_of_role:
                    entities_of_role.append(entity)

        result_data = copy(data)
        result_data["contribute"] = list(contributions_by_role.values())

        return result_data


#
# schemas for `technical` category
#
class LocationSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `technical.location`."""

    text = fields.Str(
        attribute="#text",
        data_key="#text",
        dump_default="N/A",
    )

    @classmethod
    def dump_default(cls) -> dict:
        """Dump default."""
        return {"#text": "N/A"}


class TechnicalSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `technical` category."""

    format = fields.List(
        fields.Str(
            required=True,
            validate=validate.Length(min=1, error="Format must not be empty."),
        ),
        required=True,
        validate=validate.Length(min=1, max=1, error="Must have exactly one format."),
        dump_default=["application/pdf"],
    )  # e.g. ['video/mp4']
    # TODO: optional field: size
    location = fields.Nested(
        LocationSchema(),
        dump_default=LocationSchema.dump_default,
    )
    # TODO: optional field: thumbnail
    # TODO: optional field: duration


#
# schemas for `educational` category
#
class LearningResourceTypeSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `educational.learningresourcetype`."""

    # pylint: disable=duplicate-code
    source = fields.Raw(
        required=True,
        validate=validate.Equal(LANGSTRING_KIM_HCRT_SCHEME),
        dump_default=LANGSTRING_KIM_HCRT_SCHEME,
    )
    id = fields.Str(required=True, dump_default="https://w3id.org/kim/hcrt/other")

    @classmethod
    def dump_default(cls) -> dict:
        """Dump default."""
        obj = {"id": "https://w3id.org/kim/hcrt/other"}
        obj |= {"source": LANGSTRING_KIM_HCRT_SCHEME}
        return obj


class EducationalSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `educational` category."""

    learningresourcetype = fields.List(
        fields.Nested(
            LearningResourceTypeSchema(),
            required=True,
            dump_default=LearningResourceTypeSchema.dump_default,
        ),
    )


#
# schemas for `rigths` category
#
class RightsSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `rights` category."""

    # TODO: get `copyrightandotherrestrictions`` from passed in obj instead
    copyrightandotherrestrictions = fields.Constant(
        {
            "source": {"langstring": {"#text": "LOMv1.0", "lang": "x-none"}},
            "value": {"langstring": {"#text": "yes", "lang": "x-none"}},
        },
    )
    description = fields.Nested(LangstringLicenseSchema(), required=True)


#
# schemas for `classification` category
#
class PurposeSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `classification.purpose`."""

    # pylint: disable=duplicate-code
    source = fields.Raw(
        required=True,
        validate=validate.Equal(LANGSTRING_LOM_V1),
        dump_default=LANGSTRING_LOM_V1,
    )
    value = fields.Nested(LangstringXNoneSchema(), required=True)


class TaxonSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `classification.taxonpath.taxon`."""

    id = fields.Str(required=True)
    # TODO: optional field: entry


class TaxonpathSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `classification.taxonpath`."""

    # pylint: disable=duplicate-code
    source = fields.Raw(
        required=True,
        validate=validate.Equal(LANGSTRING_OEFOS),
        dump_default=LANGSTRING_OEFOS,
    )
    taxon = fields.Raw()


class ClassificationSchema(ExcludeUnknownOrderedSchema):
    """Schema for LOM-UIBK's `classification` category."""

    purpose = fields.Nested(PurposeSchema(), required=True)
    taxonpath = fields.List(fields.Nested(TaxonpathSchema()), required=True)


#
# main schema
#
class LOMToOAISchema(ExcludeUnknownOrderedSchema):
    """Schema to reorder fields and exclude unneeded fields."""

    general = fields.Nested(GeneralSchema(), required=True)
    lifecycle = fields.Nested(LifecycleSchema(), required=True)
    # TODO: optional field: metametadata
    technical = fields.Nested(TechnicalSchema(), required=True)
    educational = fields.Nested(EducationalSchema(), required=True)
    rights = fields.Nested(RightsSchema(), required=True)
    # TODO: multiplex different ClassificationSchemas based on their purpose
    classification = fields.List(fields.Nested(ClassificationSchema(), required=True))

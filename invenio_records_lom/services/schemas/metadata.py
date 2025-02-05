# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2025 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Marshmallow schema for validating and serializing LOM JSONs."""

from collections.abc import Callable
from copy import copy
from datetime import datetime, timezone
from types import MappingProxyType

from invenio_i18n import lazy_gettext as _
from marshmallow import (
    INCLUDE,
    Schema,
    ValidationError,
    fields,
    missing,
    validate,
    validates,
)
from marshmallow_utils.fields import SanitizedUnicode
from marshmallow_utils.html import sanitize_unicode


def now_isoformat() -> str:
    """Return current date and time in ISO-8601 format.

    example-return: '2020-06-24T05:34:56.789123'
    """
    now_unaware = datetime.now(timezone.utc).replace(tzinfo=None)
    return now_unaware.isoformat()


class NoValidationSchema(Schema):
    """Let data through unchanged, without validation."""

    class Meta:
        """Configure this schema to include unknown fields no questions asked."""

        unknown = INCLUDE

    def dump(self, obj: dict, **__: dict) -> dict:
        """Overwrite dump to return `obj`, bypassing validation as class name indicates."""
        return copy(obj)


class LangstringField(fields.Field):
    """Verifies against form {"langstring": {"#text": str, "lang": str}}."""

    default_error_messages = MappingProxyType(
        {
            # the following shouldn't really be shown to users, hence no translation:
            "extraneous_keys": "Extraneous keys in this langstring: {keys!r}.",
            "extraneous_lang": "This langstring must not have a 'lang'-field.",
            "invalid_inner_type": "Inner langstring must be a `dict`.",
            "invalid_outer_type": "Outer langstring must be a `dict`.",
            "lang_required": "`lang` is falsy when its existence was required.",
            "missing_langstring_key": "No {keys!r}-key in this langstring.",
            # the following overwrites default from parent-class with a translated version:
            "required": _("Missing data for required field."),
        },
    )

    def __init__(
        self,
        *,
        lang_exists: bool = True,
        validate_lang_existence: bool = True,
        **kwargs: dict,
    ) -> None:
        """Init.

        :param bool| lang_exists:
          truthy value validates presence of 'lang',
          falsy value validates absence thereof
        :param bool validate_lang_existence:
          falsy value turns off validation of lang-existence
        """
        super().__init__(**kwargs)
        self.lang_exists = lang_exists
        self.validate_lang_existence = validate_lang_existence

    # function-signature mirrors that of all marshmallow `Field`s
    def _deserialize(  # noqa: C901
        self,
        value,  # noqa: ANN001
        attr,  # noqa: ANN001, ARG002
        data,  # noqa: ANN001, ARG002
        **kwargs,  # noqa: ANN003, ARG002
    ) -> dict:
        if not isinstance(value, dict):
            msg = "invalid_outer_type"
            raise self.make_error(msg)

        # validate outer keys
        outer_keys = set(value)
        if "langstring" not in outer_keys:
            msg = "missing_langstring_key"
            raise self.make_error(msg, keys="langstring")
        if not outer_keys <= {"langstring"}:
            msg = "extraneous_keys"
            raise self.make_error(msg, keys=sorted(outer_keys - {"langstring"}))

        langstring_inner = value["langstring"]

        # validate inner keys
        if not isinstance(langstring_inner, dict):
            msg = "invalid_inner_type"
            raise self.make_error(msg)
        inner_keys = set(langstring_inner)
        if "#text" not in inner_keys:
            msg = "missing_langstring_key"
            raise self.make_error(msg, keys="#text")
        if self.validate_lang_existence:
            if "lang" not in inner_keys and self.lang_exists:
                msg = "missing_langstring_key"
                raise self.make_error(msg, keys="lang")
            if "lang" in inner_keys and not self.lang_exists:
                msg = "extraneous_lang"
                raise self.make_error(msg)
        if not inner_keys <= {"#text", "lang"}:
            msg = "extraneous_keys"
            raise self.make_error(msg, keys=sorted(inner_keys - {"#text", "lang"}))

        text = sanitize_unicode(str(langstring_inner["#text"]))
        lang_exists = "lang" in langstring_inner
        lang = sanitize_unicode(str(langstring_inner["lang"])) if lang_exists else None

        # validate non-emptiness of "#text"-, "lang"-key
        if not text:
            msg = "required"
            raise self.make_error(msg)
        if self.validate_lang_existence and self.lang_exists and not lang:
            msg = "lang_required"
            raise self.make_error(msg)

        # validation succeded, rebuild langstring with sanitized text/lang
        result = {"langstring": {"#text": text}}
        if lang_exists:
            result["langstring"]["lang"] = lang

        return result


def validate_langstring_lang(validator: Callable) -> Callable:
    """Wrap `validator`, passing it value["langstring"]["lang"]."""

    def validate_lang[T](value: dict) -> T:
        try:
            lang = value["langstring"]["lang"]
        except (KeyError, TypeError) as error:
            msg = "not a valid langstring"
            raise ValidationError(msg) from error
        return validator(lang)

    return validate_lang


def validate_langstring_text(validator: Callable) -> Callable:
    """Wrap `validator_callable`, passing it value["langstring"]["#text"]."""

    def validate_text[T](value: dict) -> T:
        try:
            text = value["langstring"]["#text"]
        except (KeyError, TypeError) as error:
            msg = "not a valid langstring"
            raise ValidationError(msg) from error
        return validator(text)

    return validate_text


def validate_cc_license_lang(value: dict) -> None:
    """Validate that a license fits with its langstring's 'lang' (different for CC)."""
    try:
        lang = value["langstring"].get("lang", missing)
        text = value["langstring"]["#text"]
    except (KeyError, TypeError) as error:
        msg = "not a valid langstring"
        raise ValidationError(msg) from error

    if text.startswith("https://creativecommons.org/"):
        if lang != "x-t-cc-url":
            msg = "for CC licenses, lang must equal 'x-t-cc-url'"
            raise ValidationError(msg)
    elif lang != missing:
        msg = "for non-CC licenses, lang may not be present"
        raise ValidationError(msg)


class GeneralSchema(Schema):
    """Schema for LOM's `general` category."""

    class Meta:
        """Configure this schema to include unknown fields no questions asked."""

        unknown = INCLUDE

    title = LangstringField(required=True)
    description = fields.List(LangstringField)
    keyword = fields.List(LangstringField)


class RoleSchema(Schema):
    """Schema for LOM's role-fields."""

    source = fields.Raw(
        required=True,
        validate=validate.Equal({"langstring": {"#text": "LOMv1.0", "lang": "x-none"}}),
    )
    value = LangstringField(
        required=True,
        validate=validate.And(
            validate_langstring_text(
                validate.OneOf(
                    # allowed values as to LOM-UIBK
                    [
                        "Author",
                        "Content Provider",
                        "Editor",
                        "Educational Validator",
                        "Graphical Designer",
                        "Initiator",
                        "Instructional Designer",
                        "Publisher",
                        "Script Writer",
                        "Technical Implementer",
                        "Technical Validator",
                        "Terminator",
                        "Unknown",
                        "Validator",
                    ],
                ),
            ),
            validate_langstring_lang(validate.Equal("x-none")),
        ),
    )


class ContributeSchema(Schema):
    """Schema for LOM's contribute-fields."""

    role = fields.Nested(RoleSchema, required=True)
    entity = fields.List(
        SanitizedUnicode(
            validate=validate.Length(min=1, error=_("Name cannot be empty.")),
        ),
        required=True,
        validate=validate.Length(
            min=1,
            error="Contribute requires at least one associated entity.",
        ),
    )


class LifecycleSchema(Schema):
    """Schema for LOM's `lifecycle` category."""

    datetime = fields.String(load_default=now_isoformat)
    contribute = fields.List(
        fields.Nested(ContributeSchema()),
        required=True,
    )

    @validates("contribute")
    def validate_author_publisher_exist(self, contributes: list) -> None:
        """Validate existence of >=1 author/publisher contributes."""

        def get_role_text_lower(contribute: dict) -> str:
            try:
                return contribute["role"]["value"]["langstring"]["#text"].lower()
            except KeyError:
                return ""

        author_contributes = [
            contribute
            for contribute in contributes
            if get_role_text_lower(contribute) == "author"
        ]
        publisher_contributes = [
            contribute
            for contribute in contributes
            if get_role_text_lower(contribute) == "publisher"
        ]

        msg = None

        if len(author_contributes) < 1 and len(publisher_contributes) < 1:
            msg = _("Must provide at least one author and one publisher.")

        elif len(author_contributes) < 1:
            msg = _("Must provide at least one author.")

        elif len(publisher_contributes) < 1:
            msg = _("Must provide at least one publisher.")

        if msg:
            raise ValidationError(msg)


class LocationSchema(Schema):
    """Schema for LOM's `technical.location`."""

    text = SanitizedUnicode(attribute="#text", data_key="#text")


class TechnicalSchema(Schema):
    """Schema for LOM's `technical` category."""

    format = fields.List(
        SanitizedUnicode(
            required=True,
            validate=validate.Length(
                min=1,
                error=_("Missing data for required field."),
            ),
        ),
        required=True,
        validate=validate.Length(
            min=1,
            max=1,
            error="Format requires exactly one entry.",
        ),
    )
    location = fields.Nested(LocationSchema)


class LearningResourceTypeSchema(Schema):
    """Scheam for LOM's `educational.learningresourcetype`."""

    source = fields.Raw(
        required=True,
        validate=validate.Equal(
            {
                "langstring": {
                    "#text": "https://w3id.org/kim/hcrt/scheme",
                    "lang": "x-none",
                },
            },
        ),
    )
    id = SanitizedUnicode(
        required=True,
        validate=validate.Length(min=1, error=_("Missing data for required field.")),
    )


class EducationalSchema(Schema):
    """Schema for LOM's `educational` category."""

    learningresourcetype = fields.List(
        fields.Nested(LearningResourceTypeSchema, required=True),
        required=True,
        validate=validate.Length(min=1),
    )


class CopyrightAndOtherSchema(Schema):
    """Schema for LOM's "rigths.copyrightandotherrestrictions"."""

    source = fields.Raw(
        required=True,
        validate=validate.Equal({"langstring": {"#text": "LOMv1.0", "lang": "x-none"}}),
    )
    value = LangstringField(
        required=True,
        validate=validate.And(
            validate_langstring_text(validate.OneOf(["yes", "no"])),
            validate_langstring_lang(validate.Equal("x-none")),
        ),
    )


class RightsSchema(Schema):
    """Schema for LOM's `rights`-category."""

    copyrightandotherrestrictions = fields.Nested(
        CopyrightAndOtherSchema,
        required=True,
    )
    description = LangstringField(
        validate_lang_existence=False,
        required=True,
        validate=validate_cc_license_lang,
    )
    url = SanitizedUnicode(
        required=True,
        validate=validate.Length(min=1, error=_("Missing data for required field.")),
    )


class TaxonSchema(Schema):
    """Schema for LOM's `classification.taxonpath.taxon`-category."""

    id = SanitizedUnicode(
        required=True,
        validate=validate.Regexp(
            r"https://w3id.org/oerbase/vocabs/oefos2012/\d+",
            error=_("Not a valid OEFOS-url."),
        ),
    )
    entry = LangstringField(lang_exists=False)


class TaxonpathSchema(Schema):
    """Schema for LOM's `classification.taxonpath`-category."""

    source = fields.Raw(
        required=True,
        validate=validate.Equal(
            {
                "langstring": {
                    "#text": "https://w3id.org/oerbase/vocabs/oefos2012",
                    "lang": "x-none",
                },
            },
        ),
    )
    taxon = fields.Nested(
        TaxonSchema,
        many=True,
        required=True,
        validate=validate.Length(min=1, error="Taxon requires at least one entry."),
    )


class ClassificationSchema(Schema):
    """Schema for LOM's `classification`-category."""

    purpose = fields.Raw(
        required=True,
        validate=validate.Equal(
            {
                "source": {"langstring": {"#text": "LOMv1.0", "lang": "x-none"}},
                "value": {"langstring": {"#text": "discipline", "lang": "x-none"}},
            },
        ),
    )
    taxonpath = fields.Nested(
        TaxonpathSchema,
        many=True,
        required=True,
        validate=validate.Length(min=1, error=_("Must add at least one OEFOS.")),
    )


class MetadataSchema(Schema):
    """Schema for LOM-Metadata uploaded by deposit-page."""

    class Meta:
        """Configure this schema to include unknown fields no questions asked."""

        unknown = INCLUDE

    # passed by parent as to multiplex, removed by parent after load/dump
    type = fields.Raw(validate=validate.Equal("upload"))

    general = fields.Nested(GeneralSchema, required=True)
    lifecycle = fields.Nested(LifecycleSchema, required=True)
    technical = fields.Nested(TechnicalSchema, required=True)
    educational = fields.Nested(EducationalSchema, required=True)
    rights = fields.Nested(RightsSchema, required=True)
    classification = fields.Nested(
        ClassificationSchema,
        many=True,
        required=True,
        validate=validate.Length(
            min=1,
            error="Classification requires at least one entry.",
        ),
    )

    def load(self, data: dict, **kwargs: dict) -> dict:
        """Overwrite parent as to use NoValidationSchema for resource-type!="upload"."""
        if data["type"] != "upload":
            return NoValidationSchema().load(data, **kwargs)
        return super().load(data, **kwargs)

    def dump(self, obj: dict, **__: dict) -> dict:
        """Overwrite parent as to dump everything always."""
        return obj

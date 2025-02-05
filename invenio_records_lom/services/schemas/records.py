# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2025 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Marshmallow schema for validating and serializing LOM JSONs."""


from flask import current_app
from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.services.schemas import RDMRecordSchema
from invenio_rdm_records.services.schemas.pids import PIDSchema
from marshmallow import (
    ValidationError,
    fields,
    post_dump,
    post_load,
    pre_dump,
    pre_load,
)
from marshmallow_utils.fields import NestedAttribute, SanitizedUnicode
from werkzeug.local import LocalProxy

from .fields import ControlledVocabularyField
from .metadata import MetadataSchema
from .stats import LomStatisticSchema


def _validate_lom_scheme(scheme: str) -> None:
    """Validate whether scheme is supported."""
    if scheme not in current_app.config["LOM_PERSISTENT_IDENTIFIERS"]:
        raise ValidationError(_("Persistent identifier scheme unknown to LOM."))


class LOMRecordSchema(RDMRecordSchema):
    """Marshmallow schema for validating LOM records."""

    # NOTE: To ensure compatibility with invenio systemfields,
    # use ``NestedAttribute`` instead of ``fields.Nested()``.

    # overwrite metadata-field: allow any dict
    metadata = NestedAttribute(MetadataSchema)

    pids = fields.Dict(
        keys=SanitizedUnicode(validate=_validate_lom_scheme),
        values=fields.Nested(PIDSchema),
    )

    resource_type = ControlledVocabularyField(
        vocabulary=LocalProxy(lambda: current_app.config["LOM_RESOURCE_TYPES"]),
    )

    stats = NestedAttribute(LomStatisticSchema, dump_only=True)

    @pre_dump
    @pre_load
    def add_resource_type_to_metadata(self, obj: dict, **__: dict) -> dict:
        """Add `resource_type` to `obj["metadata"]`.

        `RDMRecordSchema` does not play nice with `OneOfSchema`, hence `MetadataSchema`
        does custom multiplexing. For this, `obj["metadata"]` needs the
        `resource_type` stored within itself.
        """
        if "metadata" not in obj:
            obj["metadata"] = {}
        obj["metadata"]["type"] = obj.get("resource_type")
        return obj

    @post_dump
    @post_load
    def remove_resource_type_from_metadata(self, obj: dict, **__: dict) -> dict:
        """Remove `resource_type` from `obj["metadata"]`.

        Cleanup to the above adding of `resource_type` to `obj["metadata"]`.
        """
        if obj.get("metadata", {}).get("type"):
            del obj["metadata"]["type"]
        return obj

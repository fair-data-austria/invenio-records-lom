# -*- coding: utf-8 -*-
#
# Copyright (C) 2023-2024 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""LOM facets (`facet` is opensearch-lingo for `search-query filter`)."""

from invenio_i18n import gettext as _
from invenio_records_resources.services.records.facets import TermsFacet

from ..utils.vocabularies import read_vocabulary


def license_labels(keys: list) -> dict:
    """Label licenses.

    ATTENTION: # noqa
    this should be a temporary solution. the real solution should be to fix the
    metadata within the database.

    """
    license_mapping = {
        entry.id: entry.props.get("short_name", "N/A")
        for entry in read_vocabulary("oerlicenses")
    }
    out = {}
    for key in keys:
        search_key = key
        if search_key[-1] != "/":
            search_key += "/"
        if search_key[0:5] == "http:":
            search_key = f"https{search_key[4:]}"

        out[key] = license_mapping.get(search_key)

    return out


rights_license = TermsFacet(
    field="metadata.rights.url.keyword",
    label=_("License"),
    value_labels=license_labels,
)

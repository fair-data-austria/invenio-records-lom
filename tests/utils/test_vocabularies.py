# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Tests for `invenio_records_lom.utils.vocabularies`."""

from importlib import resources

import yaml
from flask_sqlalchemy import SQLAlchemy
from invenio_vocabularies.records.models import VocabularyMetadata, VocabularyType

from invenio_records_lom.utils.vocabularies import import_vocabulary


def test_importing_vocabulary(
    db: SQLAlchemy,  # noqa: ARG001
) -> None:
    """Test importing a vocabulary."""
    traversable = resources.files("invenio_records_lom.fixtures.data.vocabularies")

    with traversable.joinpath("oer_licenses.yaml").open() as read_buffer:
        entries = yaml.safe_load(read_buffer.read())

    import_vocabulary(entries, vocabulary_id="oerlicenses", pid_type="oerlic")

    vocabulary_ids = [vt.id for vt in VocabularyType.query]
    assert "oerlicenses" in vocabulary_ids

    oerlicense_jsons = [
        row.json
        for row in VocabularyMetadata.query
        if row.json["type"]["id"] == "oerlicenses"
    ]
    assert all(json["type"]["pid_type"] == "oerlic" for json in oerlicense_jsons)

    # all jsons for CC-BY license (should only be one such license)
    ccby_jsons = [
        json
        for json in oerlicense_jsons
        if json["id"] == "https://creativecommons.org/licenses/by/4.0/"
    ]
    assert len(ccby_jsons) == 1
    cc_by_json = ccby_jsons[0]
    assert cc_by_json["props"]["short_name"]
    assert cc_by_json["title"]["en"]

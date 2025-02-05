# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""statistic utils module."""


def build_record_unique_id(doc: dict) -> dict:
    """Build record unique identifier."""
    doc["unique_id"] = f"{doc['recid']}_{doc['parent_recid']}"
    return doc

# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2025 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Utilities for creation of LOM-compliant metadata."""

from .metadata import LOMCourseMetadata, LOMMetadata, LOMRecordData
from .stats import build_record_unique_id
from .util import (
    DotAccessWrapper,
    LOMDuplicateRecordError,
    check_about_duplicate,
    create_record,
    get_learningresourcetypedict,
    get_oefosdict,
    update_record,
)
from .vcard import make_lom_vcard

__all__ = (
    "DotAccessWrapper",
    "LOMCourseMetadata",
    "LOMDuplicateRecordError",
    "LOMMetadata",
    "LOMRecordData",
    "build_record_unique_id",
    "check_about_duplicate",
    "create_record",
    "get_learningresourcetypedict",
    "get_oefosdict",
    "make_lom_vcard",
    "update_record",
)

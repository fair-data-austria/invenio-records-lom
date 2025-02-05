# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2025 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""LOM System Fields.

System Fields execute actions on creating, editing, publishing, ... the
API-object they are attributes of.
"""

from invenio_rdm_records.records.systemfields import (
    ParentRecordAccessField,
    RecordAccessField,
)

from .context import LOMPIDFieldContext
from .providers import LOMDraftRecordIdProvider, LOMRecordIdProvider
from .relations import PIDLOMRelation
from .resolver import LOMResolver
from .stats import LomRecordStatisticsField

__all__ = (
    "LOMDraftRecordIdProvider",
    "LOMPIDFieldContext",
    "LOMRecordIdProvider",
    "LOMResolver",
    "LomRecordStatisticsField",
    "PIDLOMRelation",
    "ParentRecordAccessField",
    "RecordAccessField",
)

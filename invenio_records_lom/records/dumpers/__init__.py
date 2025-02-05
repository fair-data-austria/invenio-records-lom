# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2018 CERN.
# Copyright (C) 2024-2025 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Statistics integration for RDM records."""

from .stats import LomStatisticsDumperExt

__all__ = ("LomStatisticsDumperExt",)

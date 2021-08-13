# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Circulation fetchers."""

from invenio_pidstore.fetchers import FetchedPID


def lom_pid_fetcher(record_uuid, data):
    """Fetch lomrecord's identifier(PID)."""
    return FetchedPID(
        provider=None,
        pid_type="lomid",
        pid_value=data["id"].lower(),
    )

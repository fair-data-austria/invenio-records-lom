# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Fetcher tests."""

import uuid

from invenio_records_lom.fetchers import lom_pid_fetcher
from invenio_records_lom.minters import lom_pid_minter


def test_lom_pid_fetcher(app):
    """Test legacy lomid fetcher."""
    with app.app_context():
        rec_uuid = uuid.uuid4()
        data = {}
        minted_pid = lom_pid_minter(rec_uuid, data)
        fetched_pid = lom_pid_fetcher(rec_uuid, data)
        assert minted_pid.pid_value == fetched_pid.pid_value
        assert fetched_pid.pid_type == "lomid"

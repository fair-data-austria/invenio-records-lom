# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

import copy
import os
import shutil
import tempfile

import pytest
from flask import Flask
from invenio_access import InvenioAccess
from invenio_accounts import InvenioAccounts
from invenio_config import InvenioConfigDefault
from invenio_db import InvenioDB, db
from invenio_indexer import InvenioIndexer
from invenio_pidstore import InvenioPIDStore
from invenio_records import InvenioRecords
from invenio_records_rest import InvenioRecordsREST, config
from invenio_records_rest.utils import PIDConverter
from invenio_rest import InvenioREST
from invenio_search import InvenioSearch
from sqlalchemy_utils.functions import create_database, database_exists, drop_database


@pytest.fixture()
def app(request):
    """Basic Flask application."""
    instance_path = tempfile.mkdtemp()
    app = Flask("testapp")
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite://"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TESTING=True,
        SECRET_KEY="testing",
        # SERVER_NAME='localhost:5000',
    )

    app.url_map.converters["pid"] = PIDConverter

    InvenioDB(app)
    InvenioPIDStore(app)
    InvenioRecords(app)
    InvenioAccounts(app)
    InvenioAccess(app)
    InvenioIndexer(app)
    InvenioSearch(app)
    InvenioREST(app)
    InvenioRecordsREST(app)
    InvenioConfigDefault(app)

    with app.app_context():
        db_url = str(db.engine.url)
        if db_url != "sqlite://" and not database_exists(db_url):
            create_database(db_url)
        db.create_all()

    def teardown():
        with app.app_context():
            db_url = str(db.engine.url)
            db.session.close()
            if db_url != "sqlite://":
                drop_database(db_url)
            shutil.rmtree(instance_path)

    request.addfinalizer(teardown)
    app.test_request_context().push()

    return app

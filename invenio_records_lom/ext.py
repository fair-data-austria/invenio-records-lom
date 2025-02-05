# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2025 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.


"""Flask extension for invenio-records-lom."""

from flask import Flask
from flask_menu import current_menu
from invenio_i18n import lazy_gettext as _
from invenio_rdm_records.resources import IIIFResource
from invenio_rdm_records.services import IIIFService
from invenio_rdm_records.services.pids import PIDManager, PIDsService
from invenio_records_resources.resources import FileResource
from invenio_records_resources.services import FileService

from . import config
from .resources import (
    LOMDraftFilesResourceConfig,
    LOMIIIFResourceConfig,
    LOMRecordFilesResourceConfig,
    LOMRecordResource,
    LOMRecordResourceConfig,
)
from .services import (
    LOMDraftFilesServiceConfig,
    LOMRecordFilesServiceConfig,
    LOMRecordService,
    LOMRecordServiceConfig,
)


class InvenioRecordsLOM:
    """invenio-records-lom extension."""

    def __init__(self, app: Flask = None) -> None:
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """Flask application initialization."""
        self.init_config(app)
        self.init_services(app)
        self.init_resources(app)
        app.extensions["invenio-records-lom"] = self

    def init_config(self, app: Flask) -> None:
        """Initialize configuration.

        Override configuration variables with the values in this package.
        """
        for k in dir(config):
            if k.startswith("LOM_"):
                app.config.setdefault(k, getattr(config, k))

    def init_services(self, app: Flask) -> None:
        """Initialize services."""
        record_service_config = LOMRecordServiceConfig.build(app)
        files_service_config = LOMRecordFilesServiceConfig.build(app)
        draft_files_config = LOMDraftFilesServiceConfig.build(app)

        self.records_service = LOMRecordService(
            config=record_service_config,
            files_service=FileService(files_service_config),
            draft_files_service=FileService(draft_files_config),
            pids_service=PIDsService(record_service_config, PIDManager),
        )

        self.iiif_service = IIIFService(
            records_service=self.records_service,
            config=None,
        )

    def init_resources(self, app: Flask) -> None:
        """Initialize resouces."""
        self.draft_files_resource = FileResource(
            config=LOMDraftFilesResourceConfig.build(app),
            service=self.records_service.draft_files,
        )

        # pylint: disable-next=attribute-defined-outside-init
        self.iiif_resource = IIIFResource(
            config=LOMIIIFResourceConfig.build(app),
            service=self.iiif_service,
        )

        # pylint: disable-next=attribute-defined-outside-init
        self.record_files_resource = FileResource(
            config=LOMRecordFilesResourceConfig.build(app),
            service=self.records_service.files,
        )

        # pylint: disable-next=attribute-defined-outside-init
        self.records_resource = LOMRecordResource(
            config=LOMRecordResourceConfig.build(app),
            service=self.records_service,
        )


def finalize_app(app: Flask) -> None:
    """Finalize app."""
    init(app)
    register_lom_dashboard_tab()


def api_finalize_app(app: Flask) -> None:
    """Finalize app for api."""
    init(app)


def init(app: Flask) -> None:
    """Init app by registering services."""
    # Register services - cannot be done in extension because
    # Invenio-Records-Resources might not have been initialized.
    ext = app.extensions["invenio-records-lom"]

    sregistry = app.extensions["invenio-records-resources"].registry
    sregistry.register(ext.records_service, service_id="lom-records")
    sregistry.register(ext.records_service.files, service_id="lom-files")
    sregistry.register(ext.records_service.draft_files, service_id="lom-draft-files")
    sregistry.register(ext.iiif_service, service_id="lom-iiif")

    iregistry = app.extensions["invenio-indexer"].registry
    iregistry.register(ext.records_service.indexer, indexer_id="lom-records")
    iregistry.register(
        ext.records_service.draft_indexer,
        indexer_id="lom-records-drafts",
    )


def register_lom_dashboard_tab() -> None:
    """Register entry for lom in the `flask_menu`-submenu "dashboard"."""
    user_dashboard_menu = current_menu.submenu("dashboard")
    user_dashboard_menu.submenu("OER").register(
        "invenio_records_lom.uploads",  # <blueprint-name>.<view-func-name>
        text=_("Educational Resources"),
        order=5,
    )

# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2024 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""View-functions for deposit-related pages."""

from flask import current_app, g, render_template
from flask_login import current_user, login_required
from invenio_i18n.ext import current_i18n
from invenio_records_resources.services.files.results import FileList
from invenio_records_resources.services.records.results import RecordItem
from invenio_users_resources.proxies import current_user_resources

from ...proxies import current_records_lom
from ...utils import DotAccessWrapper, LOMRecordData, expand_vocabulary
from .decorators import (
    pass_draft,
    pass_draft_files,
    pass_is_oer_certified,
    require_lom_permission,
)


def get_deposit_template_context(**extra_form_config_kwargs: dict) -> dict:
    """Get context for deposit-template from db, current_app.config."""
    app_config = current_app.config
    locale = str(current_i18n.locale)
    locale = locale if locale in ["de", "en"] else "en"

    # we'll use %-formatting to format format-strings
    # ruff: noqa: UP031  # actually turns off for whole file, but only relevant in here
    vocabularies = {}
    vocabularies["oefos"] = expand_vocabulary(
        "oefos",
        name="{{id}} - {{title.%s or title.en}}" % locale,
        value="{{title.%s or title.en}}" % locale,
    )

    vocabularies["license"] = expand_vocabulary(
        "oerlicenses",
        name="{{props.short_name}} - {{title.%s or title.en}}" % locale,
    )

    vocabularies["contributor"] = expand_vocabulary(
        "lomroles",
        name="{{title.%s or title.en}}" % locale,
    )

    vocabularies["format"] = expand_vocabulary(
        "mimetype",
        name=(
            "{{id}} - {{title.%s or title.en}}" % locale
            + " ({{props.common_file_extensions_str}})"
        ),
    )

    # TODO: reconsider language-field:
    # - wouldn't multiple languages be possible (e.g. language-courses)?
    #   currently, frontend only allows one entry
    # - are other languages really impossible?
    #   - e.g. ancient language studies
    #   - e.g. language-courses
    #   - e.g. collaborations with organisation that have to translate to their language
    # - can we reuse invenio's language-vocabulary?
    #   or is that too expansive in its included languages?
    # language-field quite possibly needs more work due to the above,
    # so I'll leave this one hard-coded for now
    vocabularies["language"] = {
        "de": {"name": "Deutsch"},
        "en": {"name": "English"},
    }

    vocabularies["resourcetype"] = expand_vocabulary(
        "highereducationresourcetypes",
        name="{{title.%s or title.en}}" % locale,
    )

    return {
        "files": {"default_preview": None, "entries": [], "links": {}},
        "forms_config": {
            "autocomplete_names": "search",
            "current_locale": str(current_i18n.locale),
            "decimal_size_display": app_config.get(
                "APP_RDM_DISPLAY_DECIMAL_FILE_SIZES",
                True,
            ),
            "default_locale": app_config.get("BABEL_DEFAULT_LOCALE", "en"),
            "links": {},
            "pids": [],
            "quota": app_config.get("APP_RDM_DEPOSIT_FORM_QUOTA"),
            "vocabularies": vocabularies,
            **extra_form_config_kwargs,
        },
        # can't get the following from `app_config`, as that ignores blueprint-prefix...
        "searchbar_config": {"searchUrl": "/oer/search"},
    }


@login_required
@require_lom_permission("create", default_endpoint="invenio_records_lom.uploads")
def deposit_create() -> str:
    """Create a new deposit."""
    service_config = current_records_lom.records_service.config

    pids = {}
    if "doi" in service_config.pids_providers:
        pids = {"doi": {"provider": "external", "identifier": ""}}
    empty_record: LOMRecordData = LOMRecordData.create(
        resource_type="upload",
        pids=pids,
    )
    empty_record["status"] = "draft"

    # insert default-publisher from config (if exists)
    app_config = current_app.config
    if default_publisher := app_config.get("LOM_PUBLISHER"):
        empty_record.metadata.append_contribute(default_publisher, role="publisher")

    # update json with defaults
    defaults = current_app.config.get("LOM_DEPOSIT_FORM_DEFAULTS", {})
    record_json = empty_record.json
    record_dot_access = DotAccessWrapper(record_json)
    for dotted_key, value in defaults.items():
        record_dot_access.setdefault(dotted_key, value)

    template_context: dict = get_deposit_template_context(createUrl="/api/oer")
    return render_template(
        "invenio_records_lom/records/deposit.html",
        files=template_context["files"],
        forms_config=template_context["forms_config"],
        # preselectedCommunity=?,
        record=record_json,
        searchbar_config=template_context["searchbar_config"],
    )


@login_required
@require_lom_permission("handle_oer", default_endpoint="invenio_records_lom.uploads")
@pass_draft(expand=True)
@pass_draft_files
def deposit_edit(
    pid_value: str,
    draft: RecordItem = None,
    draft_files: FileList = None,
) -> str:
    """Edit an existing deposit."""
    files_dict = None if draft_files is None else draft_files.to_dict()
    record = draft.to_dict()

    template_context = get_deposit_template_context(
        createUrl=f"/api/oer/records/{pid_value}/draft",
    )
    return render_template(
        "invenio_records_lom/records/deposit.html",
        files=files_dict,
        forms_config=template_context["forms_config"],
        permissions=draft.has_permissions_to(["new_version", "delete_draft"]),
        record=record,
        searchbar_config=template_context["searchbar_config"],
    )


@login_required
@pass_is_oer_certified
def uploads(*, is_oer_certified: bool = False) -> str:
    """Show overview of lom-records uploaded by user, upload further records."""
    avatar_url = current_user_resources.users_service.links_item_tpl.expand(
        g.identity,
        current_user,
    )["avatar"]

    if is_oer_certified:
        template = "invenio_records_lom/uploads.html"
    else:
        template = "invenio_records_lom/not_licensed_text.html"

    return render_template(
        template,
        # TODO: newer versions of the original template now also take `searchbar_config`
        # here
        # see `invenio_app_rdm/users_ui/views/dashboard.py:uploads`
        # also see `invenio_app_rdm/users_ui/templates/uploads.html`
        # searchbar_config={"searchUrl": ...}, #noqa: ERA001
        user_avatar=avatar_url,
    )

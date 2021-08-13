# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Default configuration."""

from __future__ import absolute_import, print_function

from flask_babelex import gettext as _
from invenio_indexer.api import RecordIndexer
from invenio_records_rest.facets import terms_filter
from invenio_records_rest.utils import allow_all, check_elasticsearch
from invenio_search import RecordsSearch

LOM_REST_ENDPOINTS = {
    "lomid": dict(
        pid_type="lomid",
        pid_minter="lomid",
        pid_fetcher="lomid",
        default_endpoint_prefix=True,
        record_class="invenio_records_lom:Lom",
        search_class=RecordsSearch,
        indexer_class="invenio_records_lom.indexer:LomRecordIndexer",
        search_index="lomrecords",
        search_type=None,
        record_serializers={
            "application/json": ("invenio_records_lom.serializers" ":json_v1_response"),
        },
        search_serializers={
            "application/json": ("invenio_records_lom.serializers" ":json_v1_search"),
        },
        record_loaders={
            "application/json": ("invenio_records_lom.loaders" ":json_v1"),
        },
        list_route="/lom/",
        item_route="/lom/<pid(lomid):pid_value>",
        default_media_type="application/json",
        max_result_window=10000,
        error_handlers=dict(),
        create_permission_factory_imp=allow_all,
        read_permission_factory_imp=check_elasticsearch,
        update_permission_factory_imp=allow_all,
        delete_permission_factory_imp=allow_all,
    ),
}
"""REST API for invenio-records-lom."""

LOM_REST_SORT_OPTIONS = dict(
    lomrecords=dict(
        bestmatch=dict(
            title=_("Best match"),
            fields=["_score"],
            default_order="desc",
            order=1,
        ),
        mostrecent=dict(
            title=_("Most recent"),
            fields=["-_created"],
            default_order="asc",
            order=2,
        ),
    )
)
"""Setup sorting options."""


LOM_REST_DEFAULT_SORT = dict(
    lomrecords=dict(
        query="bestmatch",
        noquery="mostrecent",
    )
)
"""Set default sorting options."""

# TODO: link with the base records:
# LOM_RECORD_INDEX = "records"

# TODO:
# Overwite to change the default indexer for lomrecords
# LOM_INDEXER_RECEIVER = None

LOM_REST_FACETS = dict(
    lomrecords=dict(
        aggs=dict(
            organization=dict(terms=dict(field="organization")),
        ),
        post_filters=dict(
            organization=terms_filter("organization"),
        ),
    )
)
"""Introduce searching facets."""

# Invenio-records-rest
# ===========
# See https://invenio-records-rest.readthedocs.io/en/latest/configuration.html

# RECORDS_REST_DEFAULT_CREATE_PERMISSION_FACTORY = deny_all
"""Default create permission factory: reject any request."""

# RECORDS_REST_DEFAULT_LIST_PERMISSION_FACTORY = allow_all
"""Default list permission factory: allow all requests"""

# RECORDS_REST_DEFAULT_READ_PERMISSION_FACTORY = check_elasticsearch
"""Default read permission factory: check if the record exists."""

# RECORDS_REST_DEFAULT_UPDATE_PERMISSION_FACTORY = deny_all
"""Default update permission factory: reject any request."""

# RECORDS_REST_DEFAULT_DELETE_PERMISSION_FACTORY = deny_all
"""Default delete permission factory: reject any request."""

# RECORDS_REST_ELASTICSEARCH_ERROR_HANDLERS = {
#     'query_parsing_exception': (
#         'invenio_records_rest.views'
#         ':elasticsearch_query_parsing_exception_handler'
#     ),
#     'query_shard_exception': (
#         'invenio_records_rest.views'
#         ':elasticsearch_query_parsing_exception_handler'
#     ),
# }
# """Handlers for ElasticSearch error codes."""

# RECORDS_REST_DEFAULT_RESULTS_SIZE = 10
# """Default search results size."""

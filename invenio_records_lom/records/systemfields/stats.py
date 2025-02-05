# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.

"""Cached transient field for record statistics."""

from invenio_rdm_records.records.systemfields import RecordStatisticsField
from invenio_search.proxies import current_search_client
from invenio_search.utils import build_alias_name

from ..statistics import LomStatistics


class LomRecordStatisticsField(RecordStatisticsField):
    """Field for lazy fetching and caching of tugraz record statistics.

    Note: (but not storing)
    """

    api = LomStatistics
    """lom api """

    def _get_record_stats(self, record) -> dict | None:  # noqa: ANN001
        """Get the record's statistics from either record or aggregation index."""
        stats = None
        recid, parent_recid = record["id"], record.parent["id"]

        try:
            # for more consistency between search results and each record's details,
            # we try to get the statistics from the record's search index first
            # note: this field is dumped into the record's data before indexing
            #       by the search dumper extension "StatisticsDumperExt"
            res = current_search_client.get(
                # pylint: disable-next=protected-access
                index=build_alias_name(record.index._name),  # noqa: SLF001
                id=record.id,
                params={"_source_includes": "stats"},
            )
            stats = res["_source"]["stats"]
        except Exception:  # noqa: BLE001
            stats = None

        # as a fallback, use the more up-to-date aggregations indices
        return stats or self.api.get_record_stats(
            recid=recid,
            parent_recid=parent_recid,
        )

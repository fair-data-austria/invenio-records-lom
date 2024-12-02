# -*- coding: utf-8 -*-
#
# Copyright (C) 2024 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Advanced vocabulary-manipulation not covered by VocabularyService methods."""

import dataclasses
from copy import copy
from operator import attrgetter
from typing import NamedTuple

import jinja2
from invenio_access.permissions import system_identity
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_records_resources.services.uow import UnitOfWork, unit_of_work
from invenio_vocabularies.proxies import current_service as vocabulary_service
from invenio_vocabularies.records.models import VocabularyMetadata, VocabularyType

__all__ = (
    "VocabularyDeleteItem",
    "VocabularyImportItem",
    "delete_vocabulary",
    "delete_vocabulary_entry",
    "import_vocabulary",
    "undelete_vocabulary_entry",
)

PID_TYPE_MAX_LEN = 6  # sql-table `pidstore_pid` has column `pid_type` as VARCHAR[6]


class EnsureTypeTuple(NamedTuple):
    """Typed tuple for better return-type."""

    pid_type: str
    type_created: bool


@dataclasses.dataclass
class VocabularyImportItem:
    """Holds information on work done, similar to services' `Item`-classes."""

    vocabulary_id: str
    pid_type: str
    vocabulary_type_created: bool = False
    added_entries_ids: list[str] = dataclasses.field(default_factory=list)
    unchanged_entries_ids: list[str] = dataclasses.field(default_factory=list)
    undeleted_entries_ids: list[str] = dataclasses.field(default_factory=list)
    updated_entries_ids: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class VocabularyDeleteItem:
    """Holds information on work done, similar to services' `Item`-classes."""

    vocabulary_id: str
    pid_type: str
    vocabulary_type_deleted: bool = False
    deleted_entries_ids: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class VocabularyEntry:
    """Holds vocabulary-information read from database."""

    id: str = ""
    props: dict[str, str] = dataclasses.field(default_factory=dict)
    title: dict[str, str] = dataclasses.field(default_factory=dict)


@unit_of_work()
def ensure_type(
    vocabulary_id: str,
    /,  # @unit_of_work requires at least one positional arg in functions it decorates
    pid_type: str | None = None,
    uow: UnitOfWork = None,
) -> EnsureTypeTuple:
    """Ensure various things about the vocabulary-type associated with `vocabulary_id`.

    sample call:

    .. code-block:: python

        ensured_pid_type, type_created = ensure_type('vocabulary_id', pid_type='nmofvc')

    If there is no entry in `vocabularies_types` table for `vocabulary_id`, create one.
    `pid_type` is only required when creating such entry.

    :param str vocabulary_id: id of vocabulary whose type is to be checked
    :param str pid_type: pid-type to check against, used to create type if none exists
    :param UnitOfWork uow: larger unit-of-work this func-call is part of, if any
    :return: a named-tuple of the form (ensured_pid_type:str, pid_type_was_created:bool)
    :rtype: EnsureTypeTuple
    """
    type_created = False
    pid_type_in_db: str | None = (
        VocabularyType.query.filter_by(id=vocabulary_id)
        .with_entities(VocabularyType.pid_type)
        .scalar()
    )

    if pid_type_in_db is None and pid_type is None:
        msg = "couldn't automatically get `pid_type` when none was given"
        raise ValueError(msg)
    if (
        pid_type_in_db is not None
        and pid_type is not None
        and pid_type_in_db != pid_type
    ):
        msg = f"passed pid-type differs from registered: {pid_type_in_db!r} (db) / {pid_type!r} (passed)"
        raise ValueError(msg)
    if pid_type is not None and not (1 <= len(pid_type) <= PID_TYPE_MAX_LEN):
        msg = f"pid-types need to be 1 to {PID_TYPE_MAX_LEN} letters long: was {pid_type!r}"
        raise ValueError(msg)

    if pid_type_in_db is None:
        vocabulary_service.create_type(
            identity=system_identity,
            id=vocabulary_id,
            pid_type=pid_type,
            uow=uow,
        )
        type_created = True
    else:
        pid_type = pid_type_in_db

    return EnsureTypeTuple(pid_type=pid_type, type_created=type_created)


@unit_of_work()
def import_vocabulary(
    entries: list[dict],
    /,  # @unit_of_work requires at least one positional arg in functions it decorates
    vocabulary_id: str,
    pid_type: str | None = None,
    overwrite: bool = False,  # noqa: FBT001, FBT002
    uow: UnitOfWork = None,
) -> VocabularyImportItem:
    """Import a vocabulary into database.

    sample call:

    .. code-block:: python

        import_item = import_vocabulary(
            [{"id": "id-of-entry", "title": {"en": "Title"}, ...}, ...],
            vocabulary_id="nameofvocabulary",
            pid_type="nmofvc",  # optional for previously imported vocabularies
            overwrite=False,
        )

    If there is no entry in `vocabularies_types` table for `vocabulary_id`, create one.
    `pid_type` is only required when creating such entry.
    Then, every entry in `entries` is imported to `vocabularies_metadata` table.
    (entries need conform to `VocabularySchema`)
    When encountering an already imported entry, `overwrite` signals whether to keep
    the current entry or to overwrite with the passed-in entry.

    :param list[dict] entries: entries to import
    :param str vocabulary_id: all-lowercase as-one-word name of the vocabulary
    :param str pid_type: for referencing vocabulary from `pidstore_pid` table, <=6 chars
    :param bool overwrite: whether to overwrite already imported entries
    :param UnitOfWork uow: larger unit-of-work this func-call is part of, if any
    :return: an item containing information on import-work done
    :rtype: VocabularyImportItem
    """
    pid_type, type_created = ensure_type(vocabulary_id, pid_type=pid_type, uow=uow)
    result_item = VocabularyImportItem(
        vocabulary_id=vocabulary_id,
        pid_type=pid_type,
        vocabulary_type_created=type_created,
    )

    # load entries
    registered_entry_ids = {
        row.json["id"]
        for row in VocabularyMetadata.query
        if row.json is not None and row.json["type"]["id"] == vocabulary_id
    }
    soft_deleted_entry_ids = {
        pid.pid_value
        for pid in PersistentIdentifier.query.filter_by(
            pid_type=pid_type,
            status=PIDStatus.DELETED,
        )
    }
    for entry in entries:
        entry = copy(entry)  # shallow copy suffices  # noqa: PLW2901
        entry["type"] = vocabulary_id

        is_soft_deleted = entry["id"] in soft_deleted_entry_ids
        is_registered = entry["id"] in registered_entry_ids
        if is_soft_deleted:
            undelete_vocabulary_entry(vocabulary_id, entry["id"], pid_type=pid_type)
            vocabulary_service.update(
                identity=system_identity,
                id_=(vocabulary_id, entry["id"]),
                data=entry,
                uow=uow,
            )
            result_item.undeleted_entries_ids.append(entry["id"])
        elif not is_registered:
            vocabulary_service.create(identity=system_identity, data=entry, uow=uow)
            result_item.added_entries_ids.append(entry["id"])
        elif overwrite:
            vocabulary_service.update(
                identity=system_identity,
                id_=(vocabulary_id, entry["id"]),
                data=entry,
                uow=uow,
            )
            result_item.updated_entries_ids.append(entry["id"])
        else:
            result_item.unchanged_entries_ids.append(entry["id"])

    return result_item


@unit_of_work()
def undelete_vocabulary_entry(
    vocabulary_id: str,
    /,  # @unit_of_work requires at least one positional arg in functions it decorates
    entry_id: str,
    pid_type: str | None = None,
    uow: UnitOfWork = None,
) -> None:
    """Undelete soft-deleted entry.

    :param str vocabulary_id: id of the entry's vocabulary
    :param str entry_id: id of the entry within its vocabulary
    :param UnitOfWork uow: larger unit-of-work this func-call is part of, if any
    """
    if pid_type is None:
        vocabulary_type = VocabularyType.query.filter_by(id=vocabulary_id).one()
        pid_type = vocabulary_type.pid_type

    # undelete `pid_type` for `entry["id"]`
    # requires vocabulary_service to use the default pid_provider
    pid = PersistentIdentifier.get(pid_type=pid_type, pid_value=entry_id)
    pid.status = PIDStatus.REGISTERED
    uow.session.add(pid)
    item = vocabulary_service.read(
        identity=system_identity,
        id_=(vocabulary_id, entry_id),
    )
    item._record.undelete()  # noqa: SLF001


@unit_of_work()
def delete_vocabulary_entry(
    vocabulary_id: str,
    /,  # @unit_of_work requires at least one positional arg in functions it decorates
    entry_id: str,
    uow: UnitOfWork = None,
) -> None:
    """Delete from database all info associated with given entry.

    :param str vocabulary_id: id of the entry's vocabulary
    :param str entry_id: id of the entry within the vocabulary
    :param UnitOfWork uow: larger unit-of-work this func-call is part of, if any
    """
    entry_item = vocabulary_service.read(
        identity=system_identity,
        id_=(vocabulary_id, entry_id),
    )
    # part of entry's data in `vocabularies_metadata`
    uow.session.delete(entry_item._record.model)  # noqa: SLF001
    # part of entry's data in `pidstore_pid`
    uow.session.delete(entry_item._record.pid)  # noqa: SLF001


@unit_of_work()
def delete_vocabulary(
    vocabulary_id: str,
    /,  # @unit_of_work requires at least one positional arg in functions it decorates
    uow: UnitOfWork = None,
) -> VocabularyDeleteItem:
    """Delete a vocabulary from database.

    :param str vocabulary_id: id of the to-be-deleted vocabulary
    :param UnitOfWork uow: larger unit-of-work this func-call is part of, if any
    :return: an item containing information on deletion-work done
    :rtype: VocabularyDeleteItem
    """
    vocabulary_type = VocabularyType.query.filter_by(id=vocabulary_id).one_or_none()
    pid_type = vocabulary_type.pid_type if vocabulary_type is not None else None
    result_item = VocabularyDeleteItem(vocabulary_id=vocabulary_id, pid_type=pid_type)

    entry_ids = {
        row.json["id"]
        for row in VocabularyMetadata.query.with_entities(VocabularyMetadata.json)
        if row.json is not None and row.json["type"]["id"] == vocabulary_id
    }
    for entry_id in entry_ids:
        delete_vocabulary_entry(vocabulary_id, entry_id, uow=uow)
        result_item.deleted_entries_ids.append(entry_id)

    if vocabulary_type is not None:
        uow.session.delete(vocabulary_type)
        result_item.vocabulary_type_deleted = True

    return result_item


def read_vocabulary(vocabulary_id: str) -> list[VocabularyEntry]:
    """Read list of vocabulary-entries from opensearch."""
    # vocabulary_service caches calls to .read_all, making this fast enough
    entries_item = vocabulary_service.read_all(
        system_identity,
        ["id", "props", "title"],
        vocabulary_id,
        # maximum result window for opensearch is 10_000
        # bigger number of results would have to use opensearch's scroll-API instead
        # our currently biggest vocab is 'oefos' (with ~1500 entries)
        # so no scroll-API necessary for now...
        max_records=10_000,
    )

    # usual way to parse `entries_item` is `entries_item.to_dict()['hits']['hits']`
    # but that takes >1second to parse 'oefos'-vocabulary alone...
    # since we don't need the advanced parsing of `.to_dict()`, reach into `._results`
    result = [
        VocabularyEntry(id=hit.id, props=getattr(hit, "props", {}), title=hit.title)
        for hit in entries_item._results  # noqa: SLF001
    ]
    result.sort(key=attrgetter("id"))

    return result


def expand_vocabulary(vocabulary_id: str, /, **template_strings: str) -> dict[str, str]:
    """Fill a dict with info from database according to jinja template-strings.

    Example:
        >>> expand_vocabulary("oefos", name="{{title.en}}", value="{{id}}")
        {
            101001: {"name": "Algebra", "value": 101001},
            101002: {"name": "Analysis", "value": 101002},
            101003: {"name": "Applied geometry", "value": 101003},
            ...
        }
        # kwarg-names become keys to returned dict
        # kwarg-values are jinja-templates for values to returned dict

    The following names may be used in passed-in templates:
    - id: str  # entry-id of vocabulary-entry
    - props: dict[str, str]  # contents and existence of this depend on specific vocabulary
    - title: dict[str, str]  # keys are language-codes, values are title in that language

    """
    # we got templating needs beyond what str.format can provide, so use jinja:
    jinja_env = jinja2.Environment(autoescape=True)
    templates_by_name = {
        name: jinja_env.from_string(template_string)
        for name, template_string in template_strings.items()
    }

    result = {}
    for entry in read_vocabulary(vocabulary_id):
        result[entry.id] = {
            name: template.render(id=entry.id, props=entry.props, title=entry.title)
            for name, template in templates_by_name.items()
        }

    return result

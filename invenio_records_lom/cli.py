# -*- coding: utf-8 -*-
#
# Copyright (C) 2020-2024 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Click command-line interface for LOM module."""
from __future__ import annotations

import json
from copy import deepcopy
from importlib import metadata, resources
from itertools import count
from typing import TYPE_CHECKING

import yaml
from click import Path, argument, echo, group, option, secho, style
from faker import Faker
from flask.cli import with_appcontext
from invenio_access.permissions import system_identity
from invenio_vocabularies.proxies import current_service as vocabulary_service
from invenio_vocabularies.records.models import VocabularyMetadata, VocabularyType
from sqlalchemy.orm.exc import NoResultFound

from .fixtures import publish_fake_record, publish_fake_record_over_celery
from .proxies import current_records_lom
from .records.models import LOMRecordMetadata
from .resources.serializers.oai.schema import LOMToOAISchema
from .utils import DotAccessWrapper
from .utils.vocabularies import (
    VocabularyDeleteItem,
    VocabularyImportItem,
    delete_vocabulary,
    delete_vocabulary_entry,
    import_vocabulary,
)

if TYPE_CHECKING:
    from importlib.abc import Traversable


@group()
def lom() -> None:
    """CLI-group for "invenio lom" commands."""


@lom.command("rebuild-index")
@with_appcontext
def rebuild_index() -> None:
    """Reindex all drafts, records."""
    secho("Reindexing records and drafts...", fg="green")

    rec_service = current_records_lom.records_service
    rec_service.rebuild_index(identity=system_identity)

    secho("Reindexed records!", fg="green")


@lom.command()
@with_appcontext
@option(
    "--pid",
    "-p",
    "pids_to_check",
    default=[],
    multiple=True,
    type=str,
    help="PIDs to check. If never used, check all records.",
)
def check(pids_to_check: tuple[str]) -> None:
    """Check records in SQL-database against marshmallow-schema for OAI.

    Note: this does not guarantee by itself that OAI-PMH API works correctly, since
    (1) Records in opensearch might not mirror records in SQL-database, call `invenio
        lom reindex` to remedy this.
    (2) Records that pass OAI-schema verification might still not play nicely with
        OAI-PMH harvesters
    That said, passing OAI-schema *is* a prerequisite for OAI-PMH API working correctly
    """
    json_by_pid = {}
    counter = count()  # running count to create differing unkwown pids
    for record in LOMRecordMetadata.query.all():
        json = record.json or {}
        if not json:
            continue
        pid = json.get("id") or f"unknown #{next(counter):0>2}"
        json_by_pid[pid] = json

    if not pids_to_check:
        pids_to_check = json_by_pid.keys()

    for pid in pids_to_check:
        if pid not in json_by_pid:
            secho(f"{pid}: could not find a record to this pid", fg="red")
            continue
        try:
            json = json_by_pid[pid]
            LOMToOAISchema().load(json.get("metadata", {}))
            secho(f"{pid}: Success", fg="green")
        except Exception as e:  # noqa: BLE001
            secho(f"{pid}: {e!r}", fg="red")


@lom.command()
@with_appcontext
@option(
    "--number",
    "-n",
    default=100,
    show_default=True,
    type=int,
    help="Number of records to be created.",
)
@option("--seed", "-s", default=42, type=int, help="Seed for RNG.")
@option(
    "--backend",
    "-b",
    default=False,
    type=bool,
    is_flag=True,
    help="Create in backend for large datasets",
)
def demo(number: int, seed: int, *, backend: bool) -> None:
    """Publish `number` fake LOM records to the database, for demo purposes."""
    secho(f"Creating {number} LOM demo records", fg="green")

    fake = Faker()
    Faker.seed(seed)

    for _ in range(number):
        if backend:
            publish_fake_record_over_celery(fake)
        else:
            publish_fake_record(fake)

    secho("Published fake LOM records to the database!", fg="green")


@lom.command()
@with_appcontext
def reindex() -> None:
    """Reindex all published records from SQL-database in opensearch-indices."""
    secho("Reindexing LOM records...", fg="green")

    record_ids = [
        record.json["id"]
        for record in LOMRecordMetadata.query.all()
        if record.json and "id" in record.json
    ]

    service = current_records_lom.records_service
    indexer = service.indexer
    for record_id in record_ids:
        record_api_object = service.record_cls.pid.resolve(record_id)
        indexer.index(record_api_object)

    secho("Successfully reindexed LOM records!", fg="green")


#
# vocabularies commands
#
@lom.group()
def vocabularies() -> None:
    """CLI-group for `invenio_records_lom`'s flavor of vocabulary commands."""


def echo_import_item(item: VocabularyImportItem) -> None:
    """Echo information within `item`."""
    if item.vocabulary_type_created:
        secho(f"added vocabulary-type with id {item.vocabulary_id!r}", fg="green")
    else:
        secho(f"vocabulary-type for id {item.vocabulary_id!r} already existed")

    secho(
        # note: implicit string concatenation
        f"{item.vocabulary_id!r}: "
        f"{len(item.added_entries_ids)} added, "
        f"{len(item.undeleted_entries_ids)} undeleted, "
        f"{len(item.updated_entries_ids)} updated, "
        f"{len(item.unchanged_entries_ids)} left as-is",
        fg="green",
    )


def echo_delete_item(item: VocabularyDeleteItem) -> None:
    """Echo information within `item`."""
    if item.vocabulary_type_deleted:
        secho(f"deleted vocabulary-type with id {item.vocabulary_id!r}", fg="red")
    else:
        secho(f"vocabulary-type for id {item.vocabulary_id!r} already deleted")

    secho(
        f"{item.vocabulary_id!r}: {len(item.deleted_entries_ids)} entries deleted",
        fg="red",
    )


@vocabularies.command("list")
@argument(
    "vocabulary-id",
    required=False,
    type=str,
)
@with_appcontext
def list_vocabularies(vocabulary_id: str | None) -> None:
    """List vocabulary contents.

    \b
    Examples:
      invenio lom vocabularies list
      invenio lom vocabularies list oerlicenses
      invenio lom vocabularies list oerlicenses | grep "CC*BY"

    Call without arguments to list all registered vocabulary-types.
    Call with the id of a vocabulary-type to list metadata stored for that type.
    """  # noqa: D301  # \b prevents click's line-wrapping
    if vocabulary_id is None:
        registered_types = VocabularyType.query.order_by(VocabularyType.id).all()
        pid_type_by_id = {row.id: row.pid_type for row in registered_types}
        secho(f"number of types: {len(registered_types)}", fg="green")
        for id_, pid_type in pid_type_by_id.items():
            echo(f"{pid_type:6} " + style(id_, bold=True, fg="blue"))

    else:
        jsons = [row.json for row in VocabularyMetadata.query.all()]
        relevant_jsons = [j for j in jsons if j["type"]["id"] == vocabulary_id]
        secho(
            f"number of {vocabulary_id!r} entries: {len(relevant_jsons)}",
            fg="green",
        )
        for json_ in relevant_jsons:
            data = {k: v for k, v in json_.items() if k in ["title", "props", "tags"]}
            secho(style(json_["id"], fg="cyan", bold=True) + " " + str(data))

        # check whether `vocabulary_id` has a row in vocabulary_types table
        # absence should still run above code, but output an error
        # error is output last as to become most recent line in terminal
        try:
            VocabularyType.query.filter_by(id=vocabulary_id).one()
        except NoResultFound:
            msg = f"no entry found in vocabularies_types for given id {vocabulary_id!r}"
            secho(msg, fg="red", err=True)


@vocabularies.command("import")
@option(
    "--vocabulary-id",
    help="name under which the vocabulary can later be read (lowercase, as one word)",
    required=True,
    type=str,
)
@option(
    "--pid-type",
    help="PID-type under which to register this vocabulary in `pidstore_pid` (<=6 letters)",
    type=str,
)
@option(
    "--file",
    help="path to input YAML file",
    required=True,
    type=Path(dir_okay=False, exists=True),
)
@option(
    "--force",
    default=False,
    help="whether to overwrite already imported entries",
    is_flag=True,
    type=bool,
)
@with_appcontext
def import_vocabulary_command(
    vocabulary_id: str,
    pid_type: str,
    file: str,
    force: bool,  # noqa: FBT001
) -> None:
    """Import vocabulary from file.

    \b
    Example:
        invenio lom vocabularies import
            --vocabulary-id oefos
            --pid-type oefos
            --file /path/to/oefos.yaml

    `pid_type` is optional if a vocabulary of id `vocabulary_id` was imported before.
    Per default, does NOT overwrite already imported entries, but adds new entries.
    Use `--force` to overwrite previously imported entries with data from yaml-file.
    """  # noqa: D301  # \b prevents click's line-wrapping
    with open(file, encoding="utf-8") as fh:  # noqa: PTH123
        data = yaml.safe_load(fh)
    import_item = import_vocabulary(
        data,
        vocabulary_id=vocabulary_id,
        pid_type=pid_type,
        overwrite=force,
    )
    echo_import_item(import_item)


@vocabularies.command()
@with_appcontext
def setup() -> None:
    """Set up `invenio_records_lom`'s vocabularies."""
    # get invenio_record_lom's entrypoint for vocabulary-fixtures
    (fixture_entrypoint,) = metadata.entry_points(
        group="invenio_rdm_records.fixtures",
        name="invenio_records_lom",
    )

    # that entrypoint's `.module` is path to a submodule within invenio_records_lom,
    # e.g. "invenio_records_lom.fixtures.data"
    fixture_module_id: str = fixture_entrypoint.module

    # modules need NOT be physical files (could be file-entry in a zip-file, ...)
    # this is abstracted away by `resources.files` and `Traversable`
    directory: Traversable = resources.files(fixture_module_id)
    with directory.joinpath("vocabularies.yaml").open(encoding="utf-8") as file:
        vocabularies_import_info: dict = yaml.safe_load(file)

    # import all invenio_records_lom vocabularies
    for vocabulary_id, info in vocabularies_import_info.items():
        with directory.joinpath(info["data-file"]).open(encoding="utf-8") as file:
            entries = yaml.safe_load(file)
        import_item = import_vocabulary(
            entries,
            vocabulary_id=vocabulary_id,
            pid_type=info["pid-type"],
            overwrite=False,
        )
        echo_import_item(import_item)


@vocabularies.command()
@argument(
    "vocabulary-ids",
    nargs=-1,
    required=True,
    type=str,
)
@with_appcontext
def delete(vocabulary_ids: list[str]) -> None:
    """Remove vocabulari(es).

    Example: invenio lom vocabularies delete highereducationresourcetypes oefos
    """
    for vocabulary_id in vocabulary_ids:
        delete_item = delete_vocabulary(vocabulary_id)
        echo_delete_item(delete_item)


@vocabularies.command()
@option(
    "--vocabulary-id",
    help="vocabulary to add entry to",
    required=True,
    type=str,
)
@option(
    "--entry-json-str",
    help="json of the new entry, as a str",
    required=True,
    type=str,
)
@with_appcontext
def add_entry(vocabulary_id: str, entry_json_str: str) -> None:
    """Add entry to vocabulary.

    \b
    Examples:
        invenio lom vocabularies add-entry
            --vocabulary-id oefos
            --entry-json-str '{"id": "name", "title": {"en": "en_title"}}'
        invenio lom vocabularies add-entry
            --vocabulary-id oerlicenses
            --entry-json-str "$(< /path/to/entry.json)"

    Note that the entry's json needs to be a dict with at least an "id" member.
    """  # noqa: D301  # \b prevents click's line-wrapping
    entry_json = json.loads(entry_json_str)
    if VocabularyType.query.filter_by(id=vocabulary_id).one_or_none() is None:
        msg = f"no type found for given vocabulary-id {vocabulary_id!r}"
        secho(msg, fg="red", err=True)
        return

    jsons = [row.json for row in VocabularyMetadata.query]
    entry_ids_in_db = [
        json["id"] for json in jsons if json["type"]["id"] == vocabulary_id
    ]
    entry_id = entry_json["id"]
    if entry_id in entry_ids_in_db:
        secho(f"entry already exists: {entry_id!r}", fg="red", err=True)
        return

    entry_json["type"] = vocabulary_id
    vocabulary_service.create(identity=system_identity, data=entry_json)
    secho(f"created new entry {entry_id!r} in {vocabulary_id!r}", fg="green")


@vocabularies.command()
@option(
    "--vocabulary-id",
    help="the to-be-updated entry's vocabulary-id",
    required=True,
    type=str,
)
@option(
    "--entry-id",
    help="the id of the to-be-updated entry within its vocabulary",
    required=True,
    type=str,
)
@option(
    "--key",
    help="key to the to-be-up-dated value, supports dot-notation",
    required=True,
    type=str,
)
@option(
    "--str-value",
    help="value to set data at KEY to, used as-is",
    type=str,
)
@option(
    "--json-value",
    help="value to set data at KEY to, json-parsed before use",
    type=str,
)
@with_appcontext
def update_entry(
    vocabulary_id: str,
    entry_id: str,
    key: str,
    str_value: str | None,
    json_value: str | None,
) -> None:
    """Update data within entry in vocabulary.

    \b
    Examples:
        update-entry --vocabulary-id vid --entry-id eid --key props.name --str-value me
        update-entry --vocabulary-id vid --entry-id eid --key tags.[] --str-value new-tag
        update-entry --vocabulary-id vid --entry-id eid --key "" --json-value "$(< file.json)"

    For setting a value to `key`, `DotAccessWrapper` is used internally; hence all its
    features can be used:
    "props.short_name" updates data["props"]["short_name"] (creating "props" if needed).
    "tags.[] appends to tags (creating data["tags"] as a list if needed).
    """  # noqa: D301  # \b prevents click's line-wrapping
    if (str_value is None and json_value is None) or (
        str_value is not None and json_value is not None
    ):
        secho(
            "must give exactly one of '--str-value', '--json-value'",
            fg="red",
            err=True,
        )
        return
    value = str_value if str_value is not None else json.loads(json_value)

    vocab_item = vocabulary_service.read(
        identity=system_identity,
        id_=(vocabulary_id, entry_id),
    )
    dot_access_wrapper = DotAccessWrapper(deepcopy(vocab_item.data))
    dot_access_wrapper[key] = value
    vocabulary_service.update(
        identity=system_identity,
        id_=(vocabulary_id, entry_id),
        data=dot_access_wrapper.data,
    )
    secho(
        f"updated entry {entry_id!r} in vocabulary {vocabulary_id!r}",
        fg="green",
    )


@vocabularies.command()
@option(
    "--vocabulary-id",
    help="to-be-deleted entry's vocabulary-id",
    required=True,
    type=str,
)
@option(
    "--entry-id",
    help="to-be-deleted entry's entry-id",
    required=True,
    type=str,
)
@with_appcontext
def delete_entry(vocabulary_id: str, entry_id: str) -> None:
    """Delete entry from vocabulary.

    Example: delete-entry --vocabulary-id oerlicenses --entry-id https://cre.../by/4.0/
    """
    delete_vocabulary_entry(vocabulary_id, entry_id=entry_id)
    secho(
        f"deleted entry {entry_id!r} from vocabulary {vocabulary_id!r}",
        fg="red",
    )


@vocabularies.command()
@option(
    "--vocabulary-id",
    help="vocabulary-id of the to-be-exported vocabulary",
    required=True,
    type=str,
)
@with_appcontext
def export(vocabulary_id: str) -> None:
    """Export vocabulary to stdout.

    \b
    Example:
        invenio lom vocabularies export --vocabulary-id oefos >oefos.yaml
    """  # noqa: D301  # \b prevents click's line-wrapping
    entries = []
    for vocabulary_type in VocabularyMetadata.query.all():
        if vocabulary_type.json["type"]["id"] != vocabulary_id:
            continue
        entry = {
            k: v
            for k, v in vocabulary_type.json.items()
            if k in ["id", "title", "props", "tags"]
        }
        entries.append(entry)

    entries.sort(key=lambda json: json["id"])
    secho(yaml.safe_dump(entries))
    secho(
        f"successfully exported vocabulary with id `{vocabulary_id}`",
        err=True,
        fg="green",
    )

    try:
        vocabulary_type = VocabularyType.query.filter_by(id=vocabulary_id).one()
        pid_type = vocabulary_type.pid_type
    except NoResultFound:
        secho(
            f"no pid-type found for vocabulary with id `{vocabulary_id}`",
            fg="red",
            err=True,
        )
    else:
        secho(
            f"exported vocabulary's pid-type was `{pid_type}`",
            fg="green",
            err=True,
        )

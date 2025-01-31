# -*- coding: utf-8 -*-
#
# Copyright (C) 2021-2025 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Service tests."""

import pytest
from flask_principal import Identity
from invenio_db.shared import SQLAlchemy, db
from invenio_pidstore.models import PersistentIdentifier, PIDStatus

from invenio_records_lom.records.models import (
    LOMDraftMetadata,
    LOMParentMetadata,
    LOMRecordMetadata,
    LOMVersionsState,
)
from invenio_records_lom.services import LOMRecordService

_ACCESS_CONFIGURATIONS = [
    {
        "files": "public",
        "record": "public",
        "embargo": {},
    },
    {
        "files": "restricted",
        "record": "restricted",
        "embargo": {},
    },
    {
        "files": "public",
        "record": "public",
        "embargo": {
            "until": "2030-12-31",
            "reason": "Test embargo for test record.",
            "active": True,
        },
    },
    {
        "files": "restricted",
        "record": "restricted",
        "embargo": {
            "until": "2030-12-31",
            "reason": "Test embargo for test record.",
            "active": True,
        },
    },
]


def _get_session_commits(db: SQLAlchemy) -> set:
    """Get objects that have already been commited in this session."""
    return set(db.session.identity_map.values())


def _pick_by_cls(
    iterable,
    cls,
    *,
    assert_unique: bool = True,
) -> db.Model:
    """Get first obj from `iterable` whose class is `cls`."""
    instances = [obj for obj in iterable if isinstance(obj, cls)]
    if assert_unique:
        assert len(instances) == 1
    return instances[0]


@pytest.mark.parametrize(
    "access",
    _ACCESS_CONFIGURATIONS,
)
def test_create_draft(
    service: LOMRecordService,
    db: SQLAlchemy,
    identity: Identity,
    access: dict,
) -> None:
    """Test creating a draft, then test database changes."""
    title_langstring = {"langstring": {"#text": "Test", "lang": "en"}}
    data = {
        "access": access,
        "files": {"enabled": False},
        "metadata": {"general": {"title": title_langstring}},
        "resource_type": "course",
    }

    db_before = _get_session_commits(db)
    service.create(identity=identity, data=data)
    db_after = _get_session_commits(db)
    db_new_values = db_after - db_before  # the `-` is the set-difference operator

    new_parent = _pick_by_cls(db_new_values, LOMParentMetadata)
    new_draft = _pick_by_cls(db_new_values, LOMDraftMetadata)
    new_versions_state = _pick_by_cls(db_new_values, LOMVersionsState)

    new_pids = [new for new in db_new_values if isinstance(new, PersistentIdentifier)]
    assert len(new_pids) == 2
    parent_pid = next(pid for pid in new_pids if pid.object_uuid == new_parent.id)
    draft_pid = next(pid for pid in new_pids if pid.object_uuid == new_draft.id)

    # test database relations between new database-entries
    assert parent_pid.status == PIDStatus.NEW
    assert draft_pid.status == PIDStatus.NEW
    assert new_versions_state.next_draft_id == new_draft.id
    assert new_versions_state.parent_id == new_parent.id
    assert new_draft.parent_id == new_parent.id

    # test whether pid was added by service.create
    json = new_draft.json
    assert "metadata" in json
    assert "general" in json["metadata"]
    general = json["metadata"]["general"]
    json_pid = general["identifier"][0]["entry"]["langstring"]["#text"]
    assert json_pid == draft_pid.pid_value

    # TODO: can't find where the type has been added
    del data["metadata"]["type"]
    del json["metadata"]["general"]["identifier"]
    assert json["metadata"] == data["metadata"]
    assert "access" in json
    assert json["access"]["files"] == access["files"]
    assert json["access"]["record"] == access["record"]
    assert "files" in json
    assert "pid" in json
    assert json["pid"]["pid_type"] == "lomid"


@pytest.mark.parametrize(
    "access",
    _ACCESS_CONFIGURATIONS,
)
def test_publish(
    service: LOMRecordService,
    db: SQLAlchemy,
    identity: Identity,
    access: dict,
) -> None:
    """Test publishing a record, then test database changes."""
    title_langstring = {"langstring": {"#text": "Test", "lang": "en"}}
    data = {
        "access": access,
        "files": {"enabled": False},
        "metadata": {"general": {"title": title_langstring}},
        "resource_type": "course",
    }

    db_before = _get_session_commits(db)
    draft = service.create(identity=identity, data=data)
    service.publish(identity=identity, id_=draft.id)
    db_after = _get_session_commits(db)
    db_new_values = db_after - db_before  # the `-` is the set-difference operator

    new_parent = _pick_by_cls(db_new_values, LOMParentMetadata)
    new_draft = _pick_by_cls(db_new_values, LOMDraftMetadata)
    new_versions_state = _pick_by_cls(db_new_values, LOMVersionsState)
    new_record = _pick_by_cls(db_new_values, LOMRecordMetadata)

    new_pids = [obj for obj in db_new_values if isinstance(obj, PersistentIdentifier)]
    assert len(new_pids) == 2
    parent_pid = next(pid for pid in new_pids if pid.object_uuid == new_parent.id)
    draft_pid = next(pid for pid in new_pids if pid.object_uuid == new_draft.id)
    record_pid = next(pid for pid in new_pids if pid.object_uuid == new_record.id)
    assert draft_pid == record_pid

    # test database relations between new database-entries
    assert parent_pid.status == PIDStatus.REGISTERED
    assert record_pid.status == PIDStatus.REGISTERED
    assert new_versions_state.next_draft_id is None
    assert new_versions_state.parent_id == new_parent.id
    assert new_versions_state.latest_id == new_record.id
    assert new_draft.parent_id == new_parent.id
    assert new_record.parent_id == new_parent.id

    # test whether pid was added by service.create
    json = new_record.json
    assert "metadata" in json
    assert "general" in json["metadata"]
    general = json["metadata"]["general"]
    json_pid = general["identifier"][0]["entry"]["langstring"]["#text"]
    assert json_pid == record_pid.pid_value

    del json["metadata"]["general"]["identifier"]
    assert json["metadata"] == data["metadata"]
    assert "access" in json
    assert json["access"]["files"] == access["files"]
    assert json["access"]["record"] == access["record"]
    assert "files" in json
    assert "pid" in json
    assert json["pid"]["pid_type"] == "lomid"

# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Lom Api."""

from __future__ import absolute_import, print_function

from flask import current_app
from invenio_db import db
from invenio_jsonschemas import current_jsonschemas
from invenio_pidstore.models import PersistentIdentifier
from invenio_pidstore.resolver import Resolver
from invenio_records.api import Record
from invenio_records.models import RecordMetadata
from werkzeug.local import LocalProxy

from .signals import lomrecord_created

# TODO: uncomment to use the model for db manipulation
# from invenio_records_lom.models import LomMetadata


# TODO: Move somewhere appropriate (`invenio-records-pidstore`)
class PIDRecordMixin:
    """Persistent identifier mixin for records."""

    object_type = None
    pid_type = None

    @property
    def pid(self):
        """Return primary persistent identifier of the record."""
        return PersistentIdentifier.query.filter_by(
            object_uuid=self.id,
            object_type=self.object_type,
            pid_type=self.pid_type,
        ).one()

    @classmethod
    def resolve(cls, pid_value):
        """Resolve a PID value and return the PID and record."""
        return Resolver(
            pid_type=cls.pid_type,
            object_type=cls.object_type,
            getter=cls.get_record,
        ).resolve(pid_value)

    # TODO: See if needed or if it should be customizable
    # @property
    # def pids(self):
    #     """Return all persistent identifiers of the record."""
    #     return PersistentIdentifier.query.filter_by(
    #         object_uuid=self.id,
    #         object_type=self.object_type,
    #     ).all()


class LomRecordBase(Record, PIDRecordMixin):
    """Define API for Lom creation and manipulation."""

    object_type = "lom"
    pid_type = "lomid"

    # TODO: Lom model doesn't have versioninig, some methods from
    # "invenio_records.api.RecordBase" have to be overridden/removed

    # TODO: uncomment and use the lom model instead of Records model
    # model_cls = LomMetadata
    model_cls = RecordMetadata

    schema = LocalProxy(
        lambda: current_jsonschemas.path_to_url(
            current_app.config.get("LOM_SCHEMA", "lomrecords/lom-v1.0.0.json")
        )
    )

    @classmethod
    def create(cls, data, id_=None, **kwargs):
        """Create a new Lom instance and store it in the database."""
        with db.session.begin_nested():
            data["$schema"] = str(cls.schema)
            lom = cls(data)
            lom.validate(**kwargs)
            lom.model = cls.model_cls(id=id_, json=lom)
            db.session.add(lom.model)
            lomrecord_created.send(lom)
        return lom

    def clear(self):
        """Clear but preserve the schema field."""
        schema = self["$schema"]
        # TODO: since this is a "system" field, in the future it should be
        # auto-preserved
        collections = self.get("_collections")
        super(LomRecordBase, self).clear()
        self["$schema"] = schema
        if collections:
            self["_collections"] = collections

    def delete(self, force=False):
        """Delete a lom."""
        with db.session.begin_nested():
            if force:
                db.session.delete(self.model)
            else:
                self.model.delete()
        return self

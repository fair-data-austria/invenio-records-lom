# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Proxy definitions."""

from __future__ import absolute_import, print_function

from blinker import Namespace

_signals = Namespace()

lomrecord_created = _signals.signal("lomrecord_created")

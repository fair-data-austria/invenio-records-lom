# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Proxy definitions."""

from __future__ import absolute_import, print_function

from flask import current_app
from werkzeug.local import LocalProxy

current_lomrecord = LocalProxy(
    lambda: current_app.extensions["invenio-records-lom"],
)
"""Proxy to the extension."""

Lom = LocalProxy(
    lambda: current_app.extensions["invenio-records-lom"].lom_cls,
)
"""Proxy for current lom class."""

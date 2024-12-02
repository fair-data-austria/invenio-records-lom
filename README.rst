..
    Copyright (C) 2020 Graz University of Technology.

    invenio-records-lom is free software; you can redistribute it and/or modify it
    under the terms of the MIT License; see LICENSE file for more details.

=====================
 invenio-records-lom
=====================

.. image:: https://img.shields.io/github/license/tu-graz-library/invenio-records-lom.svg
        :target: https://github.com/tu-graz-library/invenio-records-lom/blob/master/LICENSE

.. image:: https://github.com/tu-graz-library/invenio-records-lom/workflows/CI/badge.svg
        :target: https://github.com/tu-graz-library/invenio-records-lom/actions

.. image:: https://img.shields.io/coveralls/tu-graz-library/invenio-records-lom.svg
        :target: https://coveralls.io/r/tu-graz-library/invenio-records-lom

.. image:: https://img.shields.io/pypi/v/invenio-records-lom.svg
        :target: https://pypi.org/pypi/invenio-records-lom

.. image:: https://readthedocs.org/projects/invenio-records-lom/badge/?version=latest
        :target: https://invenio-records-lom.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
        :target: https://github.com/psf/black

Invenio module that adds a data model based on LOM (Learning Object Metadata).
The specification of the LOM-dialect used by this module can be found here: `LOM-UIBK (only available in german) <https://oer-repo.uibk.ac.at/lom/latest/>`_

Further documentation is available on
https://invenio-records-lom.readthedocs.io/

This package serves as the LOM datamodel for the repository. It is planned to
implement the newest version of the standard.

Following features are already implemented or will be implemented in the near
feature:

  - [ ] create a record

    - [ ] over rest API
    - [ ] over GUI

  - [ ] modify a record

    - [ ] over rest API
    - [ ] over GUI

  - [ ] validate records with meaningful error messages

    - [ ] over rest API
    - [ ] over GUI

  - [ ] upload files

    - [ ] implement SWORD
    - [ ] over rest API
    - [ ] over GUI

  - [ ] apply the same permission handling as for the rest of the repository

    - [ ] create a curator for LOM records over the normal interface for it
    - [ ] inherit ownership of records
    - [ ] lock records / make read only
    - [ ] allow creation only for users with special roles

  - [ ] landing page

    - [ ] export record as json

  - [ ] search about a record

    - [ ] create a search page only for LOM records
    - [ ] make records findable also in the common search (search over all
      standards used in the repository)

  - [ ] add a DOI

    - [ ] with a special DOI schema (e.g. PREFIX/oer-NUMBER)

  - [ ] incorporate controlled vocabularies

    - [ ] resource types
    - [ ] licences
    - [ ] oefos

  - [ ] add LOM records to a community
  - [ ] provide the records to the OAI-PMH server

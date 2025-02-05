# -*- coding: utf-8 -*-
#
# Copyright (C) 2022-2025 Graz University of Technology.
#
# invenio-records-lom is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""LOMMetadata class for creation of LOM-compliant metadata."""

from copy import deepcopy
from types import MappingProxyType

from ..resources.serializers.utils import get_text
from .util import (
    DotAccessWrapper,
    catalogify,
    get_learningresourcetypedict,
    get_oefosdict,
    langstringify,
    standardize_url,
    vocabularify,
)


class BaseLOMMetadata:
    """Base LOM Metadata."""

    def __init__(
        self,
        json: dict | None = None,
        *,
        overwritable: bool = False,
    ) -> None:
        """Construct LOMMetadata."""
        record_json = deepcopy(json or {})
        self.record = DotAccessWrapper(record_json, overwritable=overwritable)

    @property
    def json(self) -> dict:
        """Pipe-through for convenient access of underlying json."""
        return self.record.data

    def get_identifier(self, catalog: str) -> str:
        """Get identifier by catalog."""
        for identifier in self.record["general.identifier"]:
            if identifier["catalog"] == catalog:
                return identifier["entry"]["langstring"]["#text"]
        return ""

    def deduped_append(self, parent_key: str, value: str | bool | list | dict) -> None:
        """Append `value` to `self.record[key]` if not already appended."""
        self.record.setdefault(parent_key, [])
        parent = self.record[parent_key]

        if not isinstance(parent, list):
            parent = [parent]

        if value not in parent:
            parent.append(value)

    def append_contribute(
        self,
        name: str,
        role: str,
        path: str | None = None,
        description: str | None = None,  # noqa: ARG002
    ) -> None:
        """Append contribute.

        :param str name: The name of the contributing person/organisation
        :param str role: One of values LOM recommends for `lifecycle.contribute.role`
        """
        contribute = {
            "role": vocabularify(role.title()),
            "entity": [name],
        }
        self.deduped_append(path, contribute)


class LOMCourseMetadata(BaseLOMMetadata):
    """Lom course Metadata."""

    def set_title(self, title: str, language_code: str) -> None:
        """Set course title."""
        self.record["course.title"] = langstringify(title, lang=language_code)

    def append_identifier(self, id_: str, catalog: str) -> None:
        """Append course identifier."""
        self.deduped_append(
            "course.identifier",
            catalogify(id_, catalog=catalog),
        )

    def append_keyword(self, keyword: str, language_code: str) -> None:
        """Append keyword."""
        self.deduped_append(
            "course.keyword",
            langstringify(keyword, lang=language_code),
        )

    def append_context(self, context: str) -> None:
        """Append context.

        :param str context: One of the values LOM recommends for `educational.context`
        """
        self.deduped_append("course.context", vocabularify(context))

    def append_language(self, language_code: str) -> None:
        """Append language."""
        self.deduped_append("course.language", language_code)

    def set_version(self, version: str, datetime: str) -> None:
        """Set version.

        :param str version: The version of this metadata
        :param str datetime: The datetime-string of this version's release in isoformat
        """
        version_dict = langstringify(version)
        version_dict["datetime"] = datetime
        self.record["course.version"] = version_dict

    def append_description(
        self,
        description: str,
        language_code: str,
    ) -> None:
        """Append educational description."""
        self.deduped_append(
            "course.description",
            langstringify(description, lang=language_code),
        )

    def append_contribute(
        self,
        name: str,
        role: str,
        path: str | None = None,
        description: str | None = None,
    ) -> None:
        """Append contribute."""
        path = path or "course.contribute"
        super().append_contribute(name, role, path=path, description=description)


class LOMMetadata(BaseLOMMetadata):  # pylint: disable=too-many-public-methods
    """Helper-class for easy creation of LOM-metadata JSONs."""

    # learningresourcetypes according to `https://w3id.org/kim/hcrt/scheme`
    # used in LOM.educational.learningresourcetype
    # this maps (url-ending -> label-dict) where label-dict maps (lang-code -> label)
    learningresourcetype_labels = get_learningresourcetypedict()

    # oefos_dicts map (oefos_id -> oefos_name)
    # oefos_names are needed for filling in taxonpaths
    oefosdict_by_language = MappingProxyType(
        {
            "de": get_oefosdict("de"),
            "en": get_oefosdict("en"),
        },
    )

    ###############
    #
    # methods for manipulating LOM's `course` category
    #
    ###############

    def append_course(self, course: LOMCourseMetadata) -> None:
        """Append course."""
        # pylint: disable-next=unsupported-membership-test
        if "courses" not in self.record:
            self.record["courses"] = []

        courses = self.record["courses"]

        # pylint: disable-next=not-an-iterable
        versions = [course["course"]["version"] for course in courses]

        if course.record["course.version"] not in versions:
            self.record["courses"].append(course.record.data)

    def get_courses(self) -> list:
        """Get courses."""
        try:
            return self.record["courses"]
        except KeyError:
            return []

    ###############
    #
    # methods for manipulating LOM's `general` (1) category
    #
    ###############

    def append_identifier(self, id_: str, catalog: str) -> None:
        """Append identifier.

        :param str catalog: The name of the cataloging scheme (e.g. "ISBN")
        :param str id_: The value of the identifier within the cataloging scheme
        """
        self.deduped_append(
            "general.identifier",
            catalogify(id_, catalog=catalog),
        )

    def get_identifiers(self, *, text_only: bool = False) -> list:
        """Get identifiers."""
        try:
            identifiers = self.record["general.identifier"]
        except KeyError:
            return []

        if text_only:
            return [get_text(entry["entry"]) for entry in identifiers]

        return identifiers

    def set_title(self, title: str, language_code: str) -> None:
        """Set title."""
        self.record["general.title"] = langstringify(title, lang=language_code)

    def get_title(self, *, text_only: bool = False) -> str:
        """Get title."""
        try:
            title = self.record["general.title"]
        except KeyError:
            return ""

        if text_only:
            return get_text(title)

        return title

    def append_language(self, language_code: str) -> None:
        """Append language."""
        self.deduped_append("general.language", language_code)

    def get_languages(self) -> list:
        """Get languages."""
        try:
            languages = self.record["general.language"]
        except KeyError:
            return []

        if len(languages) > 0:
            return languages

        return []

    def append_description(self, description: str, language_code: str) -> None:
        """Append description."""
        self.deduped_append(
            "general.description",
            langstringify(description, lang=language_code),
        )

    def get_descriptions(self, *, text_only: bool = False) -> list:
        """Get descriptions."""
        try:
            descriptions = self.record["general.description"]
        except KeyError:
            return []

        if text_only:
            return [get_text(desc) for desc in descriptions]

        return descriptions

    def append_keyword(self, keyword: str, language_code: str) -> None:
        """Append keyword."""
        self.deduped_append(
            "general.keyword",
            langstringify(keyword, lang=language_code),
        )

    def get_keywords(self, *, text_only: bool = False) -> list:
        """Get keywords."""
        try:
            keywords = self.record["general.keyword"]
        except KeyError:
            return []

        if text_only:
            # pylint: disable-next=not-an-iterable
            return [get_text(subject) for subject in keywords]

        return self.record["general.keyword"]

    ###############
    #
    # methods for manipulating LOM's `lifeCycle` (2) category
    #
    ###############

    def set_version(self, version: str, datetime: str) -> None:
        """Set version.

        :param str version: The version of this metadata
        :param str datetime: The datetime-string of this version's release in isoformat
        """
        version_dict = langstringify(version)
        version_dict["datetime"] = datetime
        self.record["lifecycle.version"] = version_dict

    def append_contribute(
        self,
        name: str,
        role: str,
        path: str | None = None,
        description: str | None = None,
    ) -> None:
        """Append contribute.

        :param str name: The name of the contributing person/organisation
        :param str role: One of values LOM recommends for `lifecycle.contribute.role`
        """
        super().append_contribute(
            name,
            role,
            path=path or "lifecycle.contribute",
            description=description,
        )

    def get_contributors(
        self,
        *,
        name_only: bool = False,
        date_only: bool = False,
    ) -> list:
        """Get contributors."""
        try:
            contributes = self.record["lifecycle.contribute"]
        except KeyError:
            return []

        if name_only:
            contributors = []
            for contribute in contributes:  # pylint: disable=not-an-iterable
                if "entity" in contribute:
                    contributors += contribute["entity"]
            return contributors

        if date_only:
            dates = []
            for contribute in contributes:  # pylint: disable=not-an-iterable
                if "date" in contribute and "datetime" in contribute["date"]:
                    dates += [contribute["date"]["datetime"]]
            return dates

        return contributes

    def set_datetime(self, datetime: str) -> None:
        """Set the datetime the learning object was created.

        :param str datetime: The datetime-string in isoformat
        """
        self.record["lifecycle.datetime"] = datetime

    ###############
    #
    # methods for manipulating LOM's `metametadata` (3) category
    #
    ###############

    def append_metametadata_contribute(
        self,
        name: str,
        url: str,
        logo: str,
        role: str,
    ) -> None:
        """Append metametadata contribute."""
        contribute = {
            "role": vocabularify(role),
            "entity": [name],
            "url": url,
            "logo": logo,
        }

        self.deduped_append("metametadata.contribute", contribute)

    ###############
    #
    # methods for manipulating LOM's `technical` (4) category
    #
    ###############

    def append_format(self, mimetype: str) -> None:
        """Append format."""
        self.deduped_append("technical.format", mimetype)

    def get_formats(self) -> list:
        """Get formats."""
        try:
            formats = self.record["technical.format"]
        except KeyError:
            return []

        if len(formats) > 0:
            return formats

        return []

    def set_size(self, size: str | int) -> None:
        """Set size.

        :param str|int size: size in bytes (octets)
        """
        self.record["technical.size"] = str(size)

    def set_thumbnail(self, value: dict) -> None:
        """Set thumbnail."""
        self.record["technical.thumbnail"] = value

    def set_duration(self, value: str, language: str) -> None:
        """Set duration."""
        self.record["technical.duration"] = {
            "description": langstringify(value, lang=language),
        }

    def set_location(self, value: str) -> None:
        """Set location."""
        self.record["technical.location"] = {"type": "URI", "#text": value}

    ###############
    #
    # methods for manipulating LOM's `educational` (5) category
    #
    ###############

    def append_learningresourcetype(self, learningresourcetype: str) -> None:
        """Append learning resource type.

        :param str learningresourcetype: Either
            - a URL within the vocabulary `https://w3id.org/kim/hcrt/scheme`
            - a suffix such that `https://w3id.org/kim/hcrt/{suffix}` is such a URL
        """
        # if the full url was passed, remove base_url from it
        base_url = "https://w3id.org/kim/hcrt/"
        learningresourcetype = learningresourcetype.removeprefix(base_url)

        labels = self.learningresourcetype_labels[learningresourcetype]
        entry = [langstringify(label, lang=lang) for lang, label in labels.items()]
        learningresourcetype_dict = {
            "source": langstringify("https://w3id.org/kim/hcrt/scheme"),
            "id": f"https://w3id.org/kim/hcrt/{learningresourcetype}",
            "entry": entry,
        }
        self.deduped_append(
            "educational.learningresourcetype",
            learningresourcetype_dict,
        )

    def get_learning_resource_type(self, *, text_only: bool = False) -> str:
        """Get learning resource type."""
        try:
            entry = self.record["educational.learningresourcetype.0.entry"]
        except KeyError:
            return ""

        if text_only:
            return get_text(entry)

        return entry

    def append_context(self, context: str) -> None:
        """Append context.

        :param str context: One of the values LOM recommends for `educational.context`
        """
        self.deduped_append("educational.context", vocabularify(context))

    def append_educational_description(
        self,
        description: str,
        language_code: str,
    ) -> None:
        """Append educational description."""
        self.deduped_append(
            "educational.description",
            langstringify(description, lang=language_code),
        )

    def set_typical_learning_time(
        self,
        value: str,
        description: str | None = None,
    ) -> None:
        """Set typical learning time."""
        self.record["educational.typicallearningtime"] = {
            "duration": {
                "datetime": value,
                "description": description,
            },
        }

    ###############
    #
    # methods for manipulating LOM's `rights` (6) category
    #
    ###############

    def set_rights_url(self, url: str) -> None:
        """Set rights url.

        :param str url: The url of the copyright license
                        (e.g. "https://creativecommons.org/licenses/by/4.0/")
        """
        url = standardize_url(url)
        lang = "x-t-cc-url" if url.startswith("https://creativecommons.org/") else None
        self.record["rights"] = {
            "copyrightandotherrestrictions": vocabularify("yes"),
            "url": url,
            "description": langstringify(url, lang=lang),
        }

    def get_rights(self, *, url_only: bool = False) -> dict | str:
        """Get rights."""
        if "rights" not in self.record:
            return "" if url_only else {}

        if url_only:
            try:
                return self.record["rights.url"]
            except KeyError:
                return ""

        return self.record["rights"]

    ###############
    #
    # methods for manipulating LOM's `relation` (7) category
    #
    ###############

    def append_relation(self, pid: str, kind: str) -> None:
        """Append relation of kind `kind` with entry `pid`.

        `kind` is a kind, as in LOMv1.0's `relation`-group.
        `pid` is entry, as in LOMv1.0's `relation.resource.identifier` category.
        """
        resource = {"identifier": [catalogify(pid, catalog="repo-pid")]}
        relation = {"kind": vocabularify(kind), "resource": resource}
        self.deduped_append("relation", relation)

    def get_relations(self, *, text_only: bool = False) -> list:
        """Get relations."""
        if "relation" not in self.record:
            return []

        relations = []

        for relation in self.record["relation"]:  # pylint: disable=not-an-iterable
            if "resource" in relation and "description" in relation["resource"]:
                if text_only:
                    relations += [get_text(relation["resource"]["description"][0])]
                else:
                    relations += relation

        return relations

    ###############
    #
    # methods for manipulating LOM's `classification` (9) category
    #
    ###############

    def get_oefos_classification(self) -> dict:
        """Get the classification that holds OEFOS, create it if it didn't exist."""
        # oefos are part of the unique `classification` whose `purpose` is "discipline"
        # try to find that classification, otherwise create it
        for classification in self.record.get("classification", []):
            purpose = classification["purpose"]["value"]["langstring"]["#text"]
            if purpose == "discipline":
                return (oefos_classification := classification)

        # couldn't find; create oefos-classification-dict
        oefos_classification = {
            "purpose": vocabularify("discipline"),
            "taxonpath": [],
        }
        self.record["classification.[]"] = oefos_classification
        return oefos_classification

    def create_oefos_taxonpath(
        self,
        oefos_id: str | int,
        language_code: str = "de",
    ) -> dict:
        """Create the full OEFOS taxon-path that ends in `oefos_id`.

        Whenever assigning a classification, LOM requires the full taxonomic path.
        e.g. instead of the single classification `207413 (Surveying)`,
        the whole taxonomic path to it is required too, namely the full path
          `2 (TECHNICAL SCIENCES)`,
          `207 (Environmental Engineering, Applied Geosciences)`,
          `2074 (Geodesy, Surveying)`, and
          `207413 (Surveying)`
        is what's required.
        """
        oefos_id = str(oefos_id)
        oefosdict = self.oefosdict_by_language[language_code]
        taxon_ids = [
            oefos_id[:key]
            for key in range(len(oefos_id) + 1)
            if oefos_id[:key] in oefosdict
        ]
        taxons = []
        for taxon_id in taxon_ids:
            taxon = {
                "id": f"https://w3id.org/oerbase/vocabs/oefos2012/{taxon_id}",
                "entry": langstringify(oefosdict[taxon_id], lang=None),
            }
            taxons.append(taxon)
        return {
            "source": langstringify("https://w3id.org/oerbase/vocabs/oefos2012"),
            "taxon": taxons,
        }

    def append_oefos_id(
        self,
        oefos_id: str | int,
        language_code: str = "de",
    ) -> None:
        """Append a taxonpath corresponding to `oefos_id` to the oefos-classification.

        (The oefos-classification is the unique `classification` whose `purpose`
        is "discipline".)
        """
        taxonpaths = self.get_oefos_classification()["taxonpath"]
        new_taxonpath = self.create_oefos_taxonpath(oefos_id, language_code)

        # if a more comprehensive taxonpath already exists, don't add this one
        for old_taxonpath in taxonpaths:
            old_taxons = old_taxonpath["taxon"]
            new_taxons = new_taxonpath["taxon"]
            if all(taxon in old_taxons for taxon in new_taxons):
                # found previously existing taxonpath which holds a superset of
                # new taxons
                return

        # delete less comprehensive taxonpaths (if any)
        less_comprehensive_idxs = []
        for idx, old_taxonpath in enumerate(taxonpaths):
            old_taxons = old_taxonpath["taxon"]
            new_taxons = new_taxonpath["taxon"]
            if all(taxon in new_taxons for taxon in old_taxons):
                # found previously existing taxonpath which holds a subset of new taxons
                less_comprehensive_idxs.append(idx)
        for idx in sorted(less_comprehensive_idxs, reverse=True):
            del taxonpaths[idx]

        # append
        if new_taxonpath not in taxonpaths:
            taxonpaths.append(new_taxonpath)


class LOMRecordData(dict):
    """LOM record data."""

    def __init__(
        self,
        resource_type: str | None = None,
        pids: dict | None = None,
        metadata: dict | LOMMetadata = None,
        **kwargs: dict,
    ) -> None:
        """Construct."""
        self.update(**kwargs)
        self.resource_type = resource_type
        self.pids = pids or {}
        self.metadata = (
            metadata
            if isinstance(metadata, LOMMetadata)
            else LOMMetadata(metadata, overwritable=True)
        )

    @property
    def json(self) -> dict:
        """Json."""
        return {
            "pids": self.pids,
            "metadata": self.metadata.json,
            "resource_type": self.resource_type,
            **self,
        }

    @classmethod
    def create(
        cls,
        resource_type: str,
        metadata: dict | None = None,
        access: str = "public",
        pids: dict | None = None,
    ) -> "LOMRecordData":
        """Create `cls` with a json that is compatible with invenio-databases.

        :param str resource_type: One of `current_app.config["LOM_RESOURCE_TYPES"]`
        :param dict metadata: The metadata to be wrapped
        :param str access: One of "public", "restricted"
        :param dict pids: For adding external pids
        """
        files_enabled = resource_type in ["file", "upload"]
        access_dict = {
            "embargo": {},
            "files": access,
            "record": access,
        }
        return cls(
            resource_type=resource_type,
            pids=pids or {},
            metadata=metadata or {},
            access=access_dict,
            files={"enabled": files_enabled},
        )

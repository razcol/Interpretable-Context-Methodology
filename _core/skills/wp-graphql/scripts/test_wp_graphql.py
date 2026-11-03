#!/usr/bin/env python3
"""Fixture checks for the WordPress GraphQL commands. No live endpoint."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("wp_graphql.py")
    spec = importlib.util.spec_from_file_location("wp_graphql", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wp = load_module()


def field(name, named, gql=None, acf=None, choices=None):
    return {
        "name": name,
        "gqlType": gql or named,
        "named": named,
        "acfType": acf,
        "choices": choices or [],
    }


def obj(name, fields, kind="OBJECT", possible=None, interfaces=None, enum_values=None):
    return {
        "name": name,
        "kind": kind,
        "possibleTypes": possible or [],
        "interfaces": interfaces or [],
        "enumValues": enum_values or [],
        "fields": fields,
    }


def schema():
    hero = "FieldsFlexibleHeroLayout"
    en_hero = "EnFieldsEnFlexibleHeroLayout"
    return {
        "MediaItem": obj("MediaItem", [field("mediaItemUrl", "String"), dict(field("mediaItemId", "Int"), deprecated=True)]),
        "AcfMediaItemConnectionEdge": obj(
            "AcfMediaItemConnectionEdge",
            [field("node", "MediaItem"), field("cursor", "String")],
        ),
        "ModelHeroBannerImageFields": obj(
            "ModelHeroBannerImageFields",
            [field("desktop", "AcfMediaItemConnectionEdge"), field("mobile", "AcfMediaItemConnectionEdge")],
        ),
        hero: obj(hero, [field("image", "AcfMediaItemConnectionEdge"), field("imageFields", "ModelHeroBannerImageFields")]),
        en_hero: obj(en_hero, [field("title", "String")]),
        "FieldsFlexible_Layout": obj("FieldsFlexible_Layout", [], kind="UNION", possible=[hero, "FieldsFlexibleBannerLayout"]),
        "FieldsFlexibleBannerLayout": obj("FieldsFlexibleBannerLayout", [field("title", "String")]),
        "EnFieldsEnFlexible_Layout": obj("EnFieldsEnFlexible_Layout", [], kind="UNION", possible=[en_hero, "EnFieldsEnFlexibleBannerLayout"]),
        "EnFieldsEnFlexibleBannerLayout": obj("EnFieldsEnFlexibleBannerLayout", [field("title", "String")]),
        "FieldsGroup": obj("FieldsGroup", [field("flexible", "FieldsFlexible_Layout")]),
        "EnFieldsGroup": obj("EnFieldsGroup", [field("enFlexible", "EnFieldsEnFlexible_Layout")]),
        "Page": obj("Page", [field("fields", "FieldsGroup"), field("enFields", "EnFieldsGroup")]),
        "Comment": obj("Comment", [field("fields", "FieldsGroup")]),
        "SiteSettings": obj("SiteSettings", [field("generalSiteFields", "GeneralSiteFields")], interfaces=["AcfOptionsPage"]),
        "GeneralSiteFields": obj("GeneralSiteFields", [field("footerContactText", "String")]),
        "RootQuery": obj("RootQuery", [field("siteSettings", "SiteSettings"), field("carsBoardSettings", "CarsBoardFields")]),
        "CarsBoardFields": obj("CarsBoardFields", [field("minPrice", "Float")]),
        "Template_ContactUs": obj("Template_ContactUs", [field("contactUsTemplateFields", "ContactUsTemplateFields")]),
        "ContactUsTemplateFields": obj("ContactUsTemplateFields", [field("title", "String")]),
        "ButtonFields": obj("ButtonFields", [field("variant", "String", acf="select")]),
        "ActionTypeEnum": obj("ActionTypeEnum", [], kind="ENUM", enum_values=["link", "video"]),
        "WithChoices": obj("WithChoices", [field("actionType", "ActionTypeEnum", acf="select")]),
        "Described": obj("Described", [field("variant", "String", acf="select", choices=["primary", "ghost"])]),
    }


class CommandTests(unittest.TestCase):
    def test_media_item_summary_does_not_list_core_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "app" / "components"
            folder.mkdir(parents=True)
            path = folder / "MediaItem.gql"
            path.write_text("fragment MediaItem on MediaItem { node { mediaItemUrl } mediaItemId }\n")
            result = wp.command_check_fragment(schema(), False, root, path)
        self.assertTrue(any("node" in line for line in result["summary"]))
        self.assertFalse(any("ancestors" in line for line in result["summary"]))

    def test_media_node_on_media_item_is_missing_and_media_item_id_is_not(self):
        fragments = {
            "MediaItem": {
                "name": "MediaItem",
                "on": "MediaItem",
                "selection": wp.parse_document(
                    "fragment MediaItem on MediaItem { node { mediaItemUrl } mediaItemId }"
                )[0]["selection"],
            }
        }
        report = wp.fragment_report(schema(), fragments, fragments["MediaItem"])
        self.assertIn("node", report["missingOnSchema"])
        self.assertNotIn("mediaItemId", report["missingOnSchema"])

    def test_media_spread_on_connection_edge_is_a_shape_mismatch(self):
        source = """
        fragment Hero on FieldsFlexibleHeroLayout {
          image { ...MediaItem }
        }
        """
        fragment = wp.parse_document(source)[0]
        fragments = {
            "MediaItem": wp.parse_document("fragment MediaItem on MediaItem { mediaItemUrl }")[0],
            "Hero": fragment,
        }
        report = wp.fragment_report(schema(), fragments, fragment)
        self.assertEqual(report["missingOnSchema"], [])
        self.assertEqual(report["shapeMismatches"][0]["schemaShape"], "mediaEdge")
        self.assertEqual(report["shapeMismatches"][0]["path"], "image")

    def test_patterns_keep_both_unions_options_and_templates(self):
        result = wp.command_patterns(schema(), False)
        unions = {item["language"]: item for item in result["flexible"]["unions"]}
        self.assertIn("he", unions)
        self.assertIn("en", unions)
        self.assertIn("Page.fields.flexible", unions["he"]["paths"])
        self.assertIn("Page.enFields.enFlexible", unions["en"]["paths"])
        self.assertEqual(
            result["flexibleField"],
            {
                "parentType": "FieldsGroup",
                "parentField": "fields",
                "field": "flexible",
                "gqlType": "FieldsFlexible_Layout",
                "named": "FieldsFlexible_Layout",
            },
        )
        self.assertNotIn("Comment.fields.flexible", result["flexible"]["paths"])
        self.assertTrue(any(item["field"] == "siteSettings" for item in result["options"]))
        self.assertTrue(any(item["type"] == "Template_ContactUs" for item in result["templates"]))
        joined = " ".join(result["summary"])
        self.assertNotIn("Comment", joined)

    def test_patterns_reports_flexible_field_without_a_two_member_union(self):
        layout = "FieldsFlexibleOnlyLayout"
        data = {
            layout: obj(layout, [field("title", "String")]),
            "FieldsFlexible_Layout": obj("FieldsFlexible_Layout", [], kind="UNION", possible=[layout]),
            "Fields": obj(
                "Fields",
                [field("flexible", "FieldsFlexible_Layout", gql="[FieldsFlexible_Layout]", acf="flexible_content")],
            ),
            "Page": obj("Page", [field("fields", "Fields")]),
        }
        result = wp.command_patterns(data, False)
        self.assertIsNone(result["flexible"])
        self.assertEqual(
            result["flexibleField"],
            {
                "parentType": "Fields",
                "parentField": "fields",
                "field": "flexible",
                "gqlType": "[FieldsFlexible_Layout]",
                "named": "FieldsFlexible_Layout",
            },
        )
        joined = " ".join(result["summary"])
        self.assertIn("Fields.flexible", joined)
        self.assertIn("no layout union", joined)

    def test_patterns_counts_interface_layouts(self):
        hero = "FieldsFlexibleHeroLayout"
        banner = "FieldsFlexibleBannerLayout"
        data = {
            hero: obj(hero, [field("image", "AcfMediaItemConnectionEdge")]),
            banner: obj(banner, [field("title", "String")]),
            "FieldsFlexible_Layout": obj(
                "FieldsFlexible_Layout",
                [field("fieldGroupName", "String")],
                kind="INTERFACE",
                possible=[hero, banner],
            ),
            "Fields": obj(
                "Fields",
                [field("flexible", "FieldsFlexible_Layout", gql="[FieldsFlexible_Layout]", acf="flexible_content")],
            ),
            "Page": obj("Page", [field("fields", "Fields")]),
            "AcfFieldGroup": obj(
                "AcfFieldGroup",
                [],
                kind="INTERFACE",
                possible=[hero, banner, "ImageGrid"],
            ),
            "ImageGrid": obj("ImageGrid", []),
        }
        result = wp.command_patterns(data, False)
        self.assertEqual(result["flexible"]["union"], "FieldsFlexible_Layout")
        self.assertEqual([item["union"] for item in result["flexible"]["unions"]], ["FieldsFlexible_Layout"])
        self.assertEqual(result["flexible"]["unions"][0]["layouts"], 2)
        self.assertEqual(
            {item["section"] for item in result["layouts"]},
            {"Hero", "Banner"},
        )
        self.assertIsNotNone(result["flexibleField"])

    def test_type_resolves_an_options_root_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = wp.command_type(schema(), False, Path(tmp), "carsBoardSettings")
        self.assertEqual(result["type"], "CarsBoardFields")
        self.assertEqual(result["rootField"], "RootQuery.carsBoardSettings")
        self.assertTrue(any("minPrice" in line and "clone" not in line for line in result["summary"]))

    def test_section_summary_names_a_cloned_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = wp.command_section(schema(), False, Path(tmp), "Hero")
        live = next(line for line in result["summary"] if line.startswith("Live fields:"))
        self.assertIn("image (mediaItem on a connection edge)", live)
        self.assertIn("clone of ModelHeroBannerImageFields", live)

    def test_choices_from_enum_description_and_missing(self):
        enum_result = wp.command_choices(schema(), False, "WithChoices.actionType")
        self.assertEqual(enum_result["choices"], ["link", "video"])
        described = wp.command_choices(schema(), False, "Described.variant")
        self.assertEqual(described["choices"], ["primary", "ghost"])
        with self.assertRaises(wp.ChoicesUnavailable) as caught:
            wp.command_choices(schema(), False, "ButtonFields.variant")
        self.assertEqual(caught.exception.code, "CHOICES_UNAVAILABLE")
        self.assertIn("Stop", caught.exception.message)

    def test_check_repo_reports_only_the_bad_fragment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = root / "app" / "components" / "Sections" / "Hero" 
            bad = root / "code" / "app" / "components" / "Sections" / "Bad"
            good.mkdir(parents=True)
            bad.mkdir(parents=True)
            (good / "Hero.gql").write_text(
                "fragment Hero on FieldsFlexibleHeroLayout { image { node { mediaItemUrl } } }\n"
            )
            (bad / "Bad.gql").write_text(
                "fragment Bad on FieldsFlexibleHeroLayout { image { ...MediaItem } }\n"
            )
            (root / "app" / "components" / "MediaItem.gql").parent.mkdir(parents=True, exist_ok=True)
            (root / "app" / "components" / "MediaItem.gql").write_text(
                "fragment MediaItem on MediaItem { mediaItemUrl mediaItemId }\n"
            )
            result = wp.command_check_repo(schema(), False, root)
        names = [item["name"] for item in result["problems"]]
        self.assertIn("Bad", names)
        self.assertNotIn("Hero", names)
        self.assertNotIn("MediaItem", names)
        self.assertEqual(result["checked"], 3)

    def test_description_parser_keeps_enum_values_and_choices(self):
        payload = {
            "data": {
                "__schema": {
                    "types": [
                        {
                            "name": "ToneEnum",
                            "kind": "ENUM",
                            "description": None,
                            "possibleTypes": [],
                            "interfaces": [],
                            "enumValues": [{"name": "dark"}, {"name": "light"}],
                            "fields": [],
                        },
                        {
                            "name": "ButtonFields",
                            "kind": "OBJECT",
                            "description": None,
                            "possibleTypes": [],
                            "interfaces": [],
                            "enumValues": [],
                            "fields": [
                                {
                                    "name": "variant",
                                    "description": 'Field Type: select. choices: ["primary", "ghost"]',
                                    "type": {"kind": "SCALAR", "name": "String", "ofType": None},
                                }
                            ],
                        }
                    ]
                }
            }
        }
        compact = wp.compact_schema(payload)
        self.assertEqual(compact["ToneEnum"]["enumValues"], ["dark", "light"])
        self.assertEqual(compact["ButtonFields"]["fields"][0]["acfType"], "select")
        self.assertEqual(compact["ButtonFields"]["fields"][0]["choices"], ["primary", "ghost"])
    def test_null_compare_says_nothing_compared(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "Ghost.gql"
            path.write_text("fragment Ghost on FieldsFlexibleGhostLayout { title }\n")
            result = wp.command_check_fragment(schema(), False, root, path)
        joined = " ".join(result["summary"])
        self.assertIn("No type was compared", joined)
        self.assertNotIn("Every fragment field exists", joined)
        self.assertFalse(result["fragment"]["compared"])

    def test_check_repo_lists_not_compared(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "app" / "components" / "Sections" / "Ghost"
            folder.mkdir(parents=True)
            (folder / "Ghost.gql").write_text("fragment Ghost on FieldsFlexibleGhostLayout { title }\n")
            result = wp.command_check_repo(schema(), False, root)
        self.assertEqual([item["name"] for item in result["notCompared"]], ["Ghost"])
        self.assertEqual(result["problems"], [])
        self.assertNotIn("Every checked fragment matches.", result["summary"])

    def test_section_layout_not_on_flexible(self):
        data = schema()
        data["FieldsFlexibleLoneLayout"] = obj("FieldsFlexibleLoneLayout", [field("title", "String")])
        with tempfile.TemporaryDirectory() as tmp:
            result = wp.command_section(data, False, Path(tmp), "Lone")
        self.assertIn("is not on the flexible layout type", result["summary"][0])
        self.assertFalse(result["onFlexibleUnion"])

    def test_type_layout_not_on_flexible(self):
        data = schema()
        data["FieldsFlexibleLoneLayout"] = obj("FieldsFlexibleLoneLayout", [field("title", "String")])
        with tempfile.TemporaryDirectory() as tmp:
            result = wp.command_type(data, False, Path(tmp), "FieldsFlexibleLoneLayout")
        self.assertEqual(result["layoutType"], "FieldsFlexibleLoneLayout")
        self.assertIsNone(result["groupType"])
        self.assertIn("is not on the flexible layout type", result["summary"][0])
    def media_fragments(self):
        return {
            "MediaItem": wp.parse_document(
                "fragment MediaItem on MediaItem { node { mediaItemUrl mediaItemId } }"
            )[0],
            "ResponsiveMediaItem": wp.parse_document(
                "fragment ResponsiveMediaItem on TYPE { desktop { ...MediaItem } mobile { ...MediaItem } }"
            )[0],
        }

    def test_node_wrapped_spread_on_edge_matches(self):
        fragments = self.media_fragments()
        fragment = wp.parse_document("fragment Hero on FieldsFlexibleHeroLayout { image { ...MediaItem } }")[0]
        fragments["Hero"] = fragment
        report = wp.fragment_report(schema(), fragments, fragment)
        self.assertEqual(report["shapeMismatches"], [])
        self.assertEqual(report["missingOnSchema"], [])

    def test_flat_spread_on_edge_still_mismatches(self):
        fragments = {"MediaItem": wp.parse_document("fragment MediaItem on MediaItem { mediaItemUrl }")[0]}
        fragment = wp.parse_document("fragment Hero on FieldsFlexibleHeroLayout { image { ...MediaItem } }")[0]
        fragments["Hero"] = fragment
        report = wp.fragment_report(schema(), fragments, fragment)
        self.assertEqual(report["shapeMismatches"][0]["schemaShape"], "mediaEdge")

    def test_background_fields_nested_spreads_match(self):
        fragments = self.media_fragments()
        fragment = wp.parse_document(
            "fragment Hero on FieldsFlexibleHeroLayout { imageFields { ...ResponsiveMediaItem } }"
        )[0]
        fragments["Hero"] = fragment
        report = wp.fragment_report(schema(), fragments, fragment)
        self.assertEqual(report["shapeMismatches"], [])
        self.assertEqual(report["missingOnSchema"], [])

    def test_gallery_connection_still_reported(self):
        data = schema()
        data["AcfMediaItemConnection"] = obj(
            "AcfMediaItemConnection",
            [field("nodes", "MediaItem", gql="[MediaItem]"), field("edges", "AcfMediaItemConnectionEdge", gql="[AcfMediaItemConnectionEdge]")],
        )
        data["FieldsFlexibleHeroLayout"]["fields"].append(field("gallery", "AcfMediaItemConnection"))
        fragments = self.media_fragments()
        fragment = wp.parse_document("fragment Hero on FieldsFlexibleHeroLayout { gallery { ...MediaItem } }")[0]
        fragments["Hero"] = fragment
        report = wp.fragment_report(data, fragments, fragment)
        self.assertEqual(report["shapeMismatches"][0]["schemaType"], "AcfMediaItemConnection")
        self.assertIn("nodes", " ".join(wp.mismatch_lines(report["shapeMismatches"])))

    def test_double_node_reported(self):
        fragments = self.media_fragments()
        fragment = wp.parse_document(
            "fragment Hero on FieldsFlexibleHeroLayout { image { node { ...MediaItem } } }"
        )[0]
        fragments["Hero"] = fragment
        report = wp.fragment_report(schema(), fragments, fragment)
        self.assertTrue(report["missingOnSchema"] or report["shapeMismatches"])

    def test_fragment_cycle_does_not_recurse(self):
        fragments = {
            "Loop": wp.parse_document("fragment Loop on TYPE { title ...Loop }")[0],
        }
        fragment = wp.parse_document("fragment Banner on FieldsFlexibleBannerLayout { ...Loop }")[0]
        fragments["Banner"] = fragment
        report = wp.fragment_report(schema(), fragments, fragment)
        self.assertEqual(report["missingOnSchema"], [])

    def test_standalone_node_media_fragment_is_compared_on_the_edge(self):
        fragments = self.media_fragments()
        report = wp.fragment_report(schema(), fragments, fragments["MediaItem"])
        self.assertEqual(report["comparedTo"], "AcfMediaItemConnectionEdge")
        self.assertEqual(report["missingOnSchema"], [])
    def test_inline_fragment_compares_on_its_type(self):
        data = schema()
        data["Model"] = obj("Model", [field("modelListCodes", "String")])
        data["ContentNode"] = obj("ContentNode", [field("id", "ID")], kind="INTERFACE", possible=["Model"])
        data["FieldsFlexibleBannerLayout"]["fields"].append(field("model", "ContentNode"))
        fragment = wp.parse_document(
            "fragment Banner on FieldsFlexibleBannerLayout { model { id ... on Model { modelListCodes } } }"
        )[0]
        report = wp.fragment_report(data, {"Banner": fragment}, fragment)
        self.assertEqual(report["missingOnSchema"], [])

    def test_flexible_target_kept_with_stray_member(self):
        hero = "FieldsFlexibleHeroLayout"
        banner = "FieldsFlexibleBannerLayout"
        data = {
            hero: obj(hero, [field("title", "String")]),
            banner: obj(banner, [field("title", "String")]),
            "Stray": obj("Stray", []),
            "FieldsFlexible_Layout": obj("FieldsFlexible_Layout", [], kind="INTERFACE", possible=[hero, banner, "Stray"]),
            "Wider": obj("Wider", [], kind="INTERFACE", possible=[hero, banner, "Stray"]),
            "Fields": obj("Fields", [field("flexible", "FieldsFlexible_Layout", gql="[FieldsFlexible_Layout]", acf="flexible_content")]),
            "Page": obj("Page", [field("fields", "Fields")]),
        }
        found = wp.find_flexibles(data)
        self.assertEqual([entry["union"] for entry in found], ["FieldsFlexible_Layout"])
        self.assertEqual(sorted(found[0]["members"]), sorted([hero, banner]))

    def test_compact_schema_marks_deprecated(self):
        payload = {"data": {"__schema": {"types": [{
            "name": "MediaItem", "kind": "OBJECT", "description": None, "possibleTypes": [], "interfaces": [], "enumValues": [],
            "fields": [
                {"name": "mediaItemId", "description": None, "isDeprecated": True, "type": {"kind": "SCALAR", "name": "Int", "ofType": None}},
                {"name": "mediaItemUrl", "description": None, "isDeprecated": False, "type": {"kind": "SCALAR", "name": "String", "ofType": None}},
            ],
        }]}}}
        compact = wp.compact_schema(payload)
        flags = {item["name"]: item["deprecated"] for item in compact["MediaItem"]["fields"]}
        self.assertEqual(flags, {"mediaItemId": True, "mediaItemUrl": False})

    def test_deprecated_selected_not_missing(self):
        data = schema()
        data["FieldsFlexibleBannerLayout"]["fields"].append(dict(field("oldTitle", "String"), deprecated=True))
        fragment = wp.parse_document("fragment Banner on FieldsFlexibleBannerLayout { title oldTitle }")[0]
        report = wp.fragment_report(data, {"Banner": fragment}, fragment)
        self.assertEqual(report["missingOnSchema"], [])
        self.assertEqual(report["deprecatedSelected"], ["oldTitle"])
        self.assertNotIn("oldTitle", wp.omitted_fields(data, "FieldsFlexibleBannerLayout", [], {}))
        self.assertNotIn("oldTitle", [node["name"] for node in wp.field_tree(data, "FieldsFlexibleBannerLayout", 2, set())])

    def test_cache_version_3_invalidates_v2(self):
        import time
        self.assertEqual(wp.CACHE_VERSION, 3)
        self.assertFalse(wp.cache_is_fresh({"version": 2, "fetchedAt": int(time.time()), "schema": {}}))
        self.assertTrue(wp.cache_is_fresh({"version": 3, "fetchedAt": int(time.time()), "schema": {}}))
    def diff_schema(self):
        data = schema()
        data["FieldsFlexibleGridLayout"] = obj(
            "FieldsFlexibleGridLayout",
            [
                field("fieldGroupName", "String"),
                field("intro", "String", acf="text"),
                field("grid", "GridItem", gql="[GridItem]", acf="repeater"),
            ],
        )
        data["GridItem"] = obj("GridItem", [field("text", "String", acf="text"), field("image", "AcfMediaItemConnectionEdge")])
        data["FieldsFlexible_Layout"]["possibleTypes"].append("FieldsFlexibleGridLayout")
        return data

    def plan(self, fields):
        return {"schemaVersion": 1, "folder": "Grid", "fields": fields}

    def matching_fields(self):
        return [
            {"name": "intro", "acfType": "text"},
            {"name": "grid", "acfType": "repeater", "children": [
                {"name": "text", "acfType": "text"},
                {"name": "image", "shape": "mediaItem"},
            ]},
        ]

    def test_diff_group_identical_plan_has_no_differences(self):
        result = wp.command_diff_group(self.diff_schema(), False, "Grid", self.plan(self.matching_fields()))
        self.assertTrue(result["matches"])
        for key in ("added", "removed", "typeChanged", "cardinalityChanged"):
            self.assertEqual(result[key], [])
        self.assertIn("seamless clone", result["unknown"])

    def test_diff_group_added_and_removed(self):
        fields = [{"name": "header", "acfType": "group"}, {"name": "intro", "acfType": "text"}]
        result = wp.command_diff_group(self.diff_schema(), False, "Grid", self.plan(fields))
        self.assertEqual(result["added"], ["header"])
        self.assertEqual(result["removed"], ["grid"])
        self.assertFalse(result["matches"])

    def test_diff_group_type_changed(self):
        fields = self.matching_fields()
        fields[1]["children"][1] = {"name": "image", "shape": "responsiveMedia"}
        result = wp.command_diff_group(self.diff_schema(), False, "Grid", self.plan(fields))
        self.assertEqual([item["path"] for item in result["typeChanged"]], ["grid.image"])

    def test_diff_group_cardinality_changed(self):
        fields = self.matching_fields()
        fields[1] = {"name": "grid", "acfType": "group", "list": False, "children": fields[1]["children"]}
        result = wp.command_diff_group(self.diff_schema(), False, "Grid", self.plan(fields))
        self.assertEqual(result["cardinalityChanged"][0]["path"], "grid")
        self.assertEqual(result["cardinalityChanged"][0]["live"], "list")

    def test_diff_group_missing_section_adds_everything(self):
        result = wp.command_diff_group(self.diff_schema(), False, "Nothing", self.plan(self.matching_fields()))
        self.assertEqual(result["added"], ["intro", "grid"])
        self.assertFalse(result["matches"])

    def test_plan_validation_rejects_bad_plans(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            cases = [
                {"schemaVersion": 2, "fields": []},
                {"schemaVersion": 1, "fields": [{"name": "bad name"}]},
                {"schemaVersion": 1, "fields": [], "extra": 1},
                {"schemaVersion": 1, "fields": [{"name": "a", "children": [{"name": "b", "children": [{"name": "c", "children": [{"name": "d", "children": [{"name": "e", "children": [{"name": "f", "children": [{"name": "g"}]}]}]}]}]}]}]},
            ]
            for case in cases:
                path.write_text(__import__("json").dumps(case))
                with self.assertRaises(wp.UsageError):
                    wp.load_plan(path)
            path.write_text("not json")
            with self.assertRaises(wp.UsageError):
                wp.load_plan(path)
            path.write_text(__import__("json").dumps(self.plan(self.matching_fields())))
            self.assertEqual(wp.load_plan(path)["schemaVersion"], 1)


if __name__ == "__main__":
    unittest.main()

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
        "MediaItem": obj("MediaItem", [field("mediaItemUrl", "String")]),
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


if __name__ == "__main__":
    unittest.main()

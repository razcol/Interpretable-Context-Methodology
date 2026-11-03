#!/usr/bin/env python3
"""Fixture checks for probe_repo.py and check_section.py. No real repo, no network."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_section  # noqa: E402
import probe_repo  # noqa: E402

TEMPLATE = """const index = (folder) => `import ${folder} from './Server${folder}';`;
const serverComponent = (folder) => `import 'server-only';`;
const component = (folder) => `'use client';`;
const styled = (folder) => `const S = styled.div\\`\\${({ theme }) => theme.mixins.layout};\\``;
const fragment = (folder) => `fragment ${folder} on FieldsFlexible${folder}Layout { ...Layout }`;
module.exports = { index, serverComponent, component, styled, fragment };
"""

CORE = """const config = {
  sections: {
    globalFragments: importAll([
      require.context('fragments/global', true, /\\.gql$/),
      require.context('@/UIComponents', true, /\\.gql$/),
      require.context('@/Sections', true, /\\.gql$/)
    ])
  }
};
"""


def write(path: Path, text: str, eol: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\n", eol).encode())


def ora_like(root: Path, next_installed: str = "16.4.3") -> Path:
    app = root / "code"
    write(app / "package.json", json.dumps({
        "scripts": {"dev": "npm run loadenv && next dev", "lint": "next lint"},
        "dependencies": {"next": "16.4.3", "@colmobil/next": "1.0.17"},
    }))
    write(app / "node_modules" / "next" / "package.json", json.dumps({"version": next_installed}))
    write(app / "node_modules" / "@colmobil" / "next" / "package.json", json.dumps({"version": "1.0.17"}))
    write(app / "ccTemplates" / "section.js", TEMPLATE)
    write(app / "app" / "core.config.js", CORE)
    write(app / "app" / "styles" / "theme" / "index.js", """import buttonsMixins from './mixins/buttonsMixins';
const theme = {
  bps: { desktop: `@media (min-width: 1279px)`, mobile: `@media (max-width: 1279px)` },
  mixins: { buttons: buttonsMixins },
  colors: { white: '#fff', black: '#000', primaryBlue: '#1E6679', table: { header: '#b4d0de' }, shade: 'rgba(0, 0, 0, 0.5)' }
};
export default theme;
""")
    write(app / "app" / "styles" / "fonts" / "index.js", """import localFont from 'next/font/local';
export const primary = localFont({ variable: '--f', src: [{ path: './ploni-regular-aaa.woff2', weight: '400' }] });
""")
    write(app / "app" / "styles" / "GlobalStyle.js", "const G = createGlobalStyle`html { direction: rtl; }`;\n")
    write(app / "app" / "hooks" / "useWP.js", "export const useWPMenu = () => null;\n")
    write(app / "app" / "fragments" / "global" / "Button.gql", "fragment Button on TYPE { text }\n")
    write(app / "app" / "fragments" / "global" / "mediaItem.gql", "fragment MediaItem on MediaItem { node { mediaItemUrl } }\n")
    write(app / "app" / "fragments" / "global" / "layout.gql", "fragment Layout on TYPE { marginBottom }\n")
    write(app / "app" / "components" / "UIComponents" / "MediaBackground" / "BackgroundFields.gql", "fragment BackgroundFields on TYPE { type }\n")
    write(app / "app" / "components" / "Layout" / "Breadcrumbs.js", "const list = rootData?.breadcrumbs;\n")
    write(app / ".eslintrc.js", "module.exports = { rules: { 'react/prop-types': 'error' }, parserOptions: { schema: '@colmobil/next/core/validation/eslintSchema.graphql' } };\n")
    good_section(app, "Hero")
    return app


def jaecoo_like(root: Path) -> Path:
    app = root / "code"
    write(app / "package.json", json.dumps({"scripts": {"dev": "next dev -p 8000"}, "dependencies": {"next": "14.2.26", "@colmobil/next": "0.2.47"}}))
    write(app / "ccTemplates" / "section.js", TEMPLATE)
    write(app / "app" / "core.config.js", CORE)
    write(app / "app" / "styles" / "theme" / "index.js", """import colors from './colors';
import mixins from './mixin';
import { bps } from './layout';
const theme = { bps, colors, mixins };
export default theme;
""")
    write(app / "app" / "styles" / "theme" / "colors.js", "const colors = { white: '#fff', red: 'red' };\nexport default colors;\n")
    write(app / "app" / "styles" / "theme" / "mixin.js", "import layout from './mixins/layoutMixins';\nconst mixins = { ...layout, buttons: {} };\nexport default mixins;\n")
    write(app / "app" / "styles" / "theme" / "mixins" / "layoutMixins.js", "const mixins = { shrink: css`a`, layout: css`${({ $layout }) => css`b`}`, media: {} };\nexport default mixins;\n")
    write(app / "app" / "styles" / "theme" / "layout.js", "export const bps = { mobile: `@media (max-width: 1279px)`, desktop: `@media (min-width: 1280px)` };\n")
    write(app / "app" / "styles" / "fonts" / "index.js", "export const jaecoo = localFont({ src: './jaecoo/Rubik-Regular.woff2' });\n")
    write(app / "app" / "fragments" / "global" / "buttonItem.gql", "fragment ButtonItem on TYPE { text }\n")
    write(app / "app" / "fragments" / "global" / "mediaItem.gql", "fragment MediaItem on MediaItem { node { mediaItemUrl } }\n")
    good_section(app, "Hero", eol="\r\n")
    return app


def good_section(app: Path, name: str, eol: str = "\n") -> Path:
    folder = app / "app" / "components" / "Sections" / name
    write(folder / "index.js", f"import {name} from './Server{name}';\nexport default {name};\n", eol)
    write(folder / f"Server{name}.js", f"import 'server-only';\nimport Client{name} from './Client{name}';\nconst Server{name} = (props) => <Client{name} {{...props}} />;\nexport default Server{name};\n", eol)
    write(folder / f"Client{name}.js", f"'use client';\nimport propTypes from 'prop-types';\nconst Client{name} = ({{ order, title }}) => <div id={{order}}>{{title}}</div>;\nClient{name}.propTypes = {{ order: propTypes.string, title: propTypes.string }};\nexport default Client{name};\n", eol)
    write(folder / f"Styled{name}.js", f"import styled from 'styled-components';\nconst Styled{name} = styled.div`\n  width: 100%;\n  font-family: ${{({{ theme }}) => theme.fonts.primary}};\n  ${{({{ theme }}) => theme.bps.mobile}} {{ width: 100%; }}\n`;\nexport default Styled{name};\n", eol)
    write(folder / f"{name}.gql", f"fragment {name} on FieldsFlexible{name}Layout {{\n  title\n  image {{ ...MediaItem }}\n}}\n", eol)
    return folder


def statuses(result: dict) -> dict:
    return {row["id"]: row["status"] for row in result["checks"]}


class ProbeTests(unittest.TestCase):
    def test_ora_like_profile_has_every_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            ora_like(Path(tmp))
            result = probe_repo.probe(Path(tmp))
        profile = result["profile"]
        for key in ("schemaVersion", "appRoot", "next", "runtime", "sectionsDir", "existingSections", "globalFragmentDirs", "fragments",
                    "scaffold", "theme", "eol", "eslint", "lintCommand", "breadcrumbs", "useWP", "pageDirection", "dev", "browser"):
            self.assertIn(key, profile)
        self.assertEqual(profile["schemaVersion"], 1)
        self.assertEqual(profile["fragments"]["button"]["name"], "Button")
        self.assertEqual(profile["fragments"]["mediaItem"]["path"], "app/fragments/global/mediaItem.gql")
        self.assertEqual(profile["fragments"]["backgroundFields"]["name"], "BackgroundFields")
        self.assertIsNone(profile["fragments"]["mediaItemNew"])
        self.assertEqual(profile["theme"]["mixins"], ["buttons"])
        self.assertEqual(profile["theme"]["bps"], ["desktop", "mobile"])
        self.assertEqual(profile["theme"]["colors"]["white"], "#ffffff")
        self.assertEqual(profile["theme"]["colors"]["primaryBlue"], "#1e6679")
        self.assertEqual(profile["theme"]["colors"]["table.header"], "#b4d0de")
        self.assertEqual(profile["theme"]["colors"]["shade"], "#00000080")
        self.assertEqual(profile["theme"]["fonts"], [{"export": "primary", "files": ["ploni-regular-aaa"]}])
        self.assertEqual(profile["scaffold"]["files"], ["{F}.gql", "Server{F}.js", "index.js", "Client{F}.js", "Styled{F}.js"])
        self.assertEqual(profile["globalFragmentDirs"], ["app/fragments/global", "app/components/UIComponents", "app/components/Sections"])
        self.assertEqual(profile["eol"], "lf")
        self.assertEqual(profile["breadcrumbs"], "rootData?.breadcrumbs")
        self.assertTrue(profile["useWP"])
        self.assertEqual(profile["pageDirection"], "rtl")
        self.assertEqual(profile["eslint"]["propTypes"], "error")
        self.assertEqual(profile["lintCommand"], ["npx", "eslint"])
        self.assertEqual(profile["existingSections"], ["Hero"])
        joined = " ".join(result["warnings"])
        self.assertIn("next lint", joined)
        self.assertIn("theme.mixins.layout", joined)

    def test_jaecoo_like_profile_follows_imports_and_spreads(self):
        with tempfile.TemporaryDirectory() as tmp:
            jaecoo_like(Path(tmp))
            result = probe_repo.probe(Path(tmp) / "code")
        profile = result["profile"]
        self.assertEqual(profile["fragments"]["button"]["name"], "ButtonItem")
        self.assertEqual(profile["theme"]["mixins"], ["shrink", "layout", "media", "buttons"])
        self.assertEqual(profile["theme"]["bps"], ["mobile", "desktop"])
        self.assertEqual(profile["theme"]["colors"], {"white": "#ffffff", "red": "#ff0000"})
        self.assertEqual(profile["theme"]["fonts"], [{"export": "jaecoo", "files": ["Rubik-Regular"]}])
        self.assertEqual(profile["eol"], "crlf")
        self.assertEqual(profile["dev"]["port"], 8000)
        self.assertFalse(profile["useWP"])
        self.assertNotIn("theme.mixins.layout", " ".join(result["warnings"]))

    def test_missing_files_are_warnings_and_a_stale_install_warns(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = ora_like(Path(tmp), next_installed="14.2.35")
            (app / "app" / "styles" / "fonts" / "index.js").unlink()
            result = probe_repo.probe(Path(tmp))
        joined = " ".join(result["warnings"])
        self.assertIn("16.4.3 but 14.2.35 is installed", joined)
        self.assertIn("fonts/index.js was not found", joined)
        self.assertEqual(result["profile"]["theme"]["fonts"], [])

    def test_probe_never_starts_a_program(self):
        with tempfile.TemporaryDirectory() as tmp:
            ora_like(Path(tmp))
            with mock.patch.object(subprocess, "run", side_effect=AssertionError("probe ran a program")), \
                    mock.patch.object(subprocess, "Popen", side_effect=AssertionError("probe ran a program")):
                probe_repo.probe(Path(tmp))

    def test_not_a_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(probe_repo.ProbeError):
                probe_repo.probe(Path(tmp))


class CheckTests(unittest.TestCase):
    def check(self, mutate=None, repo=ora_like):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        app = repo(Path(tmp.name))
        folder = app / "app" / "components" / "Sections" / "Hero"
        if mutate:
            mutate(app, folder)
        profile = probe_repo.probe(Path(tmp.name))["profile"]
        return check_section.check_section(profile, "Hero", lint=False), app, folder

    def test_good_section_passes(self):
        result, _, _ = self.check()
        self.assertTrue(result["pass"], result["checks"])
        result, _, _ = self.check(repo=jaecoo_like)
        self.assertTrue(result["pass"], result["checks"])

    def test_each_check_fails_when_it_should(self):
        cases = {
            "files-present": lambda app, f: (f / "StyledHero.js").unlink(),
            "server-only": lambda app, f: write(f / "ServerHero.js", "import Client from './ClientHero';\n"),
            "use-client": lambda app, f: write(f / "ClientHero.js", "import x from 'y';\nconst ClientHero = () => null;\n"),
            "folder-name": lambda app, f: write(f / "Hero.gql", "fragment Banner on FieldsFlexibleBannerLayout { title }\n"),
            "no-assets": lambda app, f: write(f / "assets" / "fill.png", "x"),
            "no-font-literal": lambda app, f: write(f / "StyledHero.js", "const S = styled.div`\n  font-family: 'SimplerPro_V3', sans-serif;\n  ${({ theme }) => theme.bps.mobile} {}\n`;\n"),
            "no-root-direction": lambda app, f: write(f / "StyledHero.js", "const S = styled.div`\n  display: flex;\n  direction: rtl;\n  ${({ theme }) => theme.bps.mobile} {}\n`;\n"),
            "prop-types": lambda app, f: write(f / "ClientHero.js", "'use client';\nconst ClientHero = ({ title }) => <div>{title}</div>;\nexport default ClientHero;\n"),
            "spreads-exist": lambda app, f: write(f / "Hero.gql", "fragment Hero on FieldsFlexibleHeroLayout { image { ...Missing } }\n"),
            "no-hand-media": lambda app, f: write(f / "Hero.gql", "fragment Hero on FieldsFlexibleHeroLayout { image { node { mediaItemUrl } } }\n"),
            "no-page-fields": lambda app, f: write(f / "Hero.gql", "fragment Hero on FieldsFlexibleHeroLayout { title breadcrumbs }\n"),
            "mixins-layout": lambda app, f: write(f / "StyledHero.js", "const S = styled.div`\n  ${({ theme }) => theme.mixins.layout};\n  ${({ theme }) => theme.bps.mobile} {}\n`;\n"),
            "eol": lambda app, f: write(f / "index.js", "import Hero from './ServerHero';\nexport default Hero;\n", "\r\n"),
        }
        for check_id, mutate in cases.items():
            with self.subTest(check_id):
                result, _, _ = self.check(mutate)
                self.assertEqual(statuses(result)[check_id], "fail", result["checks"])
                failing = [row["id"] for row in result["checks"] if row["status"] == "fail"]
                self.assertEqual(failing, [check_id])

    def test_warnings_do_not_fail(self):
        def mutate(app, folder):
            write(folder / "StyledHero.js", "const S = styled.div`\n  color: #1e6679;\n`;\n")
        result, _, _ = self.check(mutate)
        self.assertTrue(result["pass"])
        self.assertEqual(statuses(result)["theme-colors"], "warn")
        self.assertEqual(statuses(result)["bps-present"], "warn")

    def test_root_rtl_with_ltr_rows_passes(self):
        def mutate(app, folder):
            write(folder / "StyledHero.js", "const S = styled.div`\n  direction: rtl;\n  .row { display: flex; direction: ltr; }\n  ${({ theme }) => theme.bps.mobile} {}\n`;\n")
        result, _, _ = self.check(mutate)
        self.assertEqual(statuses(result)["no-root-direction"], "pass")

    def test_staged_field_report_warns(self):
        def mutate(app, folder):
            write(folder / "field-report.md", "# report\n")
            subprocess.run(["git", "init", "-q"], cwd=app, check=True, shell=False)
            subprocess.run(["git", "add", str(folder / "field-report.md")], cwd=app, check=True, shell=False)
        result, _, _ = self.check(mutate)
        self.assertEqual(statuses(result)["field-report-staged"], "warn")
        self.assertTrue(result["pass"])

    def test_unstaged_field_report_is_allowed(self):
        result, _, _ = self.check(lambda app, folder: write(folder / "field-report.md", "# report\n"))
        self.assertNotIn("field-report-staged", statuses(result))
        self.assertEqual(statuses(result)["no-assets"], "pass")


if __name__ == "__main__":
    unittest.main()

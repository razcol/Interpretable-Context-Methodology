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


HOVER_OPEN = "const S = styled.div`\n  .card:hover .text {\n    grid-template-rows: 1fr;\n    opacity: 1;\n  }\n`;\n"


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
export const breakPoints = { mobile: 1279, smallerMobile: 320, laptop: 900 };
const theme = {
  bps: {
    desktop: `@media (min-width: ${breakPoints.mobile}px)`,
    mobile: `@media (max-width: ${breakPoints.mobile}px)`,
    smallerMobile: `@media (max-width:  ${breakPoints.smallerMobile}px)`,
    mobilePixels: breakPoints.mobile
  },
  layoutHeights: { header: 72, mobileIconsMenu: 66 },
  mixins: { buttons: buttonsMixins },
  colors: { white: '#fff', black: '#000', primaryBlue: '#1E6679', table: { header: '#b4d0de' }, shade: 'rgba(0, 0, 0, 0.5)' }
};
export default theme;
""")
    write(app / "app" / "styles" / "theme" / "mixins" / "layoutMixins.js", "const mixins = { shrink: css`a`, layout: css`b` };\nexport default mixins;\n")
    write(app / "app" / "styles" / "theme" / "layout.js", "export const layoutHeights = { header: 80, mobileHeader: 66 };\n")
    write(app / "app" / "app.js", "import { ThemeProvider } from 'styled-components';\nimport theme from 'styles/theme';\nconst App = ({ children }) => <ThemeProvider theme={theme}>{children}</ThemeProvider>;\nexport default App;\n")
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
import { bps, layoutHeights } from './layout';
const theme = { bps, layoutHeights, colors, mixins };
export default theme;
""")
    write(app / "app" / "styles" / "theme" / "colors.js", "const colors = { white: '#fff', red: 'red' };\nexport default colors;\n")
    write(app / "app" / "styles" / "theme" / "mixin.js", "import layout from './mixins/layoutMixins';\nconst mixins = { ...layout, buttons: {} };\nexport default mixins;\n")
    write(app / "app" / "styles" / "theme" / "mixins" / "layoutMixins.js", "const mixins = { shrink: css`a`, layout: css`${({ $layout }) => css`b`}`, media: {} };\nexport default mixins;\n")
    write(app / "app" / "styles" / "theme" / "layout.js", """export const breakPoints = { mobile: 1279, desktop: 1280 };
export const bps = {
  mobile: `@media screen and (max-width: ${breakPoints.mobile}px)`,
  desktop: `@media screen and (min-width:  ${breakPoints.desktop}px)`
};
export const layoutHeights = { header: 88, mobileHeader: 66 };
""")
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
        self.assertEqual(profile["theme"]["bps"], ["desktop", "mobile", "smallerMobile", "mobilePixels"])
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

    def test_overlapping_breakpoints_warn(self):
        with tempfile.TemporaryDirectory() as tmp:
            ora_like(Path(tmp))
            result = probe_repo.probe(Path(tmp))
        theme = result["profile"]["theme"]
        self.assertEqual(theme["breakpoints"], {"mobile": 1279, "smallerMobile": 320, "laptop": 900})
        self.assertEqual(theme["bpsMedia"], {
            "desktop": "@media (min-width: 1279px)",
            "mobile": "@media (max-width: 1279px)",
            "smallerMobile": "@media (max-width: 320px)",
            "mobilePixels": None,
        })
        self.assertIn("bps.desktop and bps.mobile both match at 1279px", result["warnings"])

    def test_adjacent_breakpoints_do_not_warn(self):
        with tempfile.TemporaryDirectory() as tmp:
            jaecoo_like(Path(tmp))
            result = probe_repo.probe(Path(tmp))
        theme = result["profile"]["theme"]
        self.assertEqual(theme["breakpoints"], {"mobile": 1279, "desktop": 1280})
        self.assertEqual(theme["bpsMedia"]["desktop"], "@media screen and (min-width: 1280px)")
        self.assertNotIn("both match", " ".join(result["warnings"]))

    def test_theme_keys_come_from_the_theme_provider_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = ora_like(Path(tmp))
            profile = probe_repo.probe(Path(tmp))["profile"]
            self.assertEqual(profile["theme"]["layoutHeights"], ["header", "mobileIconsMenu"])
            self.assertEqual(profile["theme"]["mixins"], ["buttons"])
            write(app / "app" / "styles" / "altTheme.js", "import { layoutHeights } from './theme/layout';\nimport layout from './theme/mixins/layoutMixins';\nexport default { layoutHeights, mixins: { ...layout } };\n")
            write(app / "app" / "app.js", "import theme from 'styles/altTheme';\nconst App = () => <ThemeProvider theme={theme} />;\n")
            profile = probe_repo.probe(Path(tmp))["profile"]
        self.assertEqual(profile["theme"]["layoutHeights"], ["header", "mobileHeader"])
        self.assertEqual(profile["theme"]["mixins"], ["shrink", "layout"])

    def test_mobile_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = ora_like(Path(tmp))
            components = app / "app" / "components"
            for index in range(3):
                write(components / "Sections" / "Hero" / f"Use{index}.js", "import useIsMobile from '@colmobil/next/core/hooks/useIsMobile';\n")
            write(components / "Sections" / "Hero" / "Local.js", "import useIsMobile from 'hooks/useIsMobile';\n")
            write(components / "Sections" / "Hero" / "Relative.js", "import useIsMobile from '../../../hooks/useIsMobile';\n")
            write(app / "app" / "hooks" / "useIsMobile.js", "export default function useIsMobile() {}\n")
            write(components / "Core" / "Image" / "ResponsiveImage.js", "const ResponsiveImage = () => null;\n")
            write(components / "Layout" / "Assets" / "Icons" / "ClockIcon.js", "const ClockIcon = () => <svg />;\n")
            write(components / "Layout" / "IconFactory.js", "const IconFactory = () => null;\n")
            (app / "public" / "icons").mkdir(parents=True)
            mobile = probe_repo.probe(Path(tmp))["profile"]["mobile"]
        self.assertEqual(mobile["hook"], [{"import": "@colmobil/next/core/hooks/useIsMobile", "count": 3}, {"import": "hooks/useIsMobile", "count": 2}])
        self.assertEqual(mobile["responsiveImage"], "app/components/Core/Image/ResponsiveImage.js")
        self.assertEqual(mobile["icons"], {"publicIcons": "public/icons", "inline": ["app/components/Layout/Assets/Icons"]})
        self.assertIsNone(mobile["hoverGate"])

    def test_hover_gate(self):
        styled = {
            "bps-desktop": "const revealCard = (state) => css`\n  &${state} .text { opacity: 1; }\n`;\nconst S = styled.div`\n  .card {\n    ${({ theme }) => theme.bps?.desktop} {\n      ${revealCard(':hover')}\n    }\n  }\n`;\n",
            "hover-media": "const S = styled.div`\n  @media (hover: hover) and (pointer: fine) {\n    .card:hover { opacity: 1; }\n  }\n`;\n",
            None: "const S = styled.div`\n  .card:hover { opacity: 1; }\n`;\n",
        }
        for gate, text in styled.items():
            with self.subTest(gate):
                with tempfile.TemporaryDirectory() as tmp:
                    app = ora_like(Path(tmp))
                    write(app / "app" / "components" / "Sections" / "Hero" / "StyledHero.js", text)
                    self.assertEqual(probe_repo.probe(Path(tmp))["profile"]["mobile"]["hoverGate"], gate)

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
    def check(self, mutate=None, repo=ora_like, mobile_pass=False):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        app = repo(Path(tmp.name))
        folder = app / "app" / "components" / "Sections" / "Hero"
        if mutate:
            mutate(app, folder)
        profile = probe_repo.probe(Path(tmp.name))["profile"]
        return check_section.check_section(profile, "Hero", lint=False, mobile_pass=mobile_pass), app, folder

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
            "no-hardcoded-bp": lambda app, f: write(f / "StyledHero.js", "const S = styled.div`\n  @media (max-width: 1279px) { width: 100%; }\n`;\n"),
            "hover-gated": lambda app, f: write(f / "StyledHero.js", HOVER_OPEN),
        }
        for check_id, mutate in cases.items():
            with self.subTest(check_id):
                result, _, _ = self.check(mutate, mobile_pass=True)
                self.assertEqual(statuses(result)[check_id], "fail", result["checks"])
                failing = [row["id"] for row in result["checks"] if row["status"] == "fail"]
                self.assertEqual(failing, [check_id])

    def test_warnings_do_not_fail(self):
        def mutate(app, folder):
            write(folder / "StyledHero.js", "const S = styled.div`\n  color: #1e6679;\n`;\n")
        result, _, _ = self.check(mutate)
        self.assertTrue(result["pass"])
        self.assertEqual(statuses(result)["theme-colors"], "warn")
        self.assertNotIn("bps-present", statuses(result))

    def test_mobile_checks_pass_on_a_good_section(self):
        for repo in (ora_like, jaecoo_like):
            with self.subTest(repo.__name__):
                result, _, _ = self.check(repo=repo, mobile_pass=True)
                for check_id in ("bps-overlap", "mobile-nested", "hover-gated", "no-hardcoded-bp"):
                    self.assertEqual(statuses(result)[check_id], "pass", result["checks"])

    def test_bps_overlap_warns_only_where_ranges_overlap(self):
        def mutate(app, folder):
            write(folder / "StyledHero.js", "const S = styled.div`\n  ${({ theme }) => theme.bps?.desktop} { width: 50%; }\n`;\n")
        result, _, _ = self.check(mutate)
        self.assertEqual(statuses(result)["bps-overlap"], "warn")
        self.assertIn("1279px", next(row["detail"] for row in result["checks"] if row["id"] == "bps-overlap"))
        self.assertTrue(result["pass"])
        result, _, _ = self.check(mutate, repo=jaecoo_like)
        self.assertEqual(statuses(result)["bps-overlap"], "pass")

    def test_mobile_nested_warns_above_six_selectors(self):
        def block(count):
            rules = "".join(f"    .a{index} {{ width: 1px; }}\n" for index in range(count))
            return f"const S = styled.div`\n  .a0 {{ width: 2px; }}\n  ${{({{ theme }}) => theme.bps.mobile}} {{\n{rules}  }}\n`;\n"
        result, _, _ = self.check(lambda app, folder: write(folder / "StyledHero.js", block(7)))
        self.assertEqual(statuses(result)["mobile-nested"], "warn")
        self.assertTrue(result["pass"])
        result, _, _ = self.check(lambda app, folder: write(folder / "StyledHero.js", block(6)))
        self.assertEqual(statuses(result)["mobile-nested"], "pass")

    def test_hover_gated(self):
        result, _, _ = self.check(lambda app, folder: write(folder / "StyledHero.js", HOVER_OPEN))
        self.assertEqual(statuses(result)["hover-gated"], "warn")
        self.assertTrue(result["pass"])
        gated = {
            "bps-desktop": "const S = styled.div`\n  ${({ theme }) => theme.bps?.desktop} {\n    .card:hover .text { opacity: 1; }\n  }\n`;\n",
            "helper": "const reveal = (state) => css`\n  &${state} .text { grid-template-rows: 1fr; }\n`;\nconst S = styled.div`\n  .card {\n    ${({ theme }) => theme.bps?.desktop} {\n      ${reveal(':hover')}\n    }\n  }\n`;\n",
            "hover-media": "const S = styled.div`\n  @media (hover: hover) {\n    .card:hover .text { display: block; }\n  }\n`;\n",
            "dim-only": "const S = styled.div`\n  .card:hover { opacity: 0.8; }\n`;\n",
        }
        for name, text in gated.items():
            with self.subTest(name):
                result, _, _ = self.check(lambda app, folder: write(folder / "StyledHero.js", text), mobile_pass=True)
                self.assertEqual(statuses(result)["hover-gated"], "pass", result["checks"])
        helper_open = "const reveal = css`\n  &:hover .text { max-height: 200px; }\n`;\nconst S = styled.div`\n  .card { ${reveal} }\n`;\n"
        result, _, _ = self.check(lambda app, folder: write(folder / "StyledHero.js", helper_open), mobile_pass=True)
        self.assertEqual(statuses(result)["hover-gated"], "fail")

    def test_hover_media_repo_needs_hover_media(self):
        def mutate(app, folder):
            write(app / "app" / "components" / "Sections" / "Card" / "StyledCard.js", "const S = styled.div`\n  @media (hover: hover) { a:hover { opacity: 1; } }\n`;\n")
            write(folder / "StyledHero.js", "const S = styled.div`\n  ${({ theme }) => theme.bps.desktop} {\n    .card:hover .text { opacity: 1; }\n  }\n`;\n")
        result, _, _ = self.check(mutate, mobile_pass=True)
        self.assertEqual(statuses(result)["hover-gated"], "fail")

    def test_theme_bps_media_is_not_hardcoded(self):
        result, _, _ = self.check(lambda app, folder: write(folder / "StyledHero.js", "const S = styled.div`\n  @media (hover: hover) { a { color: red; } }\n  ${({ theme }) => theme.bps.mobile} { width: 1px; }\n`;\n"))
        self.assertEqual(statuses(result)["no-hardcoded-bp"], "pass")

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

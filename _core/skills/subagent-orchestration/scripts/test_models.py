"""Unit tests for models.py. Run: python3 -m pytest _core/skills/subagent-orchestration/scripts/test_models.py"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import models  # noqa: E402


def pick_json(capsys, *argv):
    assert models.main(["pick", *argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)


def table_json(capsys, *argv):
    assert models.main(["table", *argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)


def all_cursor_slugs():
    h = models.load()["cursor"]
    return sorted({e["model"] for _, _, f in models.entries(h) for e in models.ranked(f)})


def listing(slugs):
    return "Available models\n\n" + "".join(f"{s} - {s.upper()}\n" for s in slugs) + "\nTip: use --model <id>\n"


@pytest.fixture
def agent(monkeypatch):
    """Fake `cursor-agent` on PATH; set .result to (text, returncode, error)."""
    class Fake:
        result = (listing(all_cursor_slugs()), 0, None)
        calls = []

    monkeypatch.setattr(models.shutil, "which", lambda name: "/fake/" + name)

    def fake_run(cmd):
        Fake.calls.append(cmd)
        return Fake.result

    monkeypatch.setattr(models, "run", fake_run)
    return Fake


@pytest.mark.parametrize("harness", ["cursor", "claude-code"])
def test_tiers_structural_invariants(harness):
    h = models.load()[harness]
    never = h["never"]
    expected_slots = [("light", "default"), ("mid", "default"), ("strong", "default"), ("strong", "hardest")]
    found = [(t, v) for t, v, _ in models.entries(h)]
    assert found == expected_slots

    primaries = {}
    for tier, variant, fields in models.entries(h):
        chain = models.ranked(fields)
        assert 1 <= len(chain) <= models.MAX_RANKED
        idents = [(e.get("model"), e.get("effort")) for e in chain]
        assert len(idents) == len(set(idents)), f"duplicate entry in {harness} {tier}/{variant}"
        for entry in chain:
            assert models.floor_problems(entry, tier, harness, never) == []
        primaries[(tier, variant)] = idents[0]

    # Every retry step must strictly advance the primary
    assert primaries[("light", "default")] != primaries[("mid", "default")]
    assert primaries[("mid", "default")] != primaries[("strong", "default")]
    assert primaries[("strong", "default")] != primaries[("strong", "hardest")]


@pytest.mark.parametrize("harness, tool", [("cursor", "Task"), ("claude-code", "Agent")])
@pytest.mark.parametrize("argv, expected_slot", [
    (["--tier", "light"], "light/default"),
    (["--tier", "light", "--retry"], "mid/default"),
    (["--tier", "mid"], "mid/default"),
    (["--tier", "mid", "--retry"], "strong/default"),
    (["--tier", "strong"], "strong/default"),
    (["--tier", "strong", "--retry"], "strong/hardest"),
    (["--tier", "strong", "--hardest"], "strong/hardest"),
])
def test_pick_escalation_chain(capsys, harness, tool, argv, expected_slot):
    out = pick_json(capsys, "--harness", harness, *argv)
    assert out["slot"] == expected_slot
    assert out["tool"] == tool
    assert len(out["fallbacks"]) == 2


def test_pick_retry_at_ceiling_exits_2(capsys):
    assert models.main(["pick", "--harness", "cursor", "--tier", "strong", "--hardest", "--retry"]) == 2
    assert "escalation ceiling" in capsys.readouterr().err


def test_pick_hardest_on_non_strong_exits_2(capsys):
    assert models.main(["pick", "--harness", "cursor", "--tier", "mid", "--hardest"]) == 2
    assert "--hardest only applies" in capsys.readouterr().err


@pytest.mark.parametrize("harness, expected_type", [("cursor", "explore"), ("claude-code", "Explore")])
def test_pick_readonly_sets_subagent_type(capsys, harness, expected_type):
    out = pick_json(capsys, "--harness", harness, "--tier", "light", "--readonly")
    assert out["call"]["subagent_type"] == expected_type
    assert all(f["subagent_type"] == expected_type for f in out["fallbacks"])


def test_table_resolves_all_four_slots(capsys):
    out = table_json(capsys, "--harness", "cursor")
    assert list(out["slots"].keys()) == ["light/default", "mid/default", "strong/default", "strong/hardest"]


def test_pick_available_walks_fallbacks_in_order(capsys):
    h = models.load()["cursor"]
    chain = [e["model"] for e in models.ranked(h["strong"]["default"])]
    # Primary missing -> picks fallback 1 and keeps fallback 2
    out = pick_json(capsys, "--harness", "cursor", "--tier", "strong", "--available", f"{chain[2]},{chain[1]}")
    assert out["call"]["model"] == chain[1]
    assert [f["model"] for f in out["fallbacks"]] == [chain[2]]
    assert out["skipped"] == [chain[0]]


def test_pick_available_none_of_top3_exits_2(capsys):
    rc = models.main(["pick", "--harness", "cursor", "--tier", "mid", "--available", "composer-2.5-fast,grok-4.7-low"])
    assert rc == 2
    assert "none of the top 3" in capsys.readouterr().err


def test_pick_refuses_banned_fallback(tmp_path, monkeypatch, capsys):
    data = json.load(open(models.TIERS))
    data["harnesses"]["cursor"]["mid"]["default"]["fallbacks"][1]["model"] = "composer-2.5-fast"
    bad = tmp_path / "tiers.json"
    bad.write_text(json.dumps(data))
    monkeypatch.setattr(models, "TIERS", str(bad))
    assert models.main(["pick", "--harness", "cursor", "--tier", "mid"]) == 2
    assert "composer-2.5-fast is banned" in capsys.readouterr().err


@pytest.mark.parametrize("value", [
    "grok-4.7-low", "grok-4.7-xhigh", "claude-opus-5-5-high-fast",
    "auto", "inherit", "composer-2.5-fast", "cursor-grok-4.6-high", "gpt-5.6-sol-none",
])
def test_banned_values(value):
    assert models.banned(value, models.load()["cursor"]["never"])


def test_composer_standard_not_banned():
    assert not models.banned("composer-2.5", models.load()["cursor"]["never"])


@pytest.mark.parametrize("result, reason", [
    (("Failed to load models: [unavailable] getaddrinfo EAI_AGAIN api2.cursor.sh\n", 1, None),
     "exit 1: Failed to load models"),
    (("Available models\n\nTip: use --model <id>\n", 0, None), "no slugs listed"),
    ((None, None, "timed out after 90 seconds"), "timed out after 90 seconds"),
])
def test_check_cursor_skips_when_models_unavailable(agent, capsys, result, reason):
    agent.result = result
    assert models.main(["check", "--harness", "cursor"]) == 0
    out = capsys.readouterr().out
    assert "SKIP: cursor-agent models unavailable (" in out and reason in out
    assert "FAIL" not in out


def test_check_cursor_skips_without_binary(monkeypatch, capsys):
    monkeypatch.setattr(models.shutil, "which", lambda name: None)
    assert models.main(["check", "--harness", "cursor"]) == 0
    assert "SKIP: cursor-agent not on PATH" in capsys.readouterr().out


def test_check_cursor_passes_every_primary_and_fallback(agent, capsys):
    assert models.main(["check", "--harness", "cursor"]) == 0
    out = capsys.readouterr().out
    assert agent.calls[-1] == ["cursor-agent", "models"]
    assert out.count("\nPASS ") == 12 and "FAIL" not in out


def test_check_cursor_fails_a_missing_fallback(agent, capsys):
    slugs = all_cursor_slugs()
    missing = slugs[0]
    agent.result = (listing([s for s in slugs if s != missing]), 0, None)
    assert models.main(["check", "--harness", "cursor"]) == 1
    out = capsys.readouterr().out
    assert f"{missing} (not in cursor-agent models)" in out


def test_check_cursor_fails_identical_retry_primary(tmp_path, monkeypatch, agent, capsys):
    data = json.load(open(models.TIERS))
    data["harnesses"]["cursor"]["strong"]["hardest"]["model"] = data["harnesses"]["cursor"]["strong"]["default"]["model"]
    bad = tmp_path / "tiers.json"
    bad.write_text(json.dumps(data))
    monkeypatch.setattr(models, "TIERS", str(bad))
    assert models.main(["check", "--harness", "cursor"]) == 1
    assert "identical primary" in capsys.readouterr().out


def test_check_claude_code_passes_and_rejects_low_effort_in_mid(tmp_path, monkeypatch, capsys):
    assert models.main(["check", "--harness", "claude-code"]) == 0
    assert "FAIL" not in capsys.readouterr().out
    data = json.load(open(models.TIERS))
    data["harnesses"]["claude-code"]["mid"]["default"]["fallbacks"][0]["effort"] = "low"
    bad = tmp_path / "tiers.json"
    bad.write_text(json.dumps(data))
    monkeypatch.setattr(models, "TIERS", str(bad))
    assert models.main(["check", "--harness", "claude-code"]) == 1
    assert "effort low is not allowed for mid" in capsys.readouterr().out


def test_parse_slugs_ignores_header_and_tip():
    text = listing(["grok-4.7-high", "claude-opus-5-5-high"]) + "Failed to load - something\n"
    assert models.parse_slugs(text) == {"grok-4.7-high", "claude-opus-5-5-high"}

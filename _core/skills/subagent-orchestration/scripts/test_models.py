"""Unit tests for models.py. Run: python3 -m pytest _core/skills/subagent-orchestration/scripts/test_models.py"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import models  # noqa: E402

CURSOR_SLOTS = {
    ("mid", "default"): ["claude-sonnet-5-5-high", "gpt-5.6-sol-medium", "gemini-4-neon-medium"],
    ("mid", "grok"): ["grok-4.7-medium", "grok-4.7-high", "claude-sonnet-5-5-high"],
    ("strong", "default"): ["claude-opus-5-5-medium", "claude-opus-5-5-high", "grok-4.7-high"],
    ("strong", "hardest"): ["claude-opus-5-5-high", "grok-4.7-high", "gpt-5.6-sol-medium"],
    ("strong", "grok"): ["grok-4.7-high", "claude-opus-5-5-high", "gpt-5.6-sol-medium"],
    ("strong", "grok-hardest"): ["claude-opus-5-5-high", "grok-4.7-high", "gpt-5.6-sol-medium"],
}
CLAUDE_CODE_SLOTS = {
    ("mid", "default"): [("sonnet", "high"), ("opus", "medium"), ("opus", "high")],
    ("strong", "default"): [("opus", "high"), ("opus", "xhigh"), ("sonnet", "high")],
    ("strong", "hardest"): [("opus", "xhigh"), ("opus", "high"), ("opus", "max")],
}
ALL_CURSOR_SLUGS = sorted({s for chain in CURSOR_SLOTS.values() for s in chain})
IDE_ENABLED = ["claude-sonnet-5-5-high", "claude-opus-5-5-high", "grok-4.7-high",
               "gpt-5.6-sol-medium", "gemini-4-neon-medium", "gemini-4-carbon-medium"]


def pick_json(capsys, *argv):
    assert models.main(["pick", *argv, "--json"]) == 0
    return json.loads(capsys.readouterr().out)


def listing(slugs):
    return "Available models\n\n" + "".join(f"{s} - {s.upper()}\n" for s in slugs) + "\nTip: use --model <id>\n"


@pytest.fixture
def agent(monkeypatch):
    """Fake `cursor-agent` on PATH; set .result to (text, returncode, error)."""
    class Fake:
        result = (listing(ALL_CURSOR_SLUGS), 0, None)
        calls = []

    monkeypatch.setattr(models.shutil, "which", lambda name: "/fake/" + name)

    def fake_run(cmd):
        Fake.calls.append(cmd)
        return Fake.result

    monkeypatch.setattr(models, "run", fake_run)
    return Fake


def test_tiers_every_slot_is_ranked_top3():
    h = models.load()
    assert json.load(open(models.TIERS))["checked"] == "2026-11-22"
    for (tier, variant), want in CURSOR_SLOTS.items():
        chain = models.ranked(h["cursor"][tier][variant])
        assert [e["model"] for e in chain] == want
        assert all(e["subagent_type"] == "generalPurpose" for e in chain)
    for (tier, variant), want in CLAUDE_CODE_SLOTS.items():
        chain = models.ranked(h["claude-code"][tier][variant])
        assert [(e["model"], e["effort"]) for e in chain] == want
    for name, harness in h.items():
        for _, _, fields in models.entries(harness):
            for entry in models.ranked(fields):
                assert models.floor_problems(entry, name, harness["never"]) == []


@pytest.mark.parametrize("argv, slot, want", [
    (["--tier", "mid"], "mid/default", CURSOR_SLOTS[("mid", "default")]),
    (["--tier", "strong"], "strong/default", CURSOR_SLOTS[("strong", "default")]),
    (["--tier", "mid", "--retry"], "strong/default", CURSOR_SLOTS[("strong", "default")]),
    (["--tier", "strong", "--retry"], "strong/hardest", CURSOR_SLOTS[("strong", "hardest")]),
    (["--tier", "mid", "--family", "grok"], "mid/grok", CURSOR_SLOTS[("mid", "grok")]),
    (["--tier", "strong", "--family", "grok"], "strong/grok", CURSOR_SLOTS[("strong", "grok")]),
    (["--tier", "strong", "--family", "grok", "--retry"], "strong/grok-hardest",
     CURSOR_SLOTS[("strong", "grok-hardest")]),
])
def test_pick_cursor_primary_and_two_ordered_fallbacks(capsys, argv, slot, want):
    out = pick_json(capsys, "--harness", "cursor", *argv)
    assert out["slot"] == slot and out["tool"] == "Task"
    assert out["call"] == {"subagent_type": "generalPurpose", "model": want[0]}
    assert [f["model"] for f in out["fallbacks"]] == want[1:]
    assert len(out["fallbacks"]) == 2


@pytest.mark.parametrize("argv, slot", [
    (["--tier", "mid"], ("mid", "default")),
    (["--tier", "strong"], ("strong", "default")),
    (["--tier", "mid", "--retry"], ("strong", "default")),
    (["--tier", "strong", "--retry"], ("strong", "hardest")),
    (["--tier", "strong", "--hardest"], ("strong", "hardest")),
])
def test_pick_claude_code_primary_and_two_ordered_fallbacks(capsys, argv, slot):
    out = pick_json(capsys, "--harness", "claude-code", *argv)
    want = CLAUDE_CODE_SLOTS[slot]
    assert out["tool"] == "Agent"
    assert (out["call"]["model"], out["call"]["effort"]) == want[0]
    assert out["call"]["subagent_type"] == "general-purpose"
    assert [(f["model"], f["effort"]) for f in out["fallbacks"]] == want[1:]


def test_pick_claude_code_has_no_grok(capsys):
    assert models.main(["pick", "--harness", "claude-code", "--tier", "mid", "--family", "grok"]) == 2
    assert "no grok model" in capsys.readouterr().err


def test_pick_text_output_lists_fallbacks(capsys):
    assert models.main(["pick", "--harness", "cursor", "--tier", "strong"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "# cursor strong (claude) via Task"
    assert "model: claude-opus-5-5-medium" in lines
    fb = next(line for line in lines if line.startswith("fallbacks: "))
    assert [f["model"] for f in json.loads(fb[len("fallbacks: "):])] == ["claude-opus-5-5-high", "grok-4.7-high"]


def test_pick_available_takes_fallback_1_when_primary_not_enabled(capsys):
    out = pick_json(capsys, "--harness", "cursor", "--tier", "strong", "--available", ",".join(IDE_ENABLED))
    assert out["call"]["model"] == "claude-opus-5-5-high"
    assert [f["model"] for f in out["fallbacks"]] == ["grok-4.7-high"]
    assert out["skipped"] == ["claude-opus-5-5-medium"]


def test_pick_available_takes_fallback_2_and_keeps_order(capsys):
    out = pick_json(capsys, "--harness", "cursor", "--tier", "mid", "--family", "grok",
                    "--available", "claude-sonnet-5-5-high, grok-4.7-high")
    assert out["call"]["model"] == "grok-4.7-high"
    assert [f["model"] for f in out["fallbacks"]] == ["claude-sonnet-5-5-high"]


def test_pick_available_primary_enabled_keeps_full_chain(capsys):
    out = pick_json(capsys, "--harness", "cursor", "--tier", "mid", "--available", ",".join(IDE_ENABLED))
    assert out["call"]["model"] == "claude-sonnet-5-5-high"
    assert [f["model"] for f in out["fallbacks"]] == ["gpt-5.6-sol-medium", "gemini-4-neon-medium"]
    assert out["skipped"] == []


def test_pick_available_none_of_top3_exits_2(capsys):
    rc = models.main(["pick", "--harness", "cursor", "--tier", "mid", "--available", "composer-2.5,grok-4.7-low"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "none of the top 3" in err and "claude-sonnet-5-5-high" in err


def test_pick_refuses_banned_fallback(tmp_path, monkeypatch, capsys):
    data = json.load(open(models.TIERS))
    data["harnesses"]["cursor"]["mid"]["default"]["fallbacks"][1]["model"] = "composer-2.5-fast"
    bad = tmp_path / "tiers.json"
    bad.write_text(json.dumps(data))
    monkeypatch.setattr(models, "TIERS", str(bad))
    assert models.main(["pick", "--harness", "cursor", "--tier", "mid"]) == 2
    assert "composer-2.5-fast is banned" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["grok-4.7-low", "grok-4.7-xhigh", "claude-opus-5-5-high-fast", "auto",
                                   "composer-2.5", "cursor-grok-4.6-high", "gpt-5.6-sol-none", "claude-haiku-5-5-high"])
def test_banned_values(value):
    assert models.banned(value, models.load()["cursor"]["never"])


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
    assert out.count("\nPASS ") == 18 and "FAIL" not in out
    assert "PASS strong/default fallback 2: grok-4.7-high" in out


def test_check_cursor_fails_a_missing_fallback(agent, capsys):
    agent.result = (listing([s for s in ALL_CURSOR_SLUGS if s != "gemini-4-neon-medium"]), 0, None)
    assert models.main(["check", "--harness", "cursor"]) == 1
    out = capsys.readouterr().out
    assert "FAIL mid/default fallback 2: gemini-4-neon-medium (not in cursor-agent models)" in out
    assert out.count("FAIL") == 1


def test_check_cursor_fails_a_banned_fallback_even_if_listed(tmp_path, monkeypatch, agent, capsys):
    data = json.load(open(models.TIERS))
    data["harnesses"]["cursor"]["strong"]["grok"]["fallbacks"][0]["model"] = "grok-4.7-xhigh"
    bad = tmp_path / "tiers.json"
    bad.write_text(json.dumps(data))
    monkeypatch.setattr(models, "TIERS", str(bad))
    agent.result = (listing(ALL_CURSOR_SLUGS + ["grok-4.7-xhigh"]), 0, None)
    assert models.main(["check", "--harness", "cursor"]) == 1
    out = capsys.readouterr().out
    assert "FAIL strong/grok fallback 1: grok-4.7-xhigh is banned" in out


def test_check_cursor_offline_still_fails_a_banned_value(tmp_path, monkeypatch, agent, capsys):
    data = json.load(open(models.TIERS))
    data["harnesses"]["cursor"]["mid"]["default"]["model"] = "auto"
    bad = tmp_path / "tiers.json"
    bad.write_text(json.dumps(data))
    monkeypatch.setattr(models, "TIERS", str(bad))
    agent.result = ("Failed to load models\n", 1, None)
    assert models.main(["check", "--harness", "cursor"]) == 1
    out = capsys.readouterr().out
    assert "FAIL mid/default: auto is banned" in out and "SKIP: cursor-agent models unavailable" in out


def test_check_claude_code_passes_and_rejects_low_effort(tmp_path, monkeypatch, capsys):
    assert models.main(["check", "--harness", "claude-code"]) == 0
    assert "FAIL" not in capsys.readouterr().out
    data = json.load(open(models.TIERS))
    data["harnesses"]["claude-code"]["mid"]["default"]["fallbacks"][0]["effort"] = "low"
    bad = tmp_path / "tiers.json"
    bad.write_text(json.dumps(data))
    monkeypatch.setattr(models, "TIERS", str(bad))
    assert models.main(["check", "--harness", "claude-code"]) == 1
    assert "FAIL mid/default fallback 1: effort low is below mid" in capsys.readouterr().out


def test_parse_slugs_ignores_header_and_tip():
    text = listing(["grok-4.7-high", "claude-opus-5-5-high"]) + "Failed to load - something\n"
    assert models.parse_slugs(text) == {"grok-4.7-high", "claude-opus-5-5-high"}

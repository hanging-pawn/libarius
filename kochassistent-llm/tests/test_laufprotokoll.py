"""Tests für Probedatensatz und Laufprotokoll (LIBAR-117)."""
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from kochassistent.training import laufprotokoll as lp
from kochassistent.training import probelauf

PROJEKT = Path(__file__).resolve().parents[1]
SCHEMA_BSP = json.loads((PROJEKT / "schema" / "trainingsbeispiel.schema.json").read_text("utf-8"))


def test_probedatensatz_50_gueltig_und_wiederholbar(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    beispiele = probelauf.erzeuge(a)
    probelauf.erzeuge(b)
    assert len(beispiele) == 50
    v = Draft202012Validator(SCHEMA_BSP)
    assert all(not list(v.iter_errors(x)) for x in beispiele)
    for name in ("beispiele.jsonl", "chat/train.jsonl", "chat/valid.jsonl"):
        assert (a / name).read_bytes() == (b / name).read_bytes()
    train = [json.loads(z) for z in (a / "chat" / "train.jsonl").read_text("utf-8").splitlines()]
    assert len(train) == 45 and all([m["role"] for m in z["messages"]] == ["user", "assistant"] for z in train)


def test_probedatensatz_rechnungen_stimmen(tmp_path):
    for b in probelauf.erzeuge(tmp_path):
        ausdruck, _, ergebnis = b["denkweg"][0]["stuetze"]["rechnung"].partition(" = ")
        x, y = map(float, ausdruck.split(" / "))
        assert round(x / y, 2) == float(ergebnis)


def _protokoll(tmp_path, **kw):
    t, v = tmp_path / "train.jsonl", tmp_path / "valid.jsonl"
    t.write_text('{"messages": []}\n' * 3, "utf-8")
    v.write_text('{"messages": []}\n', "utf-8")
    konfig = {"project_name": "kochassistent-x", "model_name": "unsloth/Qwen3.5-0.8B", "random_seed": 7,
              "learning_rate": "2e-4", "local_datasets": ["/fremd/pfad"]}
    return lp.neu("x", konfig, t, v, **kw)


def test_neues_protokoll_ist_schemagueltig(tmp_path):
    d = _protokoll(tmp_path, studio={"version": "2026.11.1"}, export={"format": "gguf", "quantisierung": "Q4_K_M"})
    assert lp.pruefe(d) == []
    assert d["saat"] == 7 and d["basismodell"] == "unsloth/Qwen3.5-0.8B"
    assert "local_datasets" not in d["einstellungen"] and "project_name" not in d["einstellungen"]
    assert [s["zeilen"] for s in d["datensaetze"]] == [3, 1] and len(d["datensaetze"][0]["sha256"]) == 64


def test_schema_verlangt_version_und_export(tmp_path):
    d = _protokoll(tmp_path)
    del d["studio"]["version"]
    d["export"] = {"format": "zip"}
    fehler = " ".join(lp.pruefe(d))
    assert "version" in fehler and "zip" in fehler


def test_vergleich_meldet_nur_unterschiede(tmp_path):
    a = _protokoll(tmp_path)
    b = json.loads(json.dumps(a))
    b["lauf"], b["wiederholt"] = "y", "x"
    assert lp.vergleiche(a, b) == []
    b["ergebnis"] = {"status": "fertig", "verlust_letzter": 0.5}
    b["datensaetze"][0]["sha256"] = "0" * 64
    felder = {f for f, _, _ in lp.vergleiche(a, b)}
    assert felder == {"ergebnis.status", "ergebnis.verlust_letzter", "datensatz.train.sha256"}


def test_eingecheckte_protokolle_gueltig():
    dateien = sorted((PROJEKT / "konfig" / "laeufe").glob("*.json"))
    assert dateien
    for f in dateien:
        assert lp.pruefe(json.loads(f.read_text("utf-8"))) == [], f.name

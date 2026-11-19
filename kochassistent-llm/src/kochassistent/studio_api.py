"""Aufrufe an die API der Unsloth-Studio-App auf dem Mac Studio (127.0.0.1:8888, nur lokal dort).

Der Weg führt über SSH: curl läuft auf dem Studio und liest seine Konfiguration, auch den
Schlüssel, von stdin (`curl --config -`). So steht der Schlüssel weder in argv noch im Chat.

Umgebung: STUDIO_HOST (studio), STUDIO_SCHLUESSEL (~/.config/kochassistent/studio-api-key).
Schlüssel mit Zugriff «full» in der Unsloth-App anlegen; siehe skripte/studio.sh api-schluessel.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

HOST = os.environ.get("STUDIO_HOST", "studio")
SCHLUESSEL = Path(os.environ.get("STUDIO_SCHLUESSEL", Path.home() / ".config/kochassistent/studio-api-key"))
# Eine SSH-Verbindung für viele Aufrufe (Destillation schickt Tausende)
SSH = ["ssh", "-o", "ControlMaster=auto", "-o", "ControlPath=~/.ssh/cm-kochassistent-%r@%h:%p",
       "-o", "ControlPersist=10m", HOST]


class ApiFehler(RuntimeError):
    pass


def _curl_wert(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def api(methode: str, pfad: str, body: dict | None = None, timeout: int = 900, formular: str | None = None) -> dict:
    """Ruft die Studio-API auf und gibt die JSON-Antwort zurück; ApiFehler bei HTTP ≥ 400 oder ohne JSON.

    formular: curl-Form-Feld für Uploads, z. B. «file=@/Users/Shared/x.jsonl;type=application/json».
    """
    key = SCHLUESSEL.read_text().strip()
    cfg = [f'header = "Authorization: Bearer {key}"', f'request = "{methode}"', "silent", "show-error",
           f"max-time = {timeout}", f'url = "http://127.0.0.1:8888{pfad}"', 'write-out = "\\n%{http_code}"']
    if body is not None:
        cfg += ['header = "Content-Type: application/json"',
                f'data-binary = "{_curl_wert(json.dumps(body, ensure_ascii=True))}"']
    if formular is not None:
        cfg.append(f'form = "{_curl_wert(formular)}"')
    r = subprocess.run(SSH + ["curl --config -"], input="\n".join(cfg) + "\n",
                       capture_output=True, text=True, timeout=timeout + 60)
    inhalt, _, code = r.stdout.rpartition("\n")
    if not code.isdigit() or int(code) >= 400:
        raise ApiFehler(f"{methode} {pfad}: HTTP {code or '?'} {inhalt[:300]} {r.stderr[:200]}")
    try:
        return json.loads(inhalt)
    except json.JSONDecodeError as exc:
        raise ApiFehler(f"{methode} {pfad}: keine JSON-Antwort ({exc}): {inhalt[:300]}") from exc


AUSTAUSCH = "/Users/Shared/kochassistent-llm/upload"  # für edal (App) und admin (SSH) lesbar


def hochladen(lokal: Path, name: str) -> str:
    """Datei per rsync auf das Studio legen und in den Datensatz-Ordner der App hochladen; gibt stored_path zurück.

    Die App nimmt beim Trainingsstart nur Pfade unter ihren eigenen Datensatz-Wurzeln an.
    """
    subprocess.run(SSH + [f"mkdir -p {AUSTAUSCH}"], check=True)
    subprocess.run(["rsync", "-a", "-e", " ".join(SSH[:-1]), str(lokal), f"{HOST}:{AUSTAUSCH}/{name}"], check=True)
    d = api("POST", "/api/datasets/upload", formular=f"file=@{AUSTAUSCH}/{name};filename={name};type=application/json",
            timeout=600)
    return d["stored_path"]


def chat(nachrichten: list[dict], *, temperatur: float = 0.3, max_tokens: int = 1500, json_modus: bool = False,
         seed: int | None = None, timeout: int = 900, extra: dict | None = None) -> str:
    """Eine Antwort des geladenen Modells, ohne Denkmodus. extra: weitere Felder, z. B. {"use_adapter": False}."""
    body = {"messages": nachrichten, "temperature": temperatur, "max_tokens": max_tokens, "stream": False,
            "enable_thinking": False, **(extra or {})}
    if json_modus:
        body["response_format"] = {"type": "json_object"}
    if seed is not None:
        body["seed"] = seed
    d = api("POST", "/api/inference/chat/completions", body, timeout=timeout)
    try:
        return d["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError) as exc:
        raise ApiFehler(f"unerwartete Antwort: {str(d)[:300]}") from exc

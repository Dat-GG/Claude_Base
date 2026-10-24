"""_machine.py - read this machine's tool / folder locations from ~/.claude/bacon-machine.json.

Purpose : one place for machine paths, so the shared tools carry no hard-coded drive-letter defaults. Keys are the
          tokens the docs write as <key> (studio, projects, standard, ghidra, jdk17, dotnet, ilspycmd, ldplayer, ...).
Usage   : from a script in tools/:            import _machine
          from a script in a tools/ subfolder: sys.path.insert(0, <tools folder>); import _machine
          (set sys.dont_write_bytecode = True before the import: no __pycache__ inside the plugin folder)
            _machine.load()                 -> dict (missing / unreadable / not a JSON object -> {})
            _machine.get(key, default=None) -> raw value (string as stored, e.g. "py -I" for `python`)
            _machine.path(key, default=None)-> value with %VAR% / $VAR / ~ expanded and normalized; empty value -> default
            _machine.require(key, env=None) -> path from env var `env` (wins) or the machine file; exits 2 with
                                               "set <key> in ~/.claude/bacon-machine.json (/setup-machine)" when unset
                                               or the path does not exist
Inputs  : env BACON_MACHINE = path of another JSON file (tests / overrides); else ~/.claude/bacon-machine.json (UTF-8,
          BOM tolerated). The file is created by /setup-machine.
Outputs : nothing written; require() prints one line to stderr and exits 2 on a missing location.
Proven  : 2026-10-23 with ghidra_query.py and mono_decompile.py (BACON_MACHINE temp file + missing-key path).
"""
import json
import os
import sys

FILE_HINT = "~/.claude/bacon-machine.json"
_cache = None


def machine_file():
    override = os.environ.get("BACON_MACHINE")
    if override:
        return os.path.expanduser(override)
    return os.path.join(os.path.expanduser("~"), ".claude", "bacon-machine.json")


def load():
    """The machine file as a dict; {} when missing or invalid. Cached per process."""
    global _cache
    if _cache is None:
        try:
            with open(machine_file(), encoding="utf-8-sig") as fh:
                data = json.load(fh)
            _cache = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            _cache = {}
    return _cache


def get(key, default=None):
    value = load().get(key)
    return default if value is None else value


def path(key, default=None):
    value = load().get(key)
    if not isinstance(value, str) or not value.strip():
        return default
    return os.path.normpath(os.path.expanduser(os.path.expandvars(value.strip())))


def require(key, env=None):
    """Location of `key`: env var `env` first, then the machine file; exit 2 when unset or not on disk."""
    value = os.environ.get(env) if env else None
    source = "env " + env if value else FILE_HINT
    value = os.path.normpath(os.path.expanduser(os.path.expandvars(value))) if value else path(key)
    if not value or not os.path.exists(value):
        where = " (%s from %s does not exist)" % (value, source) if value else ""
        print("set %s in %s (/setup-machine)%s" % (key, FILE_HINT, where), file=sys.stderr)
        sys.exit(2)
    return value

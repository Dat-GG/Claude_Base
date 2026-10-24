r"""Query an already-analyzed Ghidra project (no re-analysis, read-only, 30-75 s per run incl. JVM cold start).

  py -I <tools>/ghidra/ghidra_query.py --project <ghidra-projects>/E2D.gpr --program libEarnToDie2.so \
        --out <dir>/out.c decomp "CarModel::GetWheelRadius" "StoryLevelState::OnExplosion"
  ... syms   "BlendFunc::ADDITIVE" ...          static values at symbols (hex + f32)
  ... asm    0x0062be58 0x005c81c4 ...           whole-function listing around Ghidra addresses
  ... byname "CarModel::GetWheelRadius" ...      listing of functions by exact full name

Replaces hand-written .bat files: arguments go through a pattern file, so commas, quotes and the
`"%~dp0"` trailing-backslash trap (Ghidra exits silently) cannot happen. Java = the JDK 17 shipped with Unity 6.
The first analysis of a binary is a separate, one-time step (see references/engine-native-cpp.md).
Outputs: --out file (decompiled C / values / listing) + <out>.log (full Ghidra log); key log lines are echoed.
The Jython postScripts are copied to a temp script dir for each run, so Jython's `_args$py.class` cache is written
there and never inside the plugin folder.
Locations: Ghidra = env GHIDRA_HOME or key `ghidra`, JDK 17 = env GHIDRA_JDK or key `jdk17` of
~/.claude/bacon-machine.json (tools/_machine.py); missing -> one-line error, exit 2.
Proven: E2D 2026-10-10 (BC46 render / blend research); re-tested 2026-10-21 and 2026-10-22
(`CarModel::GetWheelRadius @005cfdf4`, `BlendFunc::ADDITIVE_PREMULTIPLIED = (1,1)`).
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))   # tools/ (py -I puts only this script's folder on sys.path)
sys.dont_write_bytecode = True               # no __pycache__ inside the plugin folder
import _machine  # noqa: E402
SCRIPTS = {"decomp": "DecompNamed.py", "syms": "DumpSyms.py", "asm": "DumpAsm.py", "byname": "DumpByName.py"}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project", required=True, help="path to <name>.gpr (or project dir + --name)")
    p.add_argument("--name", help="project name when --project is a directory")
    p.add_argument("--program", required=True, help="program inside the project, e.g. libEarnToDie2.so / libil2cpp.so")
    p.add_argument("--out", required=True)
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("mode", choices=sorted(SCRIPTS))
    p.add_argument("items", nargs="+")
    a = p.parse_args()
    # Locations: env GHIDRA_HOME / GHIDRA_JDK win, else keys `ghidra` / `jdk17` of ~/.claude/bacon-machine.json.
    ghidra = _machine.require("ghidra", env="GHIDRA_HOME")
    jdk = _machine.require("jdk17", env="GHIDRA_JDK")

    proj = os.path.abspath(a.project)
    if proj.lower().endswith(".gpr"):
        pdir, pname = os.path.dirname(proj), os.path.splitext(os.path.basename(proj))[0]
    else:
        pdir, pname = proj, a.name
    if not pname:
        sys.exit("--name needed when --project is a directory")
    if os.path.exists(os.path.join(pdir, pname + ".lock")):
        print(f"warn: {pname}.lock exists (Ghidra GUI open on this project?) - read-only query may still work")

    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as tf:
        tf.write("\n".join(a.items) + "\n")
        pat_file = tf.name
    # Jython compiles imported modules (_args.py) to `_args$py.class` next to the source: run from a temp copy.
    script_dir = tempfile.mkdtemp(prefix="ghidra_query_")
    for fn in os.listdir(HERE):
        if fn.endswith(".py") and fn != os.path.basename(__file__):
            shutil.copy2(os.path.join(HERE, fn), script_dir)
    env = dict(os.environ, MAXMEM=os.environ.get("MAXMEM", "12G"))
    env["PATH"] = os.path.join(jdk, "bin") + os.pathsep + env.get("PATH", "")
    cmd = [os.path.join(ghidra, "support", "analyzeHeadless.bat"), pdir, pname, "-process", a.program, "-noanalysis",
           "-readOnly", "-scriptPath", script_dir, "-postScript", SCRIPTS[a.mode], out, "@" + pat_file]
    log = out + ".log"
    try:
        with open(log, "w", encoding="utf-8", errors="replace") as lf:
            r = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=lf, stderr=subprocess.STDOUT, env=env,
                               timeout=a.timeout)
    finally:
        os.unlink(pat_file)
        shutil.rmtree(script_dir, ignore_errors=True)
    tail = open(log, encoding="utf-8", errors="replace").read().splitlines()
    for l in tail:
        if any(k in l for k in ("DecompNamed:", "DumpSyms:", "DumpAsm", "DumpByName:", "ERROR", "Exception", "Traceback")) \
                and "Invalid PNG" not in l:
            print(l.strip())
    if not os.path.exists(out):
        sys.exit(f"no output (exit {r.returncode}); see {log}")
    print(f"-> {out} ({os.path.getsize(out)} bytes), log {log}")


if __name__ == "__main__":
    main()

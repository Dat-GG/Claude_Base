# Shared by the query scripts (Jython 2.7 inside Ghidra): read the pattern list.
# The wrapper passes "@<file>" (one pattern per line) so commas / quotes never go through cmd.exe.
# Usage: `from _args import patterns` in the postScripts; not run directly. Outputs: the pattern list.
import io


def patterns(arg):
    if arg.startswith('@'):
        with io.open(arg[1:], encoding='utf-8') as f:
            return [l.strip() for l in f if l.strip()]
    return [p for p in arg.split(',') if p]

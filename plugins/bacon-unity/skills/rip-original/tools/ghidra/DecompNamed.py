# Ghidra headless postScript: decompile every function whose full name contains one of the patterns.
# Args: <out file> <patterns: "@file" or comma list>. Recovered from BC46 session 2026-10-10 (render / blend research).
# Usage: not run by hand: `py -I <tools>/ghidra/ghidra_query.py ... decomp <items>` passes the args (see its header).
# Outputs: <out file> = "// ==== Class::Method @ addr" + decompiled C per matching function; "DecompNamed: N functions" in the log.
from ghidra.app.decompiler import DecompInterface
from _args import patterns

args = getScriptArgs()
out, pats = args[0], patterns(args[1])
dec = DecompInterface()
dec.openProgram(currentProgram)
n = 0
with open(out, 'w') as f:
    for fn in currentProgram.getFunctionManager().getFunctions(True):
        name = fn.getName(True)
        if not any(p in name for p in pats):
            continue
        r = dec.decompileFunction(fn, 120, monitor)
        f.write('// ==== %s @ %s\n' % (name, fn.getEntryPoint()))
        if r and r.getDecompiledFunction():
            f.write(r.getDecompiledFunction().getC())
        f.write('\n')
        n += 1
print('DecompNamed: %d functions -> %s' % (n, out))

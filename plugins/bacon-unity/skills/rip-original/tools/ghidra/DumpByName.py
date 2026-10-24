# Ghidra headless postScript: instruction listing of functions by exact full name (e.g. "CarModel::GetWheelRadius"),
# call targets resolved. Thunks skipped.
# Args: <out file> <names: "@file" or comma list>. Recovered from BC46 session 2026-10-10.
# Usage: not run by hand: `py -I <tools>/ghidra/ghidra_query.py ... byname <items>` passes the args (see its header).
# Outputs: <out file> = "==== Function @ entry" + instruction listing per exact-name match; "DumpByName:" summary.
from _args import patterns

args = getScriptArgs()
out, names = args[0], set(patterns(args[1]))
listing = currentProgram.getListing()
fm = currentProgram.getFunctionManager()
n = 0
with open(out, 'w') as f:
    for fn in fm.getFunctions(True):
        name = fn.getName(True)
        if name not in names or fn.isThunk():
            continue
        f.write('==== %s @ %s\n' % (name, fn.getEntryPoint()))
        for ins in listing.getInstructions(fn.getBody(), True):
            refs = ''
            for r in ins.getReferencesFrom():
                f2 = fm.getFunctionAt(r.getToAddress())
                if f2 is not None:
                    refs += ' -> ' + f2.getName(True)
            f.write('%s  %s%s\n' % (ins.getAddress(), ins.toString(), refs))
        n += 1
print('DumpByName: %d functions -> %s' % (n, out))

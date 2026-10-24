# Ghidra headless postScript: instruction listing of the whole functions that contain the given addresses,
# with call targets and referenced data values resolved. Use when the decompiler output is wrong / unclear.
# Args: <out file> <addresses: "@file" or comma list of hex, Ghidra addresses incl. image base>.
# Recovered from BC46 session 2026-10-10 (CarModel wheel radius).
# Usage: not run by hand: `py -I <tools>/ghidra/ghidra_query.py ... asm <items>` passes the args (see its header).
# Outputs: <out file> = "==== Function @ entry" + one instruction per line with resolved call / data refs.
from _args import patterns

args = getScriptArgs()
out, addrs = args[0], patterns(args[1])
listing = currentProgram.getListing()
fm = currentProgram.getFunctionManager()
with open(out, 'w') as f:
    for a in addrs:
        fn = fm.getFunctionContaining(toAddr(a))
        if fn is None:
            f.write('no function at %s\n' % a)
            continue
        f.write('==== %s @ %s\n' % (fn.getName(True), fn.getEntryPoint()))
        for ins in listing.getInstructions(fn.getBody(), True):
            refs = ''
            for r in ins.getReferencesFrom():
                to = r.getToAddress()
                f2 = fm.getFunctionAt(to)
                if f2 is not None:
                    refs += ' -> ' + f2.getName(True)
                else:
                    d = listing.getDataAt(to)
                    if d is not None and d.getValue() is not None:
                        refs += ' [%s = %s]' % (to, d.getValue())
            mn = ins.getMnemonicString()
            f.write('%s  %-8s %s%s\n' % (ins.getAddress(), mn, ins.toString()[len(mn):].strip(), refs))
print('DumpAsm -> %s' % out)

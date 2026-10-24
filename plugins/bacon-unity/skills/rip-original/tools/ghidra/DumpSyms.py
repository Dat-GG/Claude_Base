# Ghidra headless postScript: read static values at symbols whose full name contains one of the patterns.
# Prints 4 raw 32-bit words plus their float32 reading (constants, tables, blend modes...).
# Args: <out file> <patterns>. Recovered from BC46 session 2026-10-10 (cocos2d::BlendFunc constants), generalized.
# Usage: not run by hand: `py -I <tools>/ghidra/ghidra_query.py ... syms <items>` passes the args (see its header).
# Outputs: <out file> = one line per symbol: "name @ addr = 4 hex words | f32 4 floats"; "DumpSyms:" summary in the log.
import struct
from _args import patterns

args = getScriptArgs()
out, pats = args[0], patterns(args[1])
mem = currentProgram.getMemory()
n = 0
with open(out, 'w') as f:
    for s in currentProgram.getSymbolTable().getAllSymbols(True):
        name = s.getName(True)
        if name.startswith('PTR_') or not any(p in name for p in pats):
            continue
        a = s.getAddress()
        try:
            words = [mem.getInt(a.add(4 * i)) & 0xffffffff for i in range(4)]
            floats = [struct.unpack('<f', struct.pack('<I', w))[0] for w in words]
            f.write('%s @ %s = %s | f32 %s\n' % (name, a, ' '.join('0x%08x' % w for w in words),
                                                ' '.join('%g' % x for x in floats)))
        except Exception as e:
            f.write('%s @ %s err %s\n' % (name, a, e))
        n += 1
print('DumpSyms: %d symbols -> %s' % (n, out))

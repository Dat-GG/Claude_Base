# Original save files

Goal: put the original and our build in the **same state** (stage, cash, upgrades, unlocks) before measuring.
Always: fresh dated backup of the device save in `<workspace>\Tools\_save\` before any push, restore afterwards, transfer
byte-exact (`device-ldplayer.md`).

---

### Find where the save lives
- Status: ✅ · Cost: 1
- Unity: `shared_prefs/<pkg>.v2.playerprefs.xml` (PlayerPrefs) or a file under `files/`; keys from IL2CPP
  `stringliteral.json`. Native / cocos: `files/*.dat`; the serializer is in the decompile. List:
  `su -c 'ls -la /data/data/<pkg>/files /data/data/<pkg>/shared_prefs'`.

### PlayerPrefs XML (plain)
- Status: ✅ UFD 2026-10-15/16 · Cost: 1
- `py -I Urban_Food_Ripped\Tools\ufd_save_tool.py pull OUT.xml | show [F] | set KEY=VAL… [--file F] | push F`
  (force-stops the game before push). UFD keys were plain property names (encryption helpers present but never called):
  check the call sites before assuming encryption.

### XOR-obfuscated binary save (E2D `profile.dat`)
- Status: ✅ E2D 2026-10-08, fixed 2026-10-13 · Cost: 2
- `py -I E2D_Ripper\Tools\e2d_save_tool.py pull | show | set | push | key`;
  `set --region --leg --cash --day --best-distance --tuning R:m,t,g,b,k,th,tu,p --modes-unlocked 0|1`.
- Key = first 5 chars of the **app's** Android ID, recovered from known plaintext (magic "ed2", version 44, zero high bytes).
  Do not use `settings get secure android_id`: since Android 8 each app gets its own ID (shell `977832fe…`, app key `c7c3b`).
- Format: little-endian, 4-byte alignment with unwritten pads, string = int32 length + bytes, fields gated by
  `if (N < version)`; derived from the serializer in the decompile.
- Pitfalls: `su` sometimes fails right after a force-stop (retry 3×). Keep the corrupted-CRLF example
  `Tools\_save\CORRUPT_crlf_do_not_push_20261013.dat` as a warning.

### Custom serialized `.sav` (HMR)
- 🧪 BC36: keys proven through the string-literal cross-reference (`engine-il2cpp.md` › Names and code › 5. String-literal cross-reference).

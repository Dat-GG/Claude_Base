# When the value is not in any data: measure

Use only after data / code reading failed or cannot contain the value (widget margins, fit mode, font size, feel).
A serialized / code value always beats a measured one; a measured one beats a guess. Tag results `[CONFIRMED]` with the
measurement source (file + frame / time), or `[DEFAULT]` when it is our choice.

### Frame measurement on a reference video
- Status: ✅ DogJump, HexRescue, BC36, BCA27, BC54 · Cost: 1–2
- `/ref-video` (framekit): probe → coarse sheet → fine frames → diff / mask / track / color → numbers with timestamps.
- Font size from video: 53.3 px on a 900-wide frame → 42.7 design px → TMP size 60 (HexRescue).

### Forced resolutions on the emulator (fit mode, anchoring)
- `device-ldplayer.md` › Layout probing.

### Edit-mode render of our scene vs a screenshot of the original
- `engine-il2cpp.md` › Materials (render `Camera.main` to PNG, `GetPixel`), `/playtest` for Play-mode captures.

### User-observed rules
- Status: ✅ BCA18 FishIO · Cost: 3 (user time)
- Nothing extractable: the user plays the original and reports; tag each rule `[CONFIRMED]` (user verified) /
  `[DEFAULT]` / `[TODO]`, expose tuning knobs, verify statistics by simulation (spawn mix by Monte Carlo against a user count
  of 64 / 29 / 7). Update the spec only after the user confirms the feel.

### Human senses
- Sound identity, "does it feel the same": pre-narrow the candidates by measurement, then ask the user to listen / play
  (5 minutes) instead of building a matcher (`assets.md` › Audio).

---
name: port-mechanic
description: Implement or change one game mechanic so it matches the original - spec first, research the original through the reference-researcher agent (parallel for independent questions), update GAME_MECHANICS.md with values + sources + tags, then code, verify against the original, log. Use for any gameplay rule, number, behavior or feel change in a project that follows an original or legacy game.
---

# Port a mechanic

Profile (`.claude/bacon-profile.json`) gives the doc names, `self_test` and `changelog` modes. Rules: `core.md`
(spec first, measure don't guess, cheapest method, minimal-risk change).

## 1. Scope
- One mechanic per pass (e.g. "boost", "crate break", "garage shadow"). Several → split and do them one by one, or
  research them in parallel (step 3) and implement one at a time.
- Out of the approved plan (new system, refactor, `_Project_Base` edit) → propose and wait (plan mode).
- A correction from the user ("almost right, only X and Y") → only X and Y; skip to step 5 with that scope.

## 2. What do we already know
- Read the matching section of the spec (`docs.mechanics`; per game for `multi-game`) and the decision tables D# / Q#. Note which values are already
  `[CONFIRMED]` / `[DATA]` with a source, and which are `[TODO]`, `[DEFAULT]`, `[LD?]` / `[OLD?]` or missing.
- Read the current code of the mechanic (grep the new names; rename map for clone projects).
- Everything needed is confirmed with a source → go to step 4.

## 3. Research the gaps with `reference-researcher`
- Write one precise question per gap: what value / formula / trigger / order, in which situation, and what the code
  currently assumes. Include the spec section and known sources so the agent does not redo them.
- Independent questions → launch several `reference-researcher` agents **in the same message** (parallel). Dependent
  questions → one agent, or sequential.
- Do not read multi-MB decompiled files / rips / scenes in the main session; that is the agent's job. Reading the 20–50
  lines an agent cites, to double-check a key number, is fine.
- Check the answers: each value has a source and a tag; "(inferred)" parts are flagged; contradictions between agents or
  with the spec are resolved (ask a follow-up, or mark `[TODO]` / `[LD?]` / `[OLD?]`).
- Only measurable on the device / in a video → `/ref-video` (or the agent with framekit), LDPlayer per `/rip-original`.

## 4. Spec first
Update `GAME_MECHANICS.md` **before** code: values in original units + conversion, the rule as pseudo-code, source per line,
tag per rule (`[CONFIRMED]`, `[DATA]`, `[DEFAULT]` for our own choice with the reason, `[LD?]` / `[OLD?]` to confirm). Resolved `[TODO]`s
change tag. Deviations from the original (dead features, original bugs not reproduced, branding) go into decisions / Part D;
quirks kept for the feel into Part E.

## 5. Code
- Numbers come from data (generated data, ScriptableObjects) or one constants place, never scattered literals; units
  converted in exactly one place.
- Follow the project's architecture and `core.md` (no per-frame allocations, pooling, physics step rules…). Clone projects:
  new names only (the hook flags original class names).
- Smallest change that matches the spec; mention edge cases.

## 6. Verify
- Compile, console clean.
- `self_test` `full` → `/playtest` the scenario; `runtime-only` → runtime checks yourself, visuals to the user; `none` →
  list what the user should check.
- Compare with the original when the mechanic is measurable: same state, same scripted input, same numbers (telemetry vs
  the device baseline / `/ref-video` measurement). Report the comparison with numbers; say plainly what was not compared.

## 7. Close
- `/log-change` (Nguyên nhân / change / **Kiểm tra** / Files · Docs with the spec section).
- Plan step done → `✅ date`. New open question → plan. New research technique or dead end → `/add-lesson`.

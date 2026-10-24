# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@~/.claude/bacon-standard/standards/core.md
@~/.claude/bacon-standard/standards/bacon-framework.md
@~/.claude/bacon-standard/standards/docs-format.md
{{MODULE_IMPORTS}}

Workflow switches: `.claude/bacon-profile.json` (type `{{TYPE}}`, changelog `{{CHANGELOG}}`, self-test `{{SELF_TEST}}`).

---

## Role (domain)

{{ROLE_DOMAIN}}

## Project environment

- Unity **{{UNITY_VERSION}}**. Rendering = {{RENDER_PIPELINE}}. Color Space = {{COLOR_SPACE}}.
- Unity MCP: {{MCP_LINE}}
- Physics / time: {{PHYSICS_LINE}} (saved to `ProjectSettings/*.asset`: {{SETTINGS_APPLY}}, or File > Save Project).
- Input: {{INPUT_LINE}}
- Orientation: {{ORIENTATION}}. Target: {{TARGET}}.
- Language: C#, namespace **`Bacon`**.

## Project rules (on top of the standard)

- {{PROJECT_RULE}}

## What this is

{{WHAT_THIS_IS}}

- Docs: `{{MECHANICS}}` (rules) · `{{PLAN}}` (phases, decisions, handoff) · `{{CHANGELOG_FILE}}` (history).
- No CLI build / test workflow unless listed here: open in Unity {{UNITY_VERSION}} and play from the Editor.

## Reference sources (read-only, outside the repo)

| What | Where |
|---|---|
| {{REF_WHAT}} | {{REF_WHERE}} |

## Code layout (game layer)

{{CODE_LAYOUT}}

## Editor tools (`Bacon/*` menus)

{{EDITOR_TOOLS}}

## Boot & flow (differences from the base)

{{FLOW}}

## Third-party assets

{{THIRD_PARTY}}

# Skills taken from Unity-Technologies/unity-agent-plugin

Source: https://github.com/Unity-Technologies/unity-agent-plugin @ `ba48956ae8bee4ef8a3ef3d75dec03c16aa5cc89`
(plugin 0.1.6-beta, 2026-10-30). License: Unity Companion License (`LICENSE.md` here): use, modify and distribute only
in connection with content authored under a Unity engine license.

| Our skill | Upstream | Changes |
|---|---|---|
| `skills/ugui` (+ `references/scrollview-setup.md`) | `skills/ui-ugui` | name, description, header note, 2 convention lines → Bacon layout |
| `skills/tmp-fonts` | `skills/optimize-text-mesh-pro` | name, description, header note |

Not taken: `optimize-audio` (every step runs through Unity's `unity-cli eval`), the rest of the plugin. Candidates for
later, **not read yet** (200 KB+ each): `manage-sprite-atlas`, `implement-in-app-purchases`,
`levelplay-unity-integration` (with group 3, release / SDK), `localization`.

Updating: download the new upstream commit, diff the upstream files against the sha above, re-apply the changes listed.

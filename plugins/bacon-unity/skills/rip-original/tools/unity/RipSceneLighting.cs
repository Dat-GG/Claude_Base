// RipSceneLighting.cs - stop URP from adding the realtime sun on top of lightmaps that already contain it.
//
// Purpose : ripped scenes keep a Mixed (Shadowmask) directional light while the baked lightmaps already include the sun, so
//           the city looks washed out. Lightmapped renderers -> rendering layer 1 only, Mixed directional lights ->
//           rendering layer 0 only (dynamic objects); enables "Use Rendering Layers" on the URP assets listed below.
// Usage   : copy into any Editor folder of a URP project, set RenderPipelineAssets (PROJECT CONSTANTS) to the project's URP
//           assets, open the ripped scene, menu Bacon/Import/Fix Rip Scene Lighting (active scene), save the scene.
// Inputs  : the active scene; the URP assets in RenderPipelineAssets (missing paths are skipped silently).
// Outputs : renderingLayerMask changed on renderers / lights, scene marked dirty, m_SupportsLightLayers on the URP assets;
//           Console log "baked renderers N, mixed directional lights M".
// Needs   : URP (UnityEngine.Rendering.Universal); compiles in Assembly-CSharp-Editor.
// Proven  : BC54 (Urban Food Delivery rebuild) 2026-10-16, matched LDPlayer screenshots.
// Origin  : <projects>/BC54_Food_Delivery/BC54_Food_Delivery/BC54_Food_Delivery/Assets/_Project/Scripts/Editor/Import/
//           (copied 2026-10-22, code unchanged).
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering.Universal;

namespace Bacon
{
    /// <summary>
    /// The original lightmaps already contain the sun's direct light, but the scene's Mixed directional light is set to Shadowmask,
    /// so URP adds the realtime sun on top of the lightmap and the city looks washed out. Fix (matches LDPlayer screenshots):
    /// lightmapped renderers go to rendering layer 1 only, the directional light lights rendering layer 0 only (dynamic objects).
    /// Requires "Use Rendering Layers" (light layers) on the URP assets.
    /// </summary>
    public static class RipSceneLighting
    {
        public const uint DynamicLayerMask = 1u;   // rendering layer 0: lit by the realtime sun
        public const uint BakedLayerMask = 2u;     // rendering layer 1: lightmapped city, sun already baked in

        // ---- PROJECT CONSTANTS: the project's URP assets (template defaults of the URP project template) ----
        private static readonly string[] RenderPipelineAssets =
        {
            "Assets/Settings/Mobile_RPAsset.asset",
            "Assets/Settings/PC_RPAsset.asset",
        };

        [MenuItem("Bacon/Import/Fix Rip Scene Lighting (active scene)")]
        public static void FixActiveScene()
        {
            EnableLightLayers();

            int baked = 0;
            foreach (var r in Object.FindObjectsByType<Renderer>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (r.lightmapIndex < 0 || r.lightmapIndex >= 65534) continue;
                r.renderingLayerMask = BakedLayerMask;
                baked++;
            }

            int lights = 0;
            foreach (var l in Object.FindObjectsByType<Light>(FindObjectsInactive.Include, FindObjectsSortMode.None))
            {
                if (l.type != LightType.Directional || l.lightmapBakeType != LightmapBakeType.Mixed) continue;
                l.renderingLayerMask = (int)DynamicLayerMask;
                lights++;
            }

            EditorSceneManager.MarkSceneDirty(EditorSceneManager.GetActiveScene());
            Debug.Log($"[RipSceneLighting] baked renderers {baked}, mixed directional lights {lights}");
        }

        private static void EnableLightLayers()
        {
            foreach (string path in RenderPipelineAssets)
            {
                var asset = AssetDatabase.LoadAssetAtPath<UniversalRenderPipelineAsset>(path);
                if (asset == null) continue;
                var so = new SerializedObject(asset);
                var prop = so.FindProperty("m_SupportsLightLayers");
                if (prop == null || prop.boolValue) continue;
                prop.boolValue = true;
                so.ApplyModifiedPropertiesWithoutUndo();
            }
            AssetDatabase.SaveAssets();
        }
    }
}

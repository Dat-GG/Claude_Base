// RipMaterialConverter.cs - convert the original game's Built-in RP materials (copied from the AssetRipper rip) to URP.
//
// Purpose : Legacy Diffuse / Specular / Self-Illumin -> URP Simple Lit, Standard -> Lit, Transparent / Cutout -> Simple Lit
//           alpha, legacy / mobile particles -> Particles/Unlit; explicit mapping per original shader, safe to re-run.
// Usage   : copy into any Editor folder of a URP project (Assets/_Project/Scripts/Editor/Import/), adjust the two
//           PROJECT CONSTANTS below, then menu Bacon/Import/Convert Rip Materials to URP (and, only for materials converted
//           by the pre-2026-10-16 version, Bacon/Import/Fix Converted Simple Lit Specular).
// Inputs  : every Material under RipRoot whose path contains RipFolderMarker.
// Outputs : the materials are changed in place (shader + properties + keywords); Console log "converted N, skipped M" with
//           the skipped shader names (skybox / UI / already URP / stub shaders: handle those by hand).
// Needs   : URP package (uses UnityEditor.Rendering.Universal.ShaderGUI); compiles in Assembly-CSharp-Editor. With an Editor
//           asmdef, reference Unity.RenderPipelines.Universal.Editor + Runtime.
// Proven  : BC54 (Urban Food Delivery rebuild) 2026-10-16, 103 materials; specular fix the same day.
// Origin  : <projects>/BC54_Food_Delivery/BC54_Food_Delivery/BC54_Food_Delivery/Assets/_Project/Scripts/Editor/Import/
//           (copied 2026-10-22; only the folder constants were made explicit).
using System.Collections.Generic;
using System.Text;
using UnityEditor;
using UnityEditor.Rendering.Universal.ShaderGUI;
using UnityEngine;
using UnityEngine.Rendering;

namespace Bacon
{
    /// <summary>
    /// Converts the original game's Built-in RP materials (copied from the ripped project into */Original/Rip) to URP.
    /// Explicit mapping per original shader so the result is predictable and the tool can be re-run.
    /// </summary>
    public static class RipMaterialConverter
    {
        // ---- PROJECT CONSTANTS: adjust per project ----
        private const string RipRoot = "Assets/_Project";              // search root for materials
        private const string RipFolderMarker = "/Original/Rip/";       // only materials whose path contains this
        // -----------------------------------------------
        private const string SimpleLit = "Universal Render Pipeline/Simple Lit";
        private const string Lit = "Universal Render Pipeline/Lit";
        private const string ParticlesUnlit = "Universal Render Pipeline/Particles/Unlit";

        private enum Surface { Opaque, Cutout, Transparent }
        private enum ParticleBlend { Alpha, Additive }

        [MenuItem("Bacon/Import/Convert Rip Materials to URP")]
        public static void ConvertAll()
        {
            var report = new StringBuilder();
            int converted = 0, skipped = 0;
            foreach (string guid in AssetDatabase.FindAssets("t:Material", new[] { RipRoot }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (!path.Contains(RipFolderMarker)) continue;
                var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (mat == null) continue;
                string from = mat.shader != null ? mat.shader.name : "null";
                if (Convert(mat, from))
                {
                    converted++;
                    EditorUtility.SetDirty(mat);
                }
                else
                {
                    skipped++;
                    report.AppendLine($"skip [{from}] {path}");
                }
            }
            AssetDatabase.SaveAssets();
            Debug.Log($"[RipMaterialConverter] converted {converted}, skipped {skipped}\n{report}");
        }

        private static bool Convert(Material mat, string from)
        {
            switch (from)
            {
                case "Legacy Shaders/Diffuse":
                case "Legacy Shaders/Diffuse Detail":
                case "Legacy Shaders/Reflective/Diffuse":
                    ToSimpleLit(mat, Surface.Opaque, false, false);
                    return true;
                case "Legacy Shaders/Specular":
                    ToSimpleLit(mat, Surface.Opaque, true, false);
                    return true;
                case "Legacy Shaders/Self-Illumin/Diffuse":
                    ToSimpleLit(mat, Surface.Opaque, false, true);
                    return true;
                case "Legacy Shaders/Transparent/Diffuse":
                    ToSimpleLit(mat, Surface.Transparent, false, false);
                    return true;
                case "Legacy Shaders/Transparent/Cutout/Diffuse":
                    ToSimpleLit(mat, Surface.Cutout, false, false);
                    return true;
                case "Standard":
                    ToLit(mat);
                    return true;
                case "Particles/Standard Unlit":
                case "Mobile/Particles/Alpha Blended":
                case "Legacy Shaders/Particles/Alpha Blended":
                    ToParticles(mat, ParticleBlend.Alpha);
                    return true;
                case "Mobile/Particles/Additive":
                case "Legacy Shaders/Particles/Additive (Soft)":
                    ToParticles(mat, ParticleBlend.Additive);
                    return true;
                default:
                    return false; // skybox / UI / already URP / stub shaders: handled separately
            }
        }

        // Reads the Built-in properties before the shader swap (Unity keeps unused properties in the material's saved data).
        private struct Source
        {
            public Texture mainTex, bump, emissionMap;
            public Vector2 scale, offset;
            public Color color, emission;
            public float cutoff, metallic, glossiness;
        }

        private static Source Read(Material mat)
        {
            var s = new Source
            {
                mainTex = mat.HasProperty("_MainTex") ? mat.GetTexture("_MainTex") : null,
                scale = mat.HasProperty("_MainTex") ? mat.GetTextureScale("_MainTex") : Vector2.one,
                offset = mat.HasProperty("_MainTex") ? mat.GetTextureOffset("_MainTex") : Vector2.zero,
                color = mat.HasProperty("_Color") ? mat.GetColor("_Color") : Color.white,
                bump = mat.HasProperty("_BumpMap") ? mat.GetTexture("_BumpMap") : null,
                cutoff = mat.HasProperty("_Cutoff") ? mat.GetFloat("_Cutoff") : 0.5f,
                metallic = mat.HasProperty("_Metallic") ? mat.GetFloat("_Metallic") : 0f,
                glossiness = mat.HasProperty("_Glossiness") ? mat.GetFloat("_Glossiness") : 0f,
                emissionMap = mat.HasProperty("_EmissionMap") ? mat.GetTexture("_EmissionMap") : null,
                emission = mat.HasProperty("_EmissionColor") ? mat.GetColor("_EmissionColor") : Color.black,
            };
            if (mat.HasProperty("_TintColor")) s.color = mat.GetColor("_TintColor") * 2f; // legacy particle tint is 0.5-based
            return s;
        }

        private static void ApplyBase(Material mat, Source s)
        {
            mat.SetTexture("_BaseMap", s.mainTex);
            mat.SetTextureScale("_BaseMap", s.scale);
            mat.SetTextureOffset("_BaseMap", s.offset);
            mat.SetColor("_BaseColor", s.color);
        }

        private static void ToSimpleLit(Material mat, Surface surface, bool specular, bool selfIllum)
        {
            var s = Read(mat);
            mat.shader = Shader.Find(SimpleLit);
            ApplyBase(mat, s);
            mat.SetFloat("_Smoothness", specular ? 0.5f : 0f);
            SetSimpleLitSpecular(mat, specular);
            if (s.bump != null)
            {
                mat.SetTexture("_BumpMap", s.bump);
                mat.EnableKeyword("_NORMALMAP");
            }
            if (selfIllum && s.mainTex != null)
            {
                mat.SetTexture("_EmissionMap", s.mainTex);
                mat.SetColor("_EmissionColor", Color.white);
                mat.EnableKeyword("_EMISSION");
                mat.globalIlluminationFlags = MaterialGlobalIlluminationFlags.BakedEmissive;
            }
            else
            {
                mat.SetColor("_EmissionColor", Color.black);
                mat.DisableKeyword("_EMISSION");
            }
            SetSurface(mat, surface, s.cutoff);
            BaseShaderGUI.SetMaterialKeywords(mat, SimpleLitGUI.SetMaterialKeywords);
        }

        /// <summary>
        /// Repairs Simple Lit materials converted before the specular fix (2026-10-16): URP's `_SpecularHighlights` is the
        /// SpecularSource enum (0 = specular on, 1 = none), the old code wrote the inverse, so every Legacy Diffuse got
        /// highlights and transparent ones also got "preserve specular" (car shadow quads rendered white).
        /// Specular materials are the ones converted with smoothness 0.5.
        /// </summary>
        [MenuItem("Bacon/Import/Fix Converted Simple Lit Specular")]
        public static void FixConvertedSimpleLit()
        {
            int fixedCount = 0;
            foreach (string guid in AssetDatabase.FindAssets("t:Material", new[] { RipRoot }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (!path.Contains(RipFolderMarker)) continue;
                var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (mat == null || mat.shader == null || mat.shader.name != SimpleLit) continue;

                bool specular = mat.GetFloat("_Smoothness") > 0.01f;
                SetSimpleLitSpecular(mat, specular);
                if (mat.GetTexture("_EmissionMap") == null)
                {
                    mat.SetColor("_EmissionColor", Color.black);
                    mat.DisableKeyword("_EMISSION");
                }
                BaseShaderGUI.SetMaterialKeywords(mat, SimpleLitGUI.SetMaterialKeywords);
                EditorUtility.SetDirty(mat);
                fixedCount++;
            }
            AssetDatabase.SaveAssets();
            Debug.Log($"[RipMaterialConverter] fixed Simple Lit specular on {fixedCount} materials");
        }

        private static void ToLit(Material mat)
        {
            var s = Read(mat);
            float mode = mat.HasProperty("_Mode") ? mat.GetFloat("_Mode") : 0f; // 0 opaque, 1 cutout, 2 fade, 3 transparent
            mat.shader = Shader.Find(Lit);
            ApplyBase(mat, s);
            mat.SetFloat("_Metallic", s.metallic);
            mat.SetFloat("_Smoothness", s.glossiness);
            if (s.bump != null)
            {
                mat.SetTexture("_BumpMap", s.bump);
                mat.EnableKeyword("_NORMALMAP");
            }
            if (s.emissionMap != null || s.emission.maxColorComponent > 0.001f)
            {
                mat.SetTexture("_EmissionMap", s.emissionMap);
                mat.SetColor("_EmissionColor", s.emission);
                mat.EnableKeyword("_EMISSION");
            }
            SetSurface(mat, mode >= 2f ? Surface.Transparent : mode >= 1f ? Surface.Cutout : Surface.Opaque, s.cutoff);
        }

        private static void ToParticles(Material mat, ParticleBlend blend)
        {
            var s = Read(mat);
            mat.shader = Shader.Find(ParticlesUnlit);
            ApplyBase(mat, s);
            mat.SetFloat("_Surface", 1f);
            mat.SetFloat("_Blend", blend == ParticleBlend.Additive ? 2f : 0f); // URP BlendMode: 0 Alpha, 2 Additive
            mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
            mat.SetFloat("_DstBlend", (float)(blend == ParticleBlend.Additive ? BlendMode.One : BlendMode.OneMinusSrcAlpha));
            mat.SetFloat("_ZWrite", 0f);
            mat.SetOverrideTag("RenderType", "Transparent");
            mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            mat.renderQueue = (int)RenderQueue.Transparent;
        }

        private static void SetSimpleLitSpecular(Material mat, bool on)
        {
            mat.SetFloat("_SpecularHighlights", (float)(on ? SimpleLitGUI.SpecularSource.SpecularTextureAndColor
                                                            : SimpleLitGUI.SpecularSource.NoSpecular));
            mat.SetFloat("_BlendModePreserveSpecular", 0f); // legacy alpha blend never kept specular at full strength
        }

        private static void SetSurface(Material mat, Surface surface, float cutoff)
        {
            mat.SetFloat("_Surface", surface == Surface.Transparent ? 1f : 0f);
            mat.SetFloat("_AlphaClip", surface == Surface.Cutout ? 1f : 0f);
            mat.SetFloat("_Cutoff", cutoff);
            if (surface == Surface.Cutout) mat.EnableKeyword("_ALPHATEST_ON");
            else mat.DisableKeyword("_ALPHATEST_ON");

            if (surface == Surface.Transparent)
            {
                mat.SetFloat("_Blend", 0f);
                mat.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                mat.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                mat.SetFloat("_ZWrite", 0f);
                mat.SetOverrideTag("RenderType", "Transparent");
                mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
                mat.renderQueue = (int)RenderQueue.Transparent;
            }
            else
            {
                mat.SetFloat("_SrcBlend", (float)BlendMode.One);
                mat.SetFloat("_DstBlend", (float)BlendMode.Zero);
                mat.SetFloat("_ZWrite", 1f);
                mat.SetOverrideTag("RenderType", surface == Surface.Cutout ? "TransparentCutout" : "Opaque");
                mat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");
                mat.renderQueue = surface == Surface.Cutout ? (int)RenderQueue.AlphaTest : -1;
            }
        }
    }
}

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEditorInternal;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace Bacon
{
    /// <summary>
    /// Build size audit (bacon-unity `/size-audit`): reads the last build report (`Library/LastBuild.buildreport`), then
    /// opens the enabled build scenes read-only to attribute packed MB to GameObject branches, and lists import / player
    /// settings that inflate the build. Writes `Library/SizeAudit/size_audit.md` (+ `assets.tsv`; the previous run is kept
    /// as `assets_prev.tsv` and the report shows the delta). Editor only, never saves a scene or an asset.
    /// Why: BC54 (2026-10-27) — a 225 MB APK where 77 MB were static batching meshes, 24 MB inactive challenge content,
    /// 15 MB unused vehicles, 10 MB pack demo assets in Resources; none of it showed in a folder-size view.
    /// </summary>
    public static class BuildSizeAudit
    {
        private const string ReportPath = "Library/LastBuild.buildreport";
        private const string OutDir = "Library/SizeAudit";
        private const string CombinedMesh = "Built-in Mesh: Combined Mesh";
        private const long BranchMinBytes = 300_000; // branches below this are not listed
        private const int TopAssets = 60;
        private const int MaxImportHints = 25;

        [MenuItem("Bacon/Build/Size Audit (last build)")]
        public static void Run()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
            {
                Debug.LogError("[SizeAudit] stop Play mode first");
                return;
            }
            BuildReport report = LoadReport();
            if (report == null)
            {
                Debug.LogError("[SizeAudit] no " + ReportPath + ": build the player once (any build), then run again");
                return;
            }

            Dictionary<string, long> size = PackedSizes(report, out Dictionary<string, long> byType);
            if (size.Count == 0)
            {
                // An incremental build that reused the previous data files lists no packed assets (BC54, Unity 6.3).
                Debug.LogError("[SizeAudit] the last build report lists no packed assets: the build reused cached data. Rebuild with Build Profiles > Build dropdown > Clean Build, then run again. " +
                               "Previous audit files kept.");
                return;
            }
            var md = new StringBuilder();
            Summary(md, report, size);
            Delta(md, size);
            Breakdown(md, size, byType);
            HashSet<string> sceneDeps = ResourcesSection(md, size);
            Scenes(md, size, sceneDeps);
            ImportHints(md, size);
            PlayerHints(md);

            Directory.CreateDirectory(OutDir);
            string tsv = Path.Combine(OutDir, "assets.tsv");
            if (File.Exists(tsv) && new FileInfo(tsv).Length > 0) File.Copy(tsv, Path.Combine(OutDir, "assets_prev.tsv"), true);
            File.WriteAllLines(tsv, size.OrderByDescending(kv => kv.Value).Select(kv => kv.Value + "\t" + kv.Key));
            string mdPath = Path.Combine(OutDir, "size_audit.md");
            File.WriteAllText(mdPath, md.ToString());
            Debug.Log("[SizeAudit] report: " + Path.GetFullPath(mdPath));
        }

        // ------------------------------------------------------------------ build report

        private static BuildReport LoadReport()
        {
            if (!File.Exists(ReportPath)) return null;
            foreach (Object o in InternalEditorUtility.LoadSerializedFileAndForget(ReportPath))
                if (o is BuildReport r) return r;
            return null;
        }

        private static Dictionary<string, long> PackedSizes(BuildReport report, out Dictionary<string, long> byType)
        {
            var size = new Dictionary<string, long>();
            byType = new Dictionary<string, long>();
            foreach (PackedAssets pa in report.packedAssets)
            foreach (PackedAssetInfo c in pa.contents)
            {
                string path = string.IsNullOrEmpty(c.sourceAssetPath) ? "(unnamed)" : c.sourceAssetPath;
                Add(size, path, (long)c.packedSize);
                Add(byType, c.type != null ? c.type.Name : "?", (long)c.packedSize);
            }
            return size;
        }

        private static void Summary(StringBuilder md, BuildReport report, Dictionary<string, long> size)
        {
            BuildSummary s = report.summary;
            md.AppendLine("# Build size audit");
            md.AppendLine();
            md.AppendLine($"- Build: {s.platform}, {s.result}, ended {s.buildEndedAt.ToLocalTime():yyyy-MM-dd HH:mm}, output `{s.outputPath}`");
            if (File.Exists(s.outputPath)) md.AppendLine($"- Output file: **{Mb(new FileInfo(s.outputPath).Length)} MB**");
            md.AppendLine($"- Packed assets (uncompressed data): **{Mb(size.Values.Sum())} MB**, {size.Count} entries");
            md.AppendLine("- The report describes that build: changes made after it are not in these numbers.");
            md.AppendLine();
        }

        private static void Delta(StringBuilder md, Dictionary<string, long> size)
        {
            string prev = Path.Combine(OutDir, "assets.tsv");
            if (File.Exists(prev) && new FileInfo(prev).Length == 0) prev = Path.Combine(OutDir, "assets_prev.tsv"); // left empty by an older version
            if (!File.Exists(prev)) return;
            var old = new Dictionary<string, long>();
            foreach (string line in File.ReadAllLines(prev))
            {
                string[] p = line.Split('\t');
                if (p.Length == 2 && long.TryParse(p[0], out long v)) old[p[1]] = v;
            }
            md.AppendLine("## Change since the previous audit");
            md.AppendLine($"- Total: {Mb(old.Values.Sum())} → {Mb(size.Values.Sum())} MB");
            var folders = new Dictionary<string, long>();
            foreach (var kv in old) Add(folders, Folder(kv.Key), -kv.Value);
            foreach (var kv in size) Add(folders, Folder(kv.Key), kv.Value);
            foreach (var kv in folders.Where(kv => Math.Abs(kv.Value) >= BranchMinBytes).OrderBy(kv => kv.Value))
                md.AppendLine($"- {(kv.Value > 0 ? "+" : "")}{Mb(kv.Value)} MB `{kv.Key}`");
            md.AppendLine();
        }

        private static void Breakdown(StringBuilder md, Dictionary<string, long> size, Dictionary<string, long> byType)
        {
            md.AppendLine("## By type");
            foreach (var kv in byType.OrderByDescending(kv => kv.Value).Take(12)) md.AppendLine($"- {Mb(kv.Value)} MB {kv.Key}");
            long combined = size.Where(kv => kv.Key.StartsWith(CombinedMesh)).Sum(kv => kv.Value);
            int count = size.Keys.Count(k => k.StartsWith(CombinedMesh));
            if (count > 0)
                md.AppendLine($"- **{Mb(combined)} MB in {count} `Combined Mesh` = static batching made at build time** (in no folder; see Scenes → static vertices)");
            md.AppendLine();

            md.AppendLine("## By folder (top 30)");
            var folders = new Dictionary<string, long>();
            foreach (var kv in size) if (!kv.Key.StartsWith(CombinedMesh)) Add(folders, Folder(kv.Key), kv.Value);
            foreach (var kv in folders.OrderByDescending(kv => kv.Value).Take(30)) md.AppendLine($"- {Mb(kv.Value)} MB `{kv.Key}`");
            md.AppendLine();

            md.AppendLine($"## Top {TopAssets} assets");
            foreach (var kv in size.Where(kv => !kv.Key.StartsWith(CombinedMesh)).OrderByDescending(kv => kv.Value).Take(TopAssets))
                md.AppendLine($"- {Mb(kv.Value)} MB `{kv.Key}`");
            md.AppendLine();
        }

        // ------------------------------------------------------------------ Resources

        /// <summary>Everything under a Resources folder ships; list what scenes do not use (pack demos, samples).</summary>
        private static HashSet<string> ResourcesSection(StringBuilder md, Dictionary<string, long> size)
        {
            string[] scenes = BuildScenes();
            var sceneDeps = new HashSet<string>(AssetDatabase.GetDependencies(scenes, true));
            var files = AssetDatabase.GetAllAssetPaths()
                .Where(p => p.StartsWith("Assets/") && p.Contains("/Resources/") && !p.Contains("/Editor/") && !AssetDatabase.IsValidFolder(p))
                .ToList();

            md.AppendLine("## Resources (always in the build)");
            md.AppendLine("MB pulled by each Resources file that no build scene uses (shared deps counted in each line):");
            foreach (var group in files.GroupBy(p => p.Substring(0, p.IndexOf("/Resources/", StringComparison.Ordinal) + 10)))
            {
                long total = Sum(AssetDatabase.GetDependencies(group.ToArray(), true).Where(d => !sceneDeps.Contains(d)), size);
                if (total < BranchMinBytes) continue;
                md.AppendLine($"- **{Mb(total)} MB** `{group.Key}`");
                foreach (string f in group)
                {
                    long own = Sum(AssetDatabase.GetDependencies(f, true).Where(d => !sceneDeps.Contains(d)), size);
                    if (own >= BranchMinBytes) md.AppendLine($"  - {Mb(own)} MB `{f.Substring(group.Key.Length + 1)}`");
                }
            }
            md.AppendLine();
            return sceneDeps;
        }

        // ------------------------------------------------------------------ scenes

        /// <summary>
        /// Packed MB that only one GameObject branch uses (roots, and the children of heavy roots), its inactive share and
        /// its static-batched vertices. Inactive objects still ship with the scene; only active static renderers are batched.
        /// </summary>
        private static void Scenes(StringBuilder md, Dictionary<string, long> size, HashSet<string> sceneDeps)
        {
            md.AppendLine("## Scenes (branches that pull MB nothing else uses)");
            var opened = new List<Scene>();
            try
            {
                var branches = new List<(string scene, Transform t, int depth, HashSet<string> deps)>();
                foreach (string path in BuildScenes())
                {
                    Scene scene = SceneManager.GetSceneByPath(path);
                    if (!scene.isLoaded)
                    {
                        scene = EditorSceneManager.OpenScene(path, OpenSceneMode.Additive);
                        opened.Add(scene);
                    }
                    foreach (GameObject root in scene.GetRootGameObjects())
                    {
                        branches.Add((scene.name, root.transform, 0, Deps(root)));
                        foreach (Transform child in root.transform) branches.Add((scene.name, child, 1, Deps(child.gameObject)));
                    }
                }

                // an asset is "only here" when no other branch of the same depth (and no Resources file) uses it
                var resourcesDeps = new HashSet<string>(AssetDatabase.GetDependencies(
                    AssetDatabase.GetAllAssetPaths().Where(p => p.Contains("/Resources/") && !p.Contains("/Editor/")).ToArray(), true));
                foreach (int depth in new[] { 0, 1 })
                {
                    var users = new Dictionary<string, int>();
                    foreach (var b in branches.Where(b => b.depth == depth))
                        foreach (string d in b.deps) users[d] = users.TryGetValue(d, out int n) ? n + 1 : 1;
                    md.AppendLine(depth == 0 ? "### Roots" : "### Children (exclusive among their siblings and all other children)");
                    foreach (var b in branches.Where(b => b.depth == depth)
                                 .Select(b => (b, only: Sum(b.deps.Where(d => users[d] == 1 && !resourcesDeps.Contains(d)), size)))
                                 .OrderByDescending(x => x.only))
                    {
                        Transform t = b.b.t;
                        int all = 0, inactive = 0, staticVerts = 0;
                        foreach (Transform x in t.GetComponentsInChildren<Transform>(true))
                        {
                            all++;
                            if (!x.gameObject.activeInHierarchy) inactive++;
                        }
                        foreach (MeshFilter mf in t.GetComponentsInChildren<MeshFilter>(false))
                        {
                            var r = mf.GetComponent<MeshRenderer>();
                            if (mf.sharedMesh != null && r != null && r.enabled
                                && GameObjectUtility.AreStaticEditorFlagsSet(mf.gameObject, StaticEditorFlags.BatchingStatic))
                                staticVerts += mf.sharedMesh.vertexCount;
                        }
                        if (b.only < BranchMinBytes && staticVerts < 100_000) continue;
                        string state = !t.gameObject.activeInHierarchy ? " **(inactive)**" : inactive > all / 2 ? $" ({inactive}/{all} objects inactive)" : "";
                        md.AppendLine($"- {Mb(b.only)} MB only-here · static verts {staticVerts:N0} · `{b.b.scene}/{HierarchyPath(t)}`{state}");
                        foreach (var a in b.b.deps.Where(d => users[d] == 1 && !resourcesDeps.Contains(d) && size.ContainsKey(d))
                                     .OrderByDescending(d => size[d]).Take(4).Where(d => size[d] >= BranchMinBytes))
                            md.AppendLine($"  - {Mb(size[a])} MB `{a}`");
                    }
                    md.AppendLine();
                }
            }
            finally
            {
                foreach (Scene s in opened)
                    if (s.isLoaded) EditorSceneManager.CloseScene(s, true);
            }
        }

        private static HashSet<string> Deps(GameObject go)
        {
            var set = new HashSet<string>();
            foreach (Object d in EditorUtility.CollectDependencies(new Object[] { go }))
            {
                if (d == null || !EditorUtility.IsPersistent(d)) continue;
                string p = AssetDatabase.GetAssetPath(d);
                if (!string.IsNullOrEmpty(p) && !p.EndsWith(".unity")) set.Add(p);
            }
            return set;
        }

        // ------------------------------------------------------------------ settings

        private static void ImportHints(StringBuilder md, Dictionary<string, long> size)
        {
            md.AppendLine($"## Import settings worth a look (biggest {MaxImportHints} assets in the build)");
            int lines = 0;
            foreach (var kv in size.OrderByDescending(kv => kv.Value))
            {
                if (kv.Value < 500_000 || lines >= MaxImportHints) break;
                int before = md.Length;
                AssetImporter imp = AssetImporter.GetAtPath(kv.Key);
                if (imp is TextureImporter ti)
                {
                    TextureImporterPlatformSettings android = ti.GetPlatformTextureSettings("Android");
                    int max = android.overridden ? android.maxTextureSize : ti.maxTextureSize;
                    ti.GetSourceTextureWidthAndHeight(out int w, out int h);
                    int shipped = Math.Min(max, Math.Max(w, h));
                    if (shipped >= 2048 || ti.textureCompression == TextureImporterCompression.CompressedHQ)
                        md.AppendLine($"- {Mb(kv.Value)} MB texture {shipped}px, {ti.textureType}, {ti.textureCompression}{(android.overridden ? ", Android " + android.format : "")}, mips {ti.mipmapEnabled}: `{kv.Key}`");
                }
                else if (imp is ModelImporter mi)
                {
                    int shapes = AssetDatabase.LoadAllAssetsAtPath(kv.Key).OfType<Mesh>().Sum(m => m.blendShapeCount);
                    if (shapes > 0 || mi.meshCompression == ModelImporterMeshCompression.Off)
                        md.AppendLine($"- {Mb(kv.Value)} MB model, blendshapes {shapes} (import {mi.importBlendShapes}), mesh compression {mi.meshCompression}: `{kv.Key}`");
                }
                else if (imp is AudioImporter ai && ai.defaultSampleSettings.compressionFormat == AudioCompressionFormat.PCM)
                    md.AppendLine($"- {Mb(kv.Value)} MB audio PCM (uncompressed): `{kv.Key}`");
                else if (kv.Key.EndsWith(".ttf", StringComparison.OrdinalIgnoreCase) || kv.Key.EndsWith(".otf", StringComparison.OrdinalIgnoreCase))
                    md.AppendLine($"- {Mb(kv.Value)} MB font file (dynamic TMP fallback / Font asset): `{kv.Key}`");
                if (md.Length > before) lines++;
            }
            md.AppendLine();
        }

        private static void PlayerHints(StringBuilder md)
        {
            NamedBuildTarget target = NamedBuildTarget.FromBuildTargetGroup(EditorUserBuildSettings.selectedBuildTargetGroup);
            md.AppendLine("## Player settings");
            md.AppendLine($"- Target {target.TargetName}, development build {EditorUserBuildSettings.development}");
            md.AppendLine($"- Managed stripping {PlayerSettings.GetManagedStrippingLevel(target)}, strip engine code {PlayerSettings.stripEngineCode}");
            md.AppendLine($"- IL2CPP code generation {PlayerSettings.GetIl2CppCodeGeneration(target)}, compiler {PlayerSettings.GetIl2CppCompilerConfiguration(target)}");
            md.AppendLine($"- Strip unused mesh components {PlayerSettings.stripUnusedMeshComponents}");
            if (target == NamedBuildTarget.Android)
                md.AppendLine($"- Android: architectures {PlayerSettings.Android.targetArchitectures}, texture subtarget {EditorUserBuildSettings.androidBuildSubtarget}, app bundle {EditorUserBuildSettings.buildAppBundle}, split binary {PlayerSettings.Android.splitApplicationBinary}");
            string ps = File.ReadAllText("ProjectSettings/ProjectSettings.asset");
            int i = ps.IndexOf("m_BuildTarget: " + EditorUserBuildSettings.activeBuildTarget, StringComparison.Ordinal);
            if (i >= 0)
            {
                int j = ps.IndexOf("m_StaticBatching:", i, StringComparison.Ordinal);
                if (j >= 0) md.AppendLine("- Static batching " + ps.Substring(j + 17, 2).Trim());
            }
            md.AppendLine();
        }

        // ------------------------------------------------------------------ helpers

        private static string[] BuildScenes() => EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();

        private static string Folder(string path)
        {
            if (path.StartsWith(CombinedMesh)) return CombinedMesh;
            string[] p = path.Split('/');
            return p.Length > 3 ? string.Join("/", p, 0, Math.Min(p.Length - 1, 4)) : path;
        }

        private static string HierarchyPath(Transform t)
        {
            string p = t.name;
            for (Transform x = t.parent; x != null; x = x.parent) p = x.name + "/" + p;
            return p;
        }

        private static long Sum(IEnumerable<string> paths, Dictionary<string, long> size) =>
            paths.Distinct().Sum(p => size.TryGetValue(p, out long v) ? v : 0);

        private static void Add(Dictionary<string, long> d, string k, long v) => d[k] = d.TryGetValue(k, out long o) ? o + v : v;

        private static string Mb(long bytes) => (bytes / 1e6).ToString("F1");
    }
}

// Install / repair / uninstall for one game, without UI, so the command line (tests) and the window share it.
// Every file it creates, replaces or removes is recorded in a manifest with a backup of what was there before, so
// Uninstall puts back exactly the files the game and Archipelago folders had (byte for byte).
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;

namespace APSetup;

sealed class ManifestEntry
{
    public string Target { get; set; }      // absolute path we wrote or removed
    public string Backup { get; set; }      // backup of the file that was there before, or null if there was none
}

sealed class Manifest
{
    public string Game { get; set; }
    public string GameDir { get; set; }     // the folders this install went into (Uninstall works on these)
    public string ApDir { get; set; }
    public List<ManifestEntry> Entries { get; set; } = [];
    public List<string> CreatedDirs { get; set; } = [];
}

sealed class Installer
{
    public readonly GameProfile Profile;
    public readonly string GameDir, ApDir, Payload, StateDir;
    public readonly List<string> Log = [];
    Manifest _manifest;

    // gameDir: the Mass Effect Legendary Edition folder; apDir: Archipelago's folder; payload: the folder holding this
    // game's release files; stateDir: where the manifest and backups live (%LOCALAPPDATA%\MassEffectAPSetup\<Id>).
    public Installer(GameProfile profile, string gameDir, string apDir, string payload, string stateDir)
    {
        Profile = profile;
        GameDir = gameDir;
        ApDir = apDir;
        Payload = payload;
        StateDir = stateDir;
    }

    public static string DefaultStateDir(GameProfile profile) =>
        Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MassEffectAPSetup", profile.Id);

    public string Root => Path.Combine(GameDir, "Game", Profile.GameFolder);
    public string Win64 => Path.Combine(Root, "Binaries", "Win64");
    public string AsiDir => Path.Combine(Win64, "ASI");
    public string BioGame => Path.Combine(Root, "BioGame");
    public string ModTarget => Path.Combine(BioGame, "DLC", Profile.DlcName);
    public string WorldTarget => Path.Combine(ApDir, "custom_worlds", Profile.Apworld);
    public string GameExe => Path.Combine(Win64, Profile.Exe);
    public string BinkProxy => Path.Combine(Win64, "bink2w64.dll");
    public string BinkOriginal => Path.Combine(Win64, "bink2w64_original.dll");
    string ManifestPath => Path.Combine(StateDir, "manifest.json");

    public bool GameFound => File.Exists(GameExe);
    public bool ArchipelagoFound => File.Exists(Path.Combine(ApDir, "ArchipelagoLauncher.exe"));
    public bool Installed => File.Exists(ManifestPath);

    public static string Hash(string path) => File.Exists(path) ? Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))) : null;
    static string Product(string path) => File.Exists(path) ? FileVersionInfo.GetVersionInfo(path).ProductName ?? "" : "";

    // ------------------------------------------------------------------ manifest
    Manifest LoadManifest() =>
        File.Exists(ManifestPath) ? JsonSerializer.Deserialize<Manifest>(File.ReadAllText(ManifestPath)) : new Manifest { Game = Profile.Id };

    // Written to a temporary file and swapped in, so an interrupted write never leaves a half-written record.
    void SaveManifest()
    {
        var temp = ManifestPath + ".tmp";
        File.WriteAllText(temp, JsonSerializer.Serialize(_manifest, new JsonSerializerOptions { WriteIndented = true }));
        File.Move(temp, ManifestPath, true);
    }

    static bool SameFolder(string a, string b) =>
        string.Equals(Path.GetFullPath(a).TrimEnd('\\'), Path.GetFullPath(b).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase);

    ManifestEntry Find(string target) =>
        _manifest.Entries.FirstOrDefault(e => string.Equals(e.Target, Path.GetFullPath(target), StringComparison.OrdinalIgnoreCase));

    // Record `target` before it changes: the first time, back up what is there (or note that nothing is).
    void Track(string target)
    {
        target = Path.GetFullPath(target);
        if (Find(target) != null) return;
        string backup = null;
        if (File.Exists(target))
        {
            backup = Path.Combine(StateDir, "backup", $"{_manifest.Entries.Count:D5}_{Path.GetFileName(target)}");
            Directory.CreateDirectory(Path.GetDirectoryName(backup));
            File.Copy(target, backup, true);
        }
        _manifest.Entries.Add(new ManifestEntry { Target = target, Backup = backup });
        SaveManifest();   // saved after every new entry: an install that stops half way can still be undone
    }

    void EnsureDir(string dir)
    {
        var missing = new List<string>();
        for (var d = Path.GetFullPath(dir); d != null && !Directory.Exists(d); d = Path.GetDirectoryName(d)) missing.Add(d);
        foreach (var d in Enumerable.Reverse(missing))
        {
            Directory.CreateDirectory(d);
            _manifest.CreatedDirs.Add(d);
        }
    }

    void Place(string target, string source)
    {
        Track(target);
        EnsureDir(Path.GetDirectoryName(target));
        File.Copy(source, target, true);
    }

    void PlaceBytes(string target, byte[] bytes)
    {
        Track(target);
        EnsureDir(Path.GetDirectoryName(target));
        File.WriteAllBytes(target, bytes);
    }

    void Remove(string target)
    {
        if (!File.Exists(target)) return;
        Track(target);
        File.Delete(target);
    }

    // Undo our change to one file now (a movie the player chose to keep after skipping it earlier).
    void Revert(string target)
    {
        var entry = Find(target);
        if (entry == null) return;
        if (entry.Backup != null) File.Copy(entry.Backup, entry.Target, true);
        else if (File.Exists(entry.Target)) File.Delete(entry.Target);
        _manifest.Entries.Remove(entry);
        SaveManifest();
    }

    // ------------------------------------------------------------------ status
    public string State(string payloadFile, string target) =>
        !File.Exists(target) ? "not installed" : Hash(payloadFile) == Hash(target) ? "installed (this version)" : "installed (different version)";

    public string LoaderState()
    {
        if (!File.Exists(BinkOriginal))
            return Profile.Loader == LoaderMode.ApLoader ? "not installed (Install adds the AP ASI Loader)"
                : "MISSING: in ME3Tweaks Mod Manager pick " + Profile.ModManagerGame + ", Tools > ASI Manager, install " +
                  string.Join(" and ", Profile.RequiredAsis.Select(a => a.Name)) + " (this adds the loader)";
        if (Product(BinkProxy) == "AP ASI Loader")
            return "AP ASI Loader, " + (Hash(Path.Combine(Payload, "bink2w64.dll")) == Hash(BinkProxy) ? "this version" : "different version (Repair updates it)");
        return $"{(Product(BinkProxy) is var p && p.Length > 0 ? p : "another loader")} (e.g. Mod Manager's)";
    }

    public IEnumerable<string> MissingRequirements()
    {
        if (Profile.Loader == LoaderMode.RequireExisting && !File.Exists(BinkOriginal)) yield return "the ASI loader (bink2w64 proxy)";
        foreach (var (pattern, name) in Profile.RequiredAsis)
            if (!Directory.Exists(AsiDir) || Directory.GetFiles(AsiDir, pattern).Length == 0) yield return name;
    }

    public string ModVersionInstalled()
    {
        if (Profile.ModVersionFile == null) return Directory.Exists(ModTarget) ? "installed" : null;
        var file = Path.Combine(ModTarget, Profile.ModVersionFile);
        return File.Exists(file) ? File.ReadLines(file).FirstOrDefault()?.Trim() : Directory.Exists(ModTarget) ? "unknown (older than 0.2.4)" : null;
    }

    public string ModVersionPayload()
    {
        var file = Path.Combine(Payload, Profile.ModFolder, Profile.DlcName, Profile.ModVersionFile ?? "-");
        return File.Exists(file) ? File.ReadLines(file).FirstOrDefault()?.Trim() : null;
    }

    // Everything Launch needs: the files Install puts down, unchanged since, and Mod Manager's one-time ASIs.
    public List<string> LaunchProblems()
    {
        var problems = new List<string>();
        if (!GameFound) problems.Add("Mass Effect Legendary Edition not found (set its folder on page 1).");
        if (!ArchipelagoFound) problems.Add("Archipelago not found (set its folder on page 1).");
        if (problems.Count > 0) return problems;
        if (Hash(Path.Combine(Payload, Profile.Apworld)) != Hash(WorldTarget)) problems.Add("The Archipelago world is missing or a different version: Install / Repair.");
        foreach (var asi in Profile.AsiFiles)
            if (Hash(Path.Combine(Payload, "ASI", asi)) != Hash(Path.Combine(AsiDir, asi))) problems.Add($"{asi} is missing or a different version: Install / Repair.");
        if (Profile.ModVersionFile != null && ModVersionInstalled() != ModVersionPayload()) problems.Add("The mod is missing or a different version: Install / Repair.");
        var source = Path.Combine(Payload, Profile.ModFolder, Profile.DlcName);
        if (Directory.GetFiles(source, "*", SearchOption.AllDirectories).Any(f =>
                new FileInfo(Path.Combine(ModTarget, Path.GetRelativePath(source, f))) is var t && (!t.Exists || t.Length != new FileInfo(f).Length)))
            problems.Add("The mod's files are missing or changed: Install / Repair.");
        if (Profile.Loader == LoaderMode.ApLoader && (!File.Exists(BinkOriginal) || !File.Exists(BinkProxy)))
            problems.Add("The ASI loader (bink2w64.dll) is missing: Install / Repair adds it.");
        foreach (var missing in MissingRequirements()) problems.Add($"{missing} is missing: {LoaderState()}.");
        return problems;
    }

    // ------------------------------------------------------------------ install
    public sealed class Options
    {
        public HashSet<string> KeepMovies = new(StringComparer.OrdinalIgnoreCase);   // OptionalMovies files to leave as they are
    }

    // Archipelago programs started from this Archipelago folder (the Launcher, and the clients it runs). A running
    // Launcher cannot load an apworld replaced under it (zipimport keeps the old file's directory: "Error -5").
    public static List<string> RunningArchipelago(string apDir)
    {
        var running = new List<string>();
        var root = Path.GetFullPath(apDir).TrimEnd('\\') + "\\";
        foreach (var process in Process.GetProcesses())
        {
            try
            {
                if (process.ProcessName.StartsWith("Archipelago", StringComparison.OrdinalIgnoreCase)
                    && process.MainModule?.FileName is { } exe && exe.StartsWith(root, StringComparison.OrdinalIgnoreCase))
                    running.Add(process.ProcessName);
            }
            catch (Exception) { }   // a process that ended, or one we may not inspect
            finally { process.Dispose(); }
        }
        return running;
    }

    void RequireArchipelagoClosed(string apDir)
    {
        var running = RunningArchipelago(apDir);
        if (running.Count > 0)
            throw new InvalidOperationException($"Close the Archipelago Launcher and its clients first ({string.Join(", ", running.Distinct())}): " +
                                                "a running Launcher cannot load the new world until it is restarted.");
    }

    public void Install(Options options)
    {
        if (!ArchipelagoFound) throw new InvalidOperationException("Set the Archipelago folder on page 1.");
        if (!GameFound) throw new InvalidOperationException("Set the Mass Effect Legendary Edition folder on page 1.");
        RequireArchipelagoClosed(ApDir);
        Directory.CreateDirectory(StateDir);
        _manifest = LoadManifest();
        if (_manifest.GameDir != null && !SameFolder(_manifest.GameDir, GameDir) || _manifest.ApDir != null && !SameFolder(_manifest.ApDir, ApDir))
            throw new InvalidOperationException($"{Profile.Title} is installed into other folders ({_manifest.GameDir}, {_manifest.ApDir}): Uninstall first.");
        _manifest.GameDir = Path.GetFullPath(GameDir);
        _manifest.ApDir = Path.GetFullPath(ApDir);
        SaveManifest();

        if (Profile.Loader == LoaderMode.ApLoader) InstallApLoader();
        Place(WorldTarget, Path.Combine(Payload, Profile.Apworld));
        foreach (var pattern in Profile.OldAsiPatterns)
            if (Directory.Exists(AsiDir))
                foreach (var old in Directory.GetFiles(AsiDir, pattern))
                    if (!Profile.AsiFiles.Contains(Path.GetFileName(old), StringComparer.OrdinalIgnoreCase)) Remove(old);
        foreach (var asi in Profile.AsiFiles) Place(Path.Combine(AsiDir, asi), Path.Combine(Payload, "ASI", asi));
        Log.Add("World and bridge installed.");

        var source = Path.Combine(Payload, Profile.ModFolder, Profile.DlcName);
        // The DLC folder ends up exactly as in the payload: files not in it are removed (backed up).
        if (Directory.Exists(ModTarget))
            foreach (var file in Directory.GetFiles(ModTarget, "*", SearchOption.AllDirectories))
                if (!File.Exists(Path.Combine(source, Path.GetRelativePath(ModTarget, file)))) Remove(file);
        foreach (var file in Directory.GetFiles(source, "*", SearchOption.AllDirectories))
            Place(Path.Combine(ModTarget, Path.GetRelativePath(source, file)), file);

        foreach (var (movie, _) in Profile.OptionalMovies)
        {
            var target = Path.Combine(BioGame, "Movies", movie);
            if (options.KeepMovies.Contains(movie)) Revert(target);
            else Place(target, Path.Combine(Payload, Profile.ModFolder, "BASEGAME", "Movies", movie));
        }

        WriteToc();
        SaveManifest();
        Log.Add("Mod installed.");
        foreach (var missing in MissingRequirements())
            Log.Add($"Still needed before playing: {missing}. {LoaderState()}.");
    }

    // The mod's file table, as Mod Manager's AutoTOC writes it (LegendaryExplorerCore TOCCreator).
    void WriteToc()
    {
        if (Profile.Toc == TocMode.DlcToc)
        {
            using var toc = LegendaryExplorerCore.Unreal.TOCCreator.CreateDLCTOCForDirectory(ModTarget, LegendaryExplorerCore.Packages.MEGame.LE2);
            PlaceBytes(Path.Combine(ModTarget, "PCConsoleTOC.bin"), toc.ToArray());
        }
        else
            PlaceBytes(Path.Combine(BioGame, "PCConsoleTOC.bin"), Le1Toc(BioGame));
    }

    // LE1 has one TOC for the game: every BioGame file plus the DLC_MOD files that override them (by mount priority).
    // AutoTOC also lists the TOC itself (BioGame\PCConsoleTOC.bin at its final size), which TOCCreator leaves out, so
    // that entry is added: the result then matches AutoTOC's file for the same folder (checked on a live install).
    public static byte[] Le1Toc(string bioGame)
    {
        using var basic = LegendaryExplorerCore.Unreal.TOCCreator.CreateBasegameTOCForDirectory(bioGame, LegendaryExplorerCore.Packages.MEGame.LE1);
        basic.Position = 0;
        var entries = new LegendaryExplorerCore.Unreal.TOCBinFile(basic).GetAllEntries().Select(e => (e.name, e.size)).ToList();
        const string self = @"BioGame\PCConsoleTOC.bin";
        entries.RemoveAll(e => e.name.Equals(self, StringComparison.OrdinalIgnoreCase));
        byte[] Build(int selfSize)
        {
            using var toc = LegendaryExplorerCore.Unreal.TOCCreator.CreateTOCForEntries([.. entries, (self, selfSize)]);
            return toc.ToArray();
        }
        return Build(Build(0).Length);   // the size field is fixed-width, so the length does not depend on its value
    }

    // Ours (AP ASI Loader) and Mod Manager's LEBinkProxy both replace bink2w64.dll and keep the real RAD DLL as
    // bink2w64_original.dll. Ours goes in only where no loader is present; another loader is never touched.
    void InstallApLoader()
    {
        var payload = Path.Combine(Payload, "bink2w64.dll");
        if (!File.Exists(payload)) return;   // a payload without our loader: Mod Manager's must be used
        if (File.Exists(BinkOriginal))
        {
            // ours (update it), or none left in front of the RAD DLL (put ours back); another loader is left alone
            if (!File.Exists(BinkProxy) || Product(BinkProxy) == "AP ASI Loader") Place(BinkProxy, payload);
            return;
        }
        if (!Product(BinkProxy).Contains("Bink"))
            throw new InvalidOperationException($"{Profile.Title}'s bink2w64.dll is not the game's own (RAD Bink) file, so the ASI loader was not installed. Verify the game files in Steam/EA and try again.");
        Place(BinkOriginal, BinkProxy);
        Place(BinkProxy, payload);
    }

    // ------------------------------------------------------------------ uninstall
    public void Uninstall()
    {
        if (!Installed) throw new InvalidOperationException($"Nothing to uninstall: no install record in {StateDir}.");
        _manifest = LoadManifest();
        RequireArchipelagoClosed(_manifest.ApDir ?? ApDir);   // the folder the install went into, not the one selected now
        foreach (var entry in Enumerable.Reverse(_manifest.Entries))
        {
            if (entry.Backup != null)
            {
                Directory.CreateDirectory(Path.GetDirectoryName(entry.Target));
                File.Copy(entry.Backup, entry.Target, true);
            }
            else if (File.Exists(entry.Target)) File.Delete(entry.Target);
        }
        foreach (var dir in Enumerable.Reverse(_manifest.CreatedDirs))
            if (Directory.Exists(dir) && !Directory.EnumerateFileSystemEntries(dir).Any()) Directory.Delete(dir);
        Directory.Delete(StateDir, true);
        Log.Add("Removed: every file is back as it was before Install.");
    }
}

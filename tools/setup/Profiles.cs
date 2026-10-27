// What differs between the games: folder and file names, how the mod gets its file table, which ASI loader rules apply.
// Each game's payload sits in a folder named after its Id next to the exe (ME1\..., ME2\...).
namespace APSetup;

enum TocMode
{
    DlcToc,        // LE2/LE3: the DLC folder carries its own PCConsoleTOC.bin
    Le1Basegame,   // LE1: one TOC for the whole game, BioGame\PCConsoleTOC.bin, with the DLC_MOD files listed (AutoTOC's job)
}

enum LoaderMode
{
    ApLoader,       // install our own AP ASI Loader (bink2w64 proxy) where no loader is present (ME2)
    RequireExisting // only check: the loader and RequiredAsis come from Mod Manager's one-time ASI step (ME1)
}

sealed class GameProfile
{
    public string Id, Title, GameFolder, Exe, ProcessName, DlcName, ModFolder, Apworld, Client, OptionsResource, ModManagerGame;
    public string[] AsiFiles = [];          // payload ASI folder files -> Binaries\Win64\ASI
    public string[] OldAsiPatterns = [];    // older copies of our ASI to remove (backed up) on install, e.g. LE1APBridge-v10.asi
    public (string Pattern, string Name)[] RequiredAsis = [];   // RequireExisting: ASIs Mod Manager provides
    public (string File, string Label)[] OptionalMovies = [];   // payload BASEGAME\Movies files the player may skip
    public string ModVersionFile;           // the mod's version file in the DLC folder (null: none)
    public TocMode Toc;
    public LoaderMode Loader;
    public string SaveNote;                 // shown on the Options page

    public static readonly GameProfile ME1 = new()
    {
        Id = "ME1", Title = "Mass Effect 1", GameFolder = "ME1", Exe = "MassEffect1.exe", ProcessName = "MassEffect1",
        DlcName = "DLC_MOD_ArchipelagoME1", ModFolder = "ArchipelagoME1", Apworld = "mass_effect_le1.apworld",
        Client = "Mass Effect LE1 Client", OptionsResource = "options-me1.json", ModManagerGame = "LE1",
        AsiFiles = ["LE1APBridge.asi", "LE1APBridge.checks.tsv"], OldAsiPatterns = ["LE1APBridge*.asi"],
        RequiredAsis = [("LE1AutoloadEnabler*.asi", "LE1 Autoload Enabler")],
        OptionalMovies = [("GLO_01_Relay.bik", "Skip the mass relay jump video"), ("UCW_Loading_Flyby.bik", "Skip the FTL flyby video")],
        ModVersionFile = "ArchipelagoME1.version", Toc = TocMode.Le1Basegame, Loader = LoaderMode.RequireExisting,
        SaveNote = "No save import is needed for Mass Effect 1: start a new career with the mod installed. The client binds the " +
                   "career to your seed the first time it connects (a career from before 0.2.4: type /bind in the client once).",
    };

    public static readonly GameProfile ME2 = new()
    {
        Id = "ME2", Title = "Mass Effect 2", GameFolder = "ME2", Exe = "MassEffect2.exe", ProcessName = "MassEffect2",
        DlcName = "DLC_MOD_ArchipelagoME2", ModFolder = "ArchipelagoME2", Apworld = "mass_effect_le2.apworld",
        Client = "Mass Effect LE2 Client", OptionsResource = "options-me2.json", ModManagerGame = "LE2",
        AsiFiles = ["LE2APBridge.asi"], Toc = TocMode.DlcToc, Loader = LoaderMode.ApLoader,
        SaveNote = "No ME1 save is needed for ME2. The mod skips the Genesis comic, and the Archipelago client writes the six " +
                   "ME1 History choices into your new career the first time it connects (an impossible romance falls back to none).",
    };

    public static readonly GameProfile[] All = [ME1, ME2];
}

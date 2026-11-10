from dataclasses import dataclass

from Options import Choice, DefaultOnToggle, OptionGroup, PerGameCommonOptions, Range, Toggle


class FragmentsTotal(Range):
    """How many Prothean Beacon Fragments are shuffled into the item pool."""

    display_name = "Beacon Fragments in Pool"
    range_start = 1
    range_end = 12
    default = 6


class FragmentsRequired(Range):
    """How many Prothean Beacon Fragments unlock Ilos. Lowered to the pool size if it is larger."""

    display_name = "Beacon Fragments Required"
    range_start = 1
    range_end = 12
    default = 4


class RequiredSquadSize(Range):
    """How many squadmates logic expects before landing on a mission world (Eden Prime and the Citadel excepted)."""

    display_name = "Required Squad Size"
    range_start = 0
    range_end = 2
    default = 2


class MakoShuffled(Toggle):
    """Shuffle the M35 Mako into the item pool. When off, the Mako is available from the start.

    Until it arrives you can't land on Therum, Feros, Noveria, Virmire, Asteroid X57 or any uncharted planet, so turning
    this on gates nearly everything behind one item. Derelict freighters are boarded on foot."""

    display_name = "Shuffle the Mako"


class HumanSquadAtCitadel(Toggle):
    """On: Kaidan and Ashley are not items. The first Citadel arrival recruits both as in the vanilla game, and logic
    counts them once you reach the Citadel. Off: they are items like Garrus, Wrex, Tali and Liara."""

    display_name = "Kaidan and Ashley Join at the Citadel"


class BringDownTheSky(DefaultOnToggle):
    """Include the Bring Down the Sky content (Asteroid X57)."""

    display_name = "Include Bring Down the Sky"


class Codexsanity(Choice):
    """Codex pages are checks: unlocking a page sends it.

    story: pages from the Citadel, the story planets and squadmate conversations on the Normandy (79).
    full: also Normandy crew and terminals, uncharted worlds and side-assignment transmissions (104).
    Pages the story gives on its own are not checks. Pages that can be missed for good hold no progression items."""

    display_name = "Codexsanity"
    option_off = 0
    option_story = 1
    option_full = 2
    default = 2


class Journalsanity(Choice):
    """Journal entries are checks: each quest's first entry (Started) and its completion (Completed). A story choice can
    skip a completion (a failed assignment), so completions only hold filler.

    story: Citadel, story planet and squadmate quests. full: also uncharted-world assignments."""

    display_name = "Journalsanity"
    option_off = 0
    option_story = 1
    option_full = 2
    default = 2


class Containersanity(Choice):
    """Containers that need no Decryption (crates, kits, ammo packs, malfunctioning objects...) are checks: opening one
    sends it. Vanilla loot stays inside.

    with_drops: each container also counts once per treasure roll it makes (crates 3, kits 2, ...), all sent on open."""

    display_name = "Containersanity"
    option_off = 0
    option_on = 1
    option_with_drops = 2
    default = 1


class AidStations(DefaultOnToggle):
    """Aid Stations (medi-gel refills) that need no Decryption are checks: using one sends it."""

    display_name = "Aid Stations"


class UnlockContainers(DefaultOnToggle):
    """Containers and Aid Stations locked behind Decryption open like plain ones (no skill, no minigame), and become
    checks under Containersanity / Aid Stations (179 more)."""

    display_name = "Unlock Containers"


class UsefulShare(Range):
    """Percent of the free slots (those left after progression that may hold useful items) that get a useful item:
    gear, a Random Upgrade or Experience, picked at random by the weights below. The rest get filler (mostly credits).
    A share, so it follows how many checks the other options turn on."""

    display_name = "Useful Item Share"
    range_start = 0
    range_end = 100
    default = 55


class GearWeight(Range):
    """Weight of gear among useful items: one manufacturer's weapon, armor, bio-amp or omni-tool line each. Every
    category is represented; about one in twenty is Spectre gear. Gear arrives at a level that climbs from I to X as
    you collect it (Spectre gear is always X). At most 227 gear items: past that, the other weights share the rest."""

    display_name = "Gear Weight"
    range_start = 0
    range_end = 100
    default = 50


class UpgradeWeight(Range):
    """Weight of Random Upgrades (a weapon, ammo, armor or grenade mod at the current gear level) among useful items."""

    display_name = "Random Upgrade Weight"
    range_start = 0
    range_end = 100
    default = 25


class ExperienceWeight(Range):
    """Weight of Experience among useful items. Each one gives the squad XP scaled to its level, like a quest reward
    (Experience Size). Needs the LE1APExtras ASI (installed with the bridge); without it, Experience items wait until it
    is installed."""

    display_name = "Experience Weight"
    range_start = 0
    range_end = 100
    default = 25


class ExperienceSize(Choice):
    """How much XP one Experience item gives: the game's quest reward of that size at the squad's level (minor: about a
    fifth of a level early on, main_plot: about a whole level early on, a quarter of one near level 50)."""

    display_name = "Experience Size"
    option_minor_quest = 0
    option_medium_quest = 1
    option_major_quest = 2
    option_main_plot = 3
    default = 2


class FinishedMissionChecks(Choice):
    """Eden Prime, Therum, Virmire and Asteroid X57 close for good once their mission is finished, so checks left behind
    there are lost. Feros and Noveria close in part: afterwards only Zhu's Hope and Port Hanshan can be revisited.

    no_progression: their containers hold no progression items: this game's gear, upgrades and filler, and other games'
    filler. Leaving one behind can cost gear, never progress.
    filler_only: they hold filler only, so nothing useful can be lost.
    any_item: they can hold anything; collect everything there before finishing those missions.
    Codex pages only found there never hold progression items (missable codex pages); filler_only makes them filler."""

    display_name = "Finished Mission Checks"
    option_filler_only = 0
    option_any_item = 1
    option_no_progression = 2
    default = 2


class IlosUsefulItems(DefaultOnToggle):
    """Landing on Ilos starts the finale, with no way back. Ilos never holds this game's progression items (other
    games' items can be there).

    On: Ilos can hold this game's gear and upgrades. Off: only filler and other games' items."""

    display_name = "Gear on Ilos"


class ShopSlots(Range):
    """Archipelago Items for sale at each merchant (ten merchants: Normandy, Citadel, Noveria, Feros, Virmire), a few
    hundred credits each. Buying one sends its item. The slots appear in a shop's stock the first time you visit it, so
    connect the client before your first shop visit. Commander Rentola's stock on the Normandy (there only for a short
    while after Virmire) holds filler only; the Virmire camp follows Finished Mission Checks."""

    display_name = "Shop Slots"
    range_start = 0
    range_end = 5
    default = 3


class InfiniteSprint(DefaultOnToggle):
    """Sprinting (storming) never runs out of stamina. Needs the LE1APBridge ASI v11 or newer (v9 and v10 leave
    Shepard out of breath)."""

    display_name = "Infinite Sprint"


@dataclass
class MassEffectLE1Options(PerGameCommonOptions):
    fragments_total: FragmentsTotal
    fragments_required: FragmentsRequired
    required_squad_size: RequiredSquadSize
    mako_shuffled: MakoShuffled
    human_squad_at_citadel: HumanSquadAtCitadel
    bring_down_the_sky: BringDownTheSky
    codexsanity: Codexsanity
    journalsanity: Journalsanity
    containersanity: Containersanity
    aid_stations: AidStations
    unlock_containers: UnlockContainers
    finished_mission_checks: FinishedMissionChecks
    ilos_useful_items: IlosUsefulItems
    shop_slots: ShopSlots
    useful_share: UsefulShare
    gear_weight: GearWeight
    upgrade_weight: UpgradeWeight
    experience_weight: ExperienceWeight
    experience_size: ExperienceSize
    infinite_sprint: InfiniteSprint


# Options Creator presets (the defaults are the "recommended" setup).
options_presets = {
    "Story Focus": {
        "codexsanity": "story",
        "journalsanity": "story",
        "containersanity": "off",
        "aid_stations": False,
        "shop_slots": 1,
        "useful_share": 45,
    },
    "Completionist": {
        "fragments_total": 8,
        "fragments_required": 6,
        "mako_shuffled": True,
        "codexsanity": "full",
        "journalsanity": "full",
        "containersanity": "with_drops",
        "aid_stations": True,
        "unlock_containers": True,
        "shop_slots": 5,
        "useful_share": 75,
    },
}

option_groups = [
    OptionGroup("Goal", [FragmentsTotal, FragmentsRequired]),
    OptionGroup("Logic", [RequiredSquadSize, MakoShuffled, HumanSquadAtCitadel, BringDownTheSky]),
    OptionGroup("Checks", [Codexsanity, Journalsanity, Containersanity, AidStations, UnlockContainers, FinishedMissionChecks,
                            IlosUsefulItems, ShopSlots]),
    OptionGroup("Items", [UsefulShare, GearWeight, UpgradeWeight, ExperienceWeight, ExperienceSize]),
    OptionGroup("Quality of Life", [InfiniteSprint]),
]

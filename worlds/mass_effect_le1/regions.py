from __future__ import annotations

import re
from typing import TYPE_CHECKING

from BaseClasses import Item, ItemClassification, Location, LocationProgressType, Region
from rule_builder.options import OptionFilter
from rule_builder.rules import Has, HasAll, HasFromList, Rule, True_
from rule_builder.field_resolvers import FromOption, FromWorldAttr
from worlds.generic.Rules import add_item_rule

from . import data, squad_talk, uncharted
from .containers import CONTAINERS
from .data import Region as R
from .items import MassEffectLE1Item
from .options import MakoShuffled, RequiredSquadSize

if TYPE_CHECKING:
    from .world import MassEffectLE1World


class MassEffectLE1Location(Location):
    game = data.GAME_NAME


HAS_SQUAD: Rule = HasFromList(*data.SQUAD, count=FromOption(RequiredSquadSize))
HAS_MAKO: Rule = Has(data.MAKO) | OptionFilter(MakoShuffled, False)
HAS_FRAGMENTS: Rule = Has(data.FRAGMENT, count=FromWorldAttr("fragments_required"))
VIRMIRE_PAIR: Rule = HasAll("Kaidan Alenko", "Ashley Williams")  # D4: the bomb choice needs both


def _mission(world_region: R) -> Rule:
    """Galaxy-map access to a mission world: its coordinates, a squad, and the Mako."""
    return Has(data.COORDINATES[world_region]) & HAS_SQUAD & HAS_MAKO


ENTRANCES: dict[R, Rule] = {
    R.CITADEL: True_(),  # D3: Act 1 starts on first landing
    R.EDEN_PRIME: Has(data.COORDINATES[R.EDEN_PRIME]),  # tutorial world, assumed solo-able (R2/R4)
    R.THERUM: _mission(R.THERUM),
    R.FEROS: _mission(R.FEROS),
    R.NOVERIA: _mission(R.NOVERIA),
    R.VIRMIRE: _mission(R.VIRMIRE) & VIRMIRE_PAIR,
    R.ASTEROID_X57: _mission(R.ASTEROID_X57),
    R.ILOS: HAS_FRAGMENTS & Has(data.EVENT_VIRMIRE) & HAS_SQUAD & HAS_MAKO,  # D5, D9
    R.UNCHARTED: Has(data.EVENT_ACT1) & HAS_MAKO,  # owner decision 2026-10-10: uncharted content after Act 1
}


def location_included(world: MassEffectLE1World, name: str, loc: data.LocationData) -> bool:
    """Whether this seed has the location: its region exists and its codexsanity tier is on (never a codex page the
    story gives on its own, AUTOMATIC_CODEX)."""
    if loc.region is R.ASTEROID_X57 and not world.options.bring_down_the_sky:
        return False
    if loc.codex is not None:
        if name in AUTOMATIC_CODEX:
            return False
        level = world.options.codexsanity.value
        return level == 2 or (level == 1 and loc.codex == "story")
    if loc.journal is not None:
        level = world.options.journalsanity.value
        return level == 2 or (level == 1 and loc.journal == "story")
    if loc.shop_slot is not None:
        return loc.shop_slot < world.options.shop_slots.value
    if loc.locked and not world.options.unlock_containers:
        return False
    if loc.container == "station":
        return bool(world.options.aid_stations)
    if loc.container == "container":
        return world.options.containersanity.value >= 1
    if loc.container == "drop":
        return world.options.containersanity.value == 2
    return True


# Eden Prime, Therum, Virmire and Asteroid X57 close once finished (Therum and Virmire through GateOverride F1402/F699;
# their levels never check the done bools, so reopening would replay the mission). Codex pages set only inside these
# missions; a new career's achievement rewards (BIOA_NOR10_01_DS1 GAME_START) can also set some, which logic does not
# count on.
CLOSING_MISSIONS = (R.EDEN_PRIME, R.THERUM, R.VIRMIRE, R.ASTEROID_X57)
MISSION_ONLY_CODEX = frozenset({
    "Codex: Aliens: Non-Council Races: Geth",  # Eden Prime
    'Codex: Weapons, Armor and Equipment: Kinetic Barriers ("Shields")',  # Eden Prime or the end of Therum
    "Codex: Aliens: Council Races: Salarians: Culture",
    "Codex: Aliens: Council Races: Salarians: Government",
    "Codex: Aliens: Council Races: Salarians: Military Doctrine",
})

# Feros and Noveria can be revisited once finished, but only partly. After the Thorian, Feros streams only Zhu's Hope
# (BIOA_WAR00's PostThorian state, these chunks); after Benezia, the road to Peak 15 and Peak 15 itself are closed.
FEROS_OPEN_CHUNKS = frozenset({
    "BIOA_WAR20_00", "BIOA_WAR20_01", "BIOA_WAR20_02", "BIOA_WAR20_03", "BIOA_WAR20_03A", "BIOA_WAR20_03B",
    "BIOA_WAR20_03E", "BIOA_WAR20_04", "BIOA_WAR20_04C", "BIOA_WAR20_05", "BIOA_WAR20_06", "BIOA_WAR20_07",
    "BIOA_WAR20_08", "BIOA_WAR20_09", "BIOA_WAR20_10", "BIOA_WAR20_10A", "BIOA_WAR20_14",
})
NOVERIA_CLOSED_CHUNK = re.compile(r"BIOA_ICE(25|50|60)_")
_PACKAGE_SUFFIX = re.compile(r"_(DSG|DS\d|PLC|ART|LAY|SND)$")


def _container_chunks() -> dict[str, str]:
    """Container, drop-slot and Aid Station location name -> its level chunk (package name without its suffix)."""
    chunks = {}
    for entry in CONTAINERS:
        chunk = _PACKAGE_SUFFIX.sub("", entry.key.split(".", 1)[0].upper())
        chunks[entry.name] = chunk
        for roll in range(2, entry.drops + 1):
            chunks[f"{entry.name} (Item {roll})"] = chunk
    return chunks


CONTAINER_CHUNKS = _container_chunks()


def closed_after_mission(name: str, loc: data.LocationData) -> bool:
    """A Feros or Noveria container in a part of the planet that is closed once its mission is finished."""
    chunk = CONTAINER_CHUNKS.get(name)
    if chunk is None:
        return False
    if loc.region is R.FEROS:
        return chunk not in FEROS_OPEN_CHUNKS
    return loc.region is R.NOVERIA and NOVERIA_CLOSED_CHUNK.match(chunk) is not None


# Codex pages by how they are obtained (the Missable column of docs/ME1_codex_entries.md). Pages the story gives on its
# own are never locations; pages that can be missed for good hold no progression items (any game's filler or useful).
AUTOMATIC_CODEX = frozenset({
    "Codex: Aliens: Council Races: Asari",  # the Council meeting
    "Codex: Aliens: Council Races: Salarians",
    "Codex: Aliens: Non-Council Races: Krogan",  # the first Citadel investigation
    "Codex: Aliens: Non-Council Races: Quarians",
    "Codex: Citadel and Galactic Government: Citadel",
    "Codex: Citadel and Galactic Government: Citadel Council",  # Avina, or Udina sending you to the Tower
    "Codex: Aliens: Non-Sapient Creatures: Husks",  # Eden Prime
    "Codex: Ships and Vehicles: Sovereign",  # main-mission conversations
    "Codex: Aliens: Council Races: Salarians: Special Tasks Group",  # a story transmission
    "Codex: Aliens: Extinct Races: Protheans: Cipher",
    "Codex: Aliens: Non-Council Races: Geth: Armatures",  # main-mission encounters
    "Codex: Aliens: Non-Council Races: Geth: Hoppers",
    "Codex: Citadel and Galactic Government: Citadel Station: Statistics",
    "Codex: Ships and Vehicles: Space Combat: Trans-Relay Assaults",
    "Codex: Ships and Vehicles: Weapons: Javelin",
})
MISSABLE_CODEX = frozenset({
    'Codex: Weapons, Armor and Equipment: Kinetic Barriers ("Shields")',  # Eden Prime, or the end of Therum
    "Codex: Aliens: Non-Council Races: Geth",  # Eden Prime
    "Codex: Aliens: Council Races: Salarians: Culture",  # Virmire
    "Codex: Aliens: Council Races: Salarians: Government",
    "Codex: Aliens: Council Races: Salarians: Military Doctrine",
    # Joker's prologue talk (nor10_joker_dlg) plays only while int 13 is 10101 and bool 3214 is unset, which the open
    # start leaves in place until Udina's office on the first Citadel visit sets 3214.
    "Codex: Humanity and the Systems Alliance: Systems Alliance",
    "Codex: Humanity and the Systems Alliance: Timeline",
    "Codex: Ships and Vehicles: FTL Drive",  # only in Adams' first conversation
    "Codex: Ships and Vehicles: Military Ship Classifications",
    "Codex: Ships and Vehicles: Starships: Carriers",  # only on the intimidate branch of its event
    "Codex: Aliens: Council Races: Asari: Biology",  # Liara's romance
    # Liara's talks need bool 4388 Grounded unset; docking at the Citadel with Therum, Feros, Noveria and Virmire done
    # plays the grounding (BIOA_STA70_02ground, F837), which nothing undoes
    "Codex: Aliens: Council Races: Asari: Government",
    "Codex: Aliens: Council Races: Asari: Religion",
    "Codex: Aliens: Extinct Races: Protheans: Beacon",
    "Codex: Aliens: Non-Council Races: Quarians: Religion",  # Tali's third talk, only while her geth quest is open
    "Codex: Aliens: Council Races: Turians: Religion",  # Garrus's Paragon or Renegade points
    # Kaidan, Ashley and Wrex can die on Virmire
    "Codex: Aliens: Council Races: Salarians: Biology",
    "Codex: Planets and Locations: Stations: Gagarin Station",
    "Codex: Technology: Biotics: Biotic Amps",
    "Codex: Technology: Biotics: Life as a Biotic",
    "Codex: Technology: Biotics: Training",
    "Codex: Humanity and the Systems Alliance: Systems Alliance: Military Doctrine",
    "Codex: Ships and Vehicles: Space Combat: Planetary Assaults",
    "Codex: Aliens: Non-Council Races: Krogan: Biology",
    "Codex: Aliens: Non-Council Races: Krogan: Culture",
    "Codex: Aliens: Non-Council Races: Krogan: Military Doctrine",
})


def closes_with_mission(name: str, loc: data.LocationData) -> bool:
    """Left behind for good when its mission ends: a closing mission's containers, shop slots and mission-only codex
    pages, and containers in the closed parts of Feros and Noveria."""
    if loc.region in CLOSING_MISSIONS:
        return loc.container is not None or loc.shop_slot is not None or name in MISSION_ONLY_CODEX
    return closed_after_mission(name, loc)


# Citadel quests whose NPCs are only there while the Normandy is grounded (Keeler: F1381 Grounded and not completed;
# the rioters: F1403 Grounded and the escape not over). The grounding plays on docking at the Citadel with Therum,
# Feros, Noveria and Virmire done; leaving the Citadel ends the window.
GROUNDED_QUESTS = frozenset({
    "Citadel: Negotiator's Request: Started", "Citadel: Negotiator's Request: Completed",
    "Citadel: Our Own Worst Enemy: Started", "Citadel: Our Own Worst Enemy: Completed",
})


def missable(name: str) -> bool:
    """A check that can be missed for good (MISSABLE_CODEX, GROUNDED_QUESTS): holds no progression item of any game."""
    return name in MISSABLE_CODEX or name in GROUNDED_QUESTS


def container_holds_no_progression(world: MassEffectLE1World, loc: data.LocationData) -> bool:
    """A container or treasure-roll check under containers_no_progression: holds no progression item of any game (some
    containers turn out missing or unopenable)."""
    return bool(world.options.containers_no_progression) and loc.container in ("container", "drop")


def no_progression_rule(world: MassEffectLE1World, name: str, loc: data.LocationData) -> bool:
    """Gets the no_progression_item_allowed rule: a check on a planet only a morality transmission opens, or a check
    that closes with its mission under finished_mission_checks no_progression (a missable check has its own)."""
    if location_excluded(world, name, loc) or missable(name):
        return False
    return uncharted.location_needs_morality(name) or (
        world.options.finished_mission_checks == world.options.finished_mission_checks.option_no_progression
        and closes_with_mission(name, loc))


def no_progression_item_allowed(world: MassEffectLE1World, item: Item) -> bool:
    """Whether a no_progression_rule location may hold this item: this world's items but its progression, and other
    players' filler."""
    if item.player == world.player:
        return not item.advancement
    return item.excludable


def missable_item_allowed(item: Item) -> bool:
    """Whether a missable check may hold this item: any game's filler or useful item, never progression."""
    return not item.advancement


def holds_no_progression(world: MassEffectLE1World, name: str, loc: data.LocationData) -> bool:
    """Never holds this world's progression: filler only (location_excluded), no_progression_rule, a missable check,
    or container_holds_no_progression."""
    return (location_excluded(world, name, loc) or no_progression_rule(world, name, loc) or missable(name)
            or container_holds_no_progression(world, loc))


def location_excluded(world: MassEffectLE1World, name: str, loc: data.LocationData) -> bool:
    """Filler only: a story choice can skip it, a squadmate quest needs a choice (squad_talk.TalkGate.choice), its
    planet's landing condition is unverified, or it closes with its mission (finished_mission_checks: filler_only)."""
    if loc.excluded or uncharted.location_unverified(name):
        return True
    if (gate := squad_talk.TALK_GATES.get(name)) is not None and gate.choice and loc.codex is None:
        return True
    return (world.options.finished_mission_checks == world.options.finished_mission_checks.option_filler_only
            and closes_with_mission(name, loc))


def no_return_item_allowed(world: MassEffectLE1World, item: Item) -> bool:
    """Whether a location in data.NO_RETURN_REGIONS may hold this item: any other player's item, this world's filler,
    and this world's useful items when ilos_useful_items is on; never this world's progression."""
    if item.player != world.player:
        return True
    if item.advancement:
        return False
    return bool(world.options.ilos_useful_items) or not item.useful


def create_regions(world: MassEffectLE1World) -> None:
    regions = {r: Region(r.value, world.player, world.multiworld) for r in R}
    if not world.options.bring_down_the_sky:
        del regions[R.ASTEROID_X57]
    world.multiworld.regions += regions.values()

    normandy = regions[R.NORMANDY]
    for target, rule in ENTRANCES.items():
        if target in regions:
            world.create_entrance(normandy, regions[target], rule, name=f"Galaxy Map -> {target.value}")
    regions[R.ILOS].connect(regions[R.FINAL_CITADEL], "Ilos -> Conduit")  # linear story

    for name, loc in data.LOCATIONS.items():
        if not location_included(world, name, loc):
            continue
        location = MassEffectLE1Location(world.player, name, data.LOCATION_NAME_TO_ID[name], regions[loc.region])
        if location_excluded(world, name, loc):
            location.progress_type = LocationProgressType.EXCLUDED
        if loc.region in data.NO_RETURN_REGIONS:
            add_item_rule(location, lambda item: no_return_item_allowed(world, item))
        elif no_progression_rule(world, name, loc):
            add_item_rule(location, lambda item: no_progression_item_allowed(world, item))
        elif missable(name):
            add_item_rule(location, missable_item_allowed)
        if container_holds_no_progression(world, loc):
            add_item_rule(location, missable_item_allowed)  # on top of the rules above
        regions[loc.region].locations.append(location)

    _add_event(world, regions[R.CITADEL], data.EVENT_ACT1)
    if world.options.human_squad_at_citadel:
        # Same names as the items, so HAS_SQUAD and VIRMIRE_PAIR count them; no ID, so the client never sets InParty.
        for name in data.HUMAN_SQUAD:
            _add_event(world, regions[R.CITADEL], name, f"Citadel: {name} Joins (arrival)")
    _add_event(world, regions[R.THERUM], data.EVENT_THERUM)
    _add_event(world, regions[R.FEROS], data.EVENT_FEROS)
    _add_event(world, regions[R.NOVERIA], data.EVENT_NOVERIA)
    _add_event(world, regions[R.VIRMIRE], data.EVENT_VIRMIRE)
    _add_event(world, regions[R.FINAL_CITADEL], data.EVENT_VICTORY)


def _add_event(world: MassEffectLE1World, region: Region, name: str, location_name: str | None = None) -> None:
    location = MassEffectLE1Location(world.player, location_name or name, None, region)
    location.place_locked_item(MassEffectLE1Item(name, ItemClassification.progression, None, world.player))
    region.locations.append(location)

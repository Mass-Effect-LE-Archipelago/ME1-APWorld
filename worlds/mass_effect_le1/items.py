from __future__ import annotations

from typing import TYPE_CHECKING

from BaseClasses import Item, LocationProgressType

from . import data

if TYPE_CHECKING:
    from .world import MassEffectLE1World


class MassEffectLE1Item(Item):
    game = data.GAME_NAME


def create_item(world: MassEffectLE1World, name: str) -> MassEffectLE1Item:
    return MassEffectLE1Item(name, data.ITEMS[name].classification, data.ITEM_NAME_TO_ID[name], world.player)


def create_items(world: MassEffectLE1World) -> None:
    pool: list[MassEffectLE1Item] = []
    for name, item in data.ITEMS.items():
        pool += [create_item(world, name) for _ in range(item.count)]

    if world.options.human_squad_at_citadel:
        pool = [item for item in pool if item.name not in data.HUMAN_SQUAD]
    if not world.options.bring_down_the_sky:
        pool = [item for item in pool if item.name != data.COORDINATES[data.Region.ASTEROID_X57]]
    if world.options.mako_shuffled:
        pool.append(create_item(world, data.MAKO))
    pool += [create_item(world, data.FRAGMENT) for _ in range(world.options.fragments_total.value)]

    unfilled = len(world.multiworld.get_unfilled_locations(world.player))
    if len(pool) > unfilled:
        # generate_early already guarantees room; this guards future table edits
        raise RuntimeError(f"{data.GAME_NAME}: {len(pool)} items for {unfilled} locations")

    # Useful items cannot go to excluded locations, nor to data.NO_RETURN_REGIONS with ilos_useful_items off: those slots
    # are left out of the free room that useful_share applies to.
    no_return = {region.value for region in data.NO_RETURN_REGIONS}
    excluded = sum(1 for loc in world.multiworld.get_unfilled_locations(world.player)
                   if loc.progress_type == LocationProgressType.EXCLUDED
                   or (not world.options.ilos_useful_items and loc.parent_region.name in no_return))
    room = unfilled - excluded
    useful = round(max(0, room - len(pool)) * world.options.useful_share.value / 100)
    gear_count, upgrades, experience = draw_useful(world, useful)
    gear = draw_gear(world, gear_count)
    pool += [create_item(world, name) for name in gear]
    world.gear_total = len(gear)
    pool += [create_item(world, data.UPGRADE) for _ in range(upgrades)]
    pool += [create_item(world, data.EXPERIENCE) for _ in range(experience)]

    pool += [create_item(world, world.get_filler_item_name()) for _ in range(unfilled - len(pool))]
    world.multiworld.itempool += pool


SPECTRE_SHARE = 20  # about one gear item in twenty is Spectre gear (at least one when any gear is drawn)
_SPECTRE_LINES = sum(1 for line in data.GEAR_LINES if line.spectre)
_OTHER_LINES = len(data.GEAR_LINES) - _SPECTRE_LINES
# The most distinct gear lines draw_gear can return (every non-Spectre line plus Spectre gear at one in twenty).
GEAR_MAX = max(count for count in range(1, len(data.GEAR_LINES) + 1)
               if min(_SPECTRE_LINES, max(1, count // SPECTRE_SHARE)) + _OTHER_LINES >= count)


def draw_useful(world: MassEffectLE1World, count: int) -> tuple[int, int, int]:
    """Split `count` useful items into (gear, upgrades, Experience), each item picked at random by the weight options.
    Gear stops at GEAR_MAX; the other kinds then share the rest. Items with no weight left become filler."""
    weights = [world.options.gear_weight.value, world.options.upgrade_weight.value, world.options.experience_weight.value]
    counts = [0, 0, 0]
    for _ in range(count):
        if counts[0] >= GEAR_MAX:
            weights[0] = 0
        if not any(weights):
            break
        counts[world.random.choices(range(3), weights)[0]] += 1
    return counts[0], counts[1], counts[2]


def draw_gear(world: MassEffectLE1World, count: int) -> list[str]:
    """Draw `count` distinct gear lines: Spectre lines first (count // SPECTRE_SHARE, at least 1), then round-robin over
    the categories in a random order, each category's lines shuffled, so every category is represented."""
    if count <= 0:
        return []
    rng = world.random
    spectre = [line.name for line in data.GEAR_LINES if line.spectre]
    rng.shuffle(spectre)
    picked = spectre[:max(1, count // SPECTRE_SHARE)]

    by_category: dict[str, list[str]] = {}
    for line in data.GEAR_LINES:
        if not line.spectre:
            by_category.setdefault(line.category, []).append(line.name)
    queues = list(by_category.values())
    for queue in queues:
        rng.shuffle(queue)
    rng.shuffle(queues)
    while len(picked) < count and any(queues):
        for queue in queues:
            if queue and len(picked) < count:
                picked.append(queue.pop())
    return picked

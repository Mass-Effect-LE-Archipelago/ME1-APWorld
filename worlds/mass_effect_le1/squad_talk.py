"""Squadmate Normandy conversations: what each check given in one needs besides the squadmate.

From the game data (cha00_*_dlg conversations, BioAutoConditionals in PlotManager.pcc, the StateTransitionMap in
BIOC_Materials.pcc). Each squadmate's talks come in stages. After the first, a stage opens only while that
squadmate's "new talk" flag is set, and talking clears it. Transitions 430-433 (Therum, Feros, Noveria, Virmire done)
set the flag once, so missions finished before a squadmate joins give one talk, not one each. Every third uncharted
Mako landing sets it again (transition 4057 counts landings, conditional 1226 is "count >= 3", transition 2986 sets
the flag), so landings are the source the logic counts on.
"""
from __future__ import annotations

from typing import NamedTuple


class TalkGate(NamedTuple):
    uncharted: bool = False  # needs uncharted landings: a later talk stage, or a flag set on an uncharted world
    missions: int = 0  # how many of Therum, Feros and Noveria must be finished (the conversation checks)
    choice: bool = False  # also needs a romance or dialogue-point choice, or the squadmate alive after Virmire: filler


TALK_GATES: dict[str, TalkGate] = {
    # Garrus: stage int 18, flag 5356 (F1085); his first talk gives none of these.
    "Codex: Aliens: Council Races: Turians: Culture": TalkGate(uncharted=True),  # stage 1
    "Codex: Aliens: Council Races: Turians: Military Doctrine": TalkGate(uncharted=True),  # stage 1
    "Codex: Aliens: Council Races: Turians: Biology": TalkGate(uncharted=True),  # stage 2
    "Codex: Aliens: Council Races: Turians: Government": TalkGate(uncharted=True),  # stage 3
    "Codex: Aliens: Council Races: Turians: Religion": TalkGate(uncharted=True, choice=True),  # stage 4, int 37/38 >= 4
    "Garrus: Find Dr. Saleon: Started": TalkGate(uncharted=True),  # stage >= 3 (F1088)
    # Liara: stage int 16, flag 4687. Culture, Government and Protheans: Beacon are in her first talk.
    "Codex: Aliens: Council Races: Asari: Religion": TalkGate(uncharted=True),  # stage 1
    # stage 2, bool 4169
    "Codex: Aliens: Council Races: Asari: Biology": TalkGate(uncharted=True, missions=2, choice=True),
    # Kaidan: stage int 15, flag 4688; every talk checks finished missions. Kaidan or Ashley dies on Virmire, so a page
    # only they give is choice (Mass Effect Fields: also an engineering console on the Normandy).
    "Codex: Technology: Biotics": TalkGate(missions=1, choice=True),
    "Codex: Technology: Mass Effect Fields": TalkGate(missions=1),
    "Codex: Planets and Locations: Stations: Gagarin Station": TalkGate(missions=1, choice=True),
    "Codex: Technology: Biotics: Training": TalkGate(missions=1, choice=True),
    "Codex: Technology: Biotics: Life as a Biotic": TalkGate(uncharted=True, missions=1, choice=True),  # stage 1
    "Codex: Aliens: Council Races: Salarians: Biology": TalkGate(uncharted=True, missions=2, choice=True),  # stage 2
    "Codex: Technology: Biotics: Biotic Amps": TalkGate(uncharted=True, missions=2, choice=True),  # stage 2
    # Ashley: stage int 17, flag 4685; her first talk already needs the flag (Human Diplomatic Relations: also Pressly).
    "Codex: Humanity and the Systems Alliance: Human Diplomatic Relations": TalkGate(uncharted=True),
    "Codex: Humanity and the Systems Alliance: Systems Alliance: Military Doctrine":
        TalkGate(uncharted=True, missions=1, choice=True),
    "Codex: Ships and Vehicles: Space Combat: Planetary Assaults": TalkGate(uncharted=True, missions=2, choice=True),
    # Tali: flag 7143. Economy, Migrant Fleet and Government are in her first talk.
    "Codex: Aliens: Non-Council Races: Quarians: Religion": TalkGate(uncharted=True),
    "Codex: Aliens: Non-Council Races: Quarians: Law and Defense": TalkGate(uncharted=True),  # bool 4599, a later talk
    "Tali and the Geth: Started": TalkGate(uncharted=True),  # bool 4597, set on Solcrum (BIOA_UNC55)
    "Tali and the Geth: Completed": TalkGate(uncharted=True),
    # Wrex: stage bools 5110-5113, flag 5334. He can die on Virmire, so a page only his later talks give is choice.
    # Genophage is in his first talk (and Kirrahe's, before the standoff); the requisitions officer gives Body Armor.
    "Codex: Weapons, Armor and Equipment: Body Armor": TalkGate(uncharted=True),  # bool 5112
    "Codex: Aliens: Non-Council Races: Krogan: Culture": TalkGate(uncharted=True, choice=True),
    "Codex: Aliens: Non-Council Races: Krogan: Military Doctrine": TalkGate(uncharted=True, choice=True),  # bool 5113
    "Codex: Aliens: Non-Council Races: Krogan: Biology": TalkGate(uncharted=True, choice=True),
    "Wrex: Family Armor: Started": TalkGate(uncharted=True, choice=True),  # bool 5112
    "Wrex: Family Armor: Completed": TalkGate(uncharted=True, choice=True),
}

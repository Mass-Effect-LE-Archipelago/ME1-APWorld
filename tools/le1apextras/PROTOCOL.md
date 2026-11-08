# LE1APExtras protocol (version 1)

Named pipe `\\.\pipe\LE1APExtras`, one client at a time, one ASCII request per message and one reply per request
(the same transport as LE1APBridge). Requests that touch the game run on the game thread (ProcessEvent hook); the
pipe thread waits up to 5 seconds and otherwise answers `ERR timeout`.

| Request | Reply | Notes |
|---|---|---|
| `PING` | `OK pong 1` | Answered on the pipe thread. |
| `VER` | `OK 1` | |
| `LEVEL` | `OK <level> <xp>` | The player squad's level (`BioPlayerSquad.GetPlayerSquadLevel`) and XP. |
| `XPIDX` | `OK <n>` | Experience items granted to this save: plot int 2010. |
| `XPTXN <seed> <slot> <index> <amount>` | `OK applied` / `OK done` / `ERR gap <n>` / `ERR identity` | Grants Experience item `<index>` once: only on the save bound to `<seed> <slot>` (plot ints 2004/2005, set by LE1APBridge's IDSET), only when plot int 2010 equals `<index>`; then `BioPlayerSquad.GrantExperience(<amount>, Generic)` and int 2010 + 1 in the same game-thread step. A lower index answers `OK done` (already granted). Amount 1-1000000. |

Errors: `ERR noworld` (no world or plot table yet), `ERR nosquad` (no player squad yet), `ERR timeout`,
`ERR notallowed` (an argument out of range), `ERR badrequest`, `ERR badop`.

The client (`worlds/mass_effect_le1/client.py`) delivers each Experience item through LE1APBridge as `TXN NONE`, so
the bridge's received index keeps the server's order, and then grants it here (`sync_experience`). The amount is the
game's `LevelUp_Experience` quest reward for the slot's `experience_size` at the squad level read with `LEVEL`.

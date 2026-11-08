#pragma once
// Version info for the Archipelago ME1 extras ASI (format follows LExASIs' SharedVersion.h).

#define CURRENT_YEAR "2026"
#define DEVELOPER_A "ME1-APWorld"
#define DEVELOPER_W L"ME1-APWorld"
#define ASI_NAME_A "LE1 AP Extras"
#define ASI_NAME_W L"LE1 AP Extras"
#define ASI_NAME_NO_SPACE_A "LE1APExtras"
#define ASI_NAME_NO_SPACE_W L"LE1APExtras"
#define ASI_VERSION 1
#define ASI_DESCRIPTION "Named-pipe companion to LE1APBridge: squad level and exactly-once XP grants."

#define ASI_GAME_ID_RC 4
#define ASI_GROUP_ID_RC 0

#define STRINGIFY(x) #x
#define TOSTRING(x) STRINGIFY(x)
#define VERSION_STRING_A TOSTRING(ASI_VERSION) ".0." TOSTRING(ASI_GAME_ID_RC) "." TOSTRING(ASI_GROUP_ID_RC)
#define VERSION_STRING_W TOSTRING(ASI_VERSION) L".0." TOSTRING(ASI_GAME_ID_RC) L"." TOSTRING(ASI_GROUP_ID_RC)

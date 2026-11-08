#pragma once
#include <LESDK/Headers.hpp>
#include <LESDK/Init.hpp>
#include "Common/Base.hpp"

// Named pipe \\.\pipe\LE1APExtras; the request/reply contract is tools/le1apextras/PROTOCOL.md.
// Plot and squad access happens on the game thread (ProcessEvent hook); the pipe thread only parses, queues and waits,
// so one XPTXN (grant + XP index update) can never be split by a save.
namespace LE1APExtras
{
    void StartPipeServer();
    void StopPipeServer();           // on ASI detach: ask the pipe thread to stop (the module is pinned)
    void ProcessPendingRequests();   // call on the game thread

    using t_UObject_ProcessEvent = void(UObject* Context, UFunction* Function, void* Parms, void* Result);
    extern t_UObject_ProcessEvent* UObject_ProcessEvent_orig;
    void UObject_ProcessEvent_hook(UObject* Context, UFunction* Function, void* Parms, void* Result);
}

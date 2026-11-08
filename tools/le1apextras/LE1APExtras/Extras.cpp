#include "LE1APExtras/Extras.hpp"
#include "LE1APExtras/SharedVersion.h"
#include "Common/Objects.hpp"

#include <Windows.h>
#include <concurrent_queue.h>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <future>
#include <string>
#include <thread>

// Pipe thread, game-thread queue and world lookup follow LE2APBridge (ME2-APWorld), itself ported from LE1APBridge.
namespace LE1APExtras
{
    namespace
    {
        constexpr wchar_t PipeName[] = L"\\\\.\\pipe\\LE1APExtras";
        constexpr DWORD BufferSize = 1024;
        // AP plot ints shared with LE1APBridge (worlds/mass_effect_le1/client.py): the save's identity, and the number of
        // XP grants applied, written only by XPTXN.
        constexpr int IdentitySeedInt = 2004, IdentitySlotInt = 2005;
        constexpr int XpIndexInt = 2010;
        constexpr int XpAmountMax = 1000000;
        // SFXGame.BioPlayerSquad.EExperienceSourceType
        constexpr unsigned char XpSourceGeneric = 3;

        struct Request
        {
            char Op[8]{};
            int Args[4]{};
            std::promise<std::string> Reply;
        };

        concurrency::concurrent_queue<Request*> g_Pending{};
        std::atomic<bool> g_Stop{ false };
        thread_local bool t_InProcess = false;

        // First live (not default, not being destroyed) object of type T.
        template<typename T>
        T* FirstLive()
        {
            constexpr uint64_t Dead = static_cast<uint64_t>(EObjectFlags::ClassDefaultObject)
                | static_cast<uint64_t>(EObjectFlags::PendingKill) | static_cast<uint64_t>(EObjectFlags::Unreachable)
                | static_cast<uint64_t>(EObjectFlags::BeginDestroyed) | static_cast<uint64_t>(EObjectFlags::FinishDestroyed);
            UObject** const Data = UObject::GObjObjects->GetData();
            int const Count = UObject::GObjObjects->Count();
            for (int i = 0; i < Count; ++i)
            {
                UObject* const Obj = Data[i];
                if (Obj == nullptr || (static_cast<uint64_t>(Obj->ObjectFlags) & Dead) != 0) continue;
                if (T* const Typed = Obj->Cast<T>()) return Typed;
            }
            return nullptr;
        }

        ABioWorldInfo* CurrentBioWorld()
        {
            // Asking the engine before the first world exists dereferences a null persistent level (LE1APBridge,
            // 2026-10-08), so only ask once a live world object has been seen.
            static bool WorldSeen = false;
            static UEngine* Engine = nullptr;
            if (!WorldSeen && FirstLive<ABioWorldInfo>() == nullptr) return nullptr;
            WorldSeen = true;
            if (Engine == nullptr) Engine = FirstLive<UEngine>();
            if (Engine == nullptr) return nullptr;
            AWorldInfo* const World = Engine->GetCurrentWorldInfo();
            return World != nullptr ? World->Cast<ABioWorldInfo>() : nullptr;
        }

        // A loaded save or new career: a world with its plot table and the player squad.
        std::string GetContext(ABioWorldInfo*& World, UBioGlobalVariableTable*& Vars, ABioPlayerSquad*& Squad)
        {
            World = CurrentBioWorld();
            if (World == nullptr) return "ERR noworld";
            Vars = World->GetGlobalVariables();
            if (Vars == nullptr) return "ERR noworld";
            Squad = World->m_playerSquad;
            if (Squad == nullptr) return "ERR nosquad";
            return "";
        }

        // XPTXN <seed> <slot> <index> <amount>: grant XP item <index> exactly once, on the save bound to <seed> <slot>.
        // The grant and the XP index update run in the same game-thread step, so no save holds one without the other.
        std::string ExecuteXpTxn(Request const& R, UBioGlobalVariableTable* Vars, ABioPlayerSquad* Squad)
        {
            if (Vars->GetInt(IdentitySeedInt) != R.Args[0] || Vars->GetInt(IdentitySlotInt) != R.Args[1])
                return "ERR identity";
            int const Current = Vars->GetInt(XpIndexInt);
            if (R.Args[2] < Current) return "OK done";
            if (R.Args[2] > Current) return "ERR gap " + std::to_string(Current);
            Squad->GrantExperience(R.Args[3], XpSourceGeneric);
            Vars->SetInt(XpIndexInt, Current + 1);
            LEASI_INFO("XPTXN {} {} -> applied", R.Args[2], R.Args[3]);
            return "OK applied";
        }

        std::string Execute(Request const& R)
        {
            ABioWorldInfo* World = nullptr;
            UBioGlobalVariableTable* Vars = nullptr;
            ABioPlayerSquad* Squad = nullptr;
            std::string const Error = GetContext(World, Vars, Squad);
            if (!Error.empty()) return Error;
            std::string const Op{ R.Op };
            if (Op == "LEVEL")
                return "OK " + std::to_string(Squad->eventGetPlayerSquadLevel()) + " " + std::to_string(Squad->GetPlayerSquadExperience());
            if (Op == "XPIDX") return "OK " + std::to_string(Vars->GetInt(XpIndexInt));
            if (Op == "XPTXN") return ExecuteXpTxn(R, Vars, Squad);
            return "ERR badop";
        }

        // Parses and validates on the pipe thread; returns a reply, or "" if the request must run in game.
        std::string Parse(char const* Text, Request& R)
        {
            int const Fields = std::sscanf(Text, "%7s %d %d %d %d", R.Op, &R.Args[0], &R.Args[1], &R.Args[2], &R.Args[3]);
            std::string const Op{ R.Op };
            if (Fields == 1 && Op == "PING") return "OK pong " TOSTRING(ASI_VERSION);
            if (Fields == 1 && Op == "VER") return "OK " TOSTRING(ASI_VERSION);
            if (Fields == 1 && (Op == "LEVEL" || Op == "XPIDX")) return "";
            if (Fields == 5 && Op == "XPTXN")
                return (R.Args[0] > 0 && R.Args[1] > 0 && R.Args[2] >= 0 && R.Args[3] >= 1 && R.Args[3] <= XpAmountMax)
                    ? "" : "ERR notallowed";
            return "ERR badrequest";
        }

        void Reply(HANDLE Pipe, std::string const& Text)
        {
            DWORD Written = 0;
            WriteFile(Pipe, Text.c_str(), static_cast<DWORD>(Text.size()), &Written, nullptr);
        }

        void PipeThread()
        {
            while (!g_Stop.load())
            {
                HANDLE Pipe = CreateNamedPipeW(PipeName, PIPE_ACCESS_DUPLEX,
                    PIPE_TYPE_MESSAGE | PIPE_READMODE_MESSAGE | PIPE_WAIT, 1, BufferSize, BufferSize, 0, nullptr);
                if (Pipe == INVALID_HANDLE_VALUE)
                {
                    LEASI_ERROR("CreateNamedPipe failed: {}", GetLastError());
                    return;
                }
                if (ConnectNamedPipe(Pipe, nullptr) != FALSE || GetLastError() == ERROR_PIPE_CONNECTED)
                {
                    LEASI_INFO("Client connected");
                    char Buffer[BufferSize]{};
                    DWORD Read = 0;
                    while (!g_Stop.load() && ReadFile(Pipe, Buffer, BufferSize - 1, &Read, nullptr) != FALSE)
                    {
                        Buffer[Read] = '\0';
                        auto* R = new Request{};
                        std::string const Error = Parse(Buffer, *R);
                        if (!Error.empty())
                        {
                            delete R;
                            Reply(Pipe, Error);
                            continue;
                        }
                        std::future<std::string> Result = R->Reply.get_future();
                        g_Pending.push(R);   // ownership passes to the game thread
                        // A timed-out XPTXN may still apply later; the client's retry then gets "OK done", never a second
                        // grant, because the index is compared on the game thread.
                        if (Result.wait_for(std::chrono::seconds(5)) == std::future_status::ready)
                            Reply(Pipe, Result.get());
                        else
                            Reply(Pipe, "ERR timeout");
                    }
                    LEASI_INFO("Client disconnected");
                }
                DisconnectNamedPipe(Pipe);
                CloseHandle(Pipe);
            }
        }
    }

    void StartPipeServer()
    {
        // Pin this module: the pipe thread lives for the whole process, so the ASI must never be unloaded under it.
        HMODULE Self = nullptr;
        GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_PIN,
            reinterpret_cast<LPCWSTR>(&StartPipeServer), &Self);
        std::thread(PipeThread).detach();
        LEASI_INFO("Pipe server started (module pinned)");
    }

    void StopPipeServer()
    {
        g_Stop.store(true);
    }

    void ProcessPendingRequests()
    {
        if (t_InProcess) return;   // SDK calls re-enter ProcessEvent; do not nest
        t_InProcess = true;
        Request* R = nullptr;
        while (g_Pending.try_pop(R))
        {
            R->Reply.set_value(Execute(*R));
            delete R;
        }
        t_InProcess = false;
    }

    t_UObject_ProcessEvent* UObject_ProcessEvent_orig = nullptr;
    void UObject_ProcessEvent_hook(UObject* Context, UFunction* Function, void* Parms, void* Result)
    {
        ProcessPendingRequests();
        UObject_ProcessEvent_orig(Context, Function, Parms, Result);
    }
}

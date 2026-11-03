# Oodle block codec for le1pkg.py: runs OodleLZ_Decompress / OodleLZ_Compress from the game's own oo2core DLL.
# Jobs file: int32 count, then per block: int32 inSize, int32 outSize (decompress: the raw size; compress: 0), bytes.
# Output file: per block, int32 size then bytes.
param([string]$Dll, [string]$Mode, [string]$Jobs, [string]$Out)
$ErrorActionPreference = "Stop"
Add-Type -TypeDefinition @"
using System;
using System.IO;
using System.Runtime.InteropServices;
public static class LE1Oodle {
    [DllImport("kernel32", SetLastError=true, CharSet=CharSet.Unicode)] static extern IntPtr LoadLibrary(string p);
    [DllImport("kernel32")] static extern IntPtr GetProcAddress(IntPtr h, string n);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    delegate long Dec(byte[] c, long cs, byte[] r, long rs, int fuzz, int crc, int verb, IntPtr a, long b, IntPtr cb, IntPtr ud, IntPtr mem, long ms, int phase);
    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    delegate long Enc(int compressor, byte[] r, long rs, byte[] c, int level, IntPtr opts, IntPtr dict, IntPtr lrm, IntPtr scratch, long ss);
    const int Kraken = 8, LevelNormal = 4;
    public static void Run(string dll, string mode, string jobs, string outp) {
        IntPtr h = LoadLibrary(dll); if (h == IntPtr.Zero) throw new Exception("LoadLibrary " + Marshal.GetLastWin32Error());
        var dec = (Dec)Marshal.GetDelegateForFunctionPointer(GetProcAddress(h, "OodleLZ_Decompress"), typeof(Dec));
        var enc = (Enc)Marshal.GetDelegateForFunctionPointer(GetProcAddress(h, "OodleLZ_Compress"), typeof(Enc));
        using (var r = new BinaryReader(File.OpenRead(jobs))) using (var w = new BinaryWriter(File.Create(outp))) {
            int n = r.ReadInt32();
            for (int i = 0; i < n; i++) {
                int inSize = r.ReadInt32(), outSize = r.ReadInt32();
                byte[] input = r.ReadBytes(inSize);
                if (mode == "decompress") {
                    byte[] o = new byte[outSize];
                    long got = dec(input, inSize, o, outSize, 1, 0, 0, IntPtr.Zero, 0, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, 0, 3);
                    if (got != outSize) throw new Exception("decompress block " + i + ": " + got + " != " + outSize);
                    w.Write(outSize); w.Write(o);
                } else {
                    byte[] o = new byte[inSize + 274 * ((inSize + 0x3FFFF) / 0x40000) + 1024];
                    long got = enc(Kraken, input, inSize, o, LevelNormal, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, IntPtr.Zero, 0);
                    if (got <= 0) throw new Exception("compress block " + i + " failed");
                    w.Write((int)got); w.Write(o, 0, (int)got);
                }
            }
        }
    }
}
"@
[LE1Oodle]::Run($Dll, $Mode, $Jobs, $Out)

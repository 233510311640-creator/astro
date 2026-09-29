using System;
using System.IO;
using System.Runtime.InteropServices;

namespace Cypher.CorePreview
{
    // One bounded, in-memory recording from the Windows default microphone.
    // Short native buffers expose completed audio without saving it to disk.
    internal sealed class VoiceCapture : IDisposable
    {
        [StructLayout(LayoutKind.Sequential)]
        private struct WaveFormat
        {
            public ushort FormatTag, Channels;
            public uint SamplesPerSecond, AverageBytesPerSecond;
            public ushort BlockAlign, BitsPerSample, ExtraSize;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct WaveHeader
        {
            public IntPtr Data;
            public uint BufferLength, BytesRecorded;
            public IntPtr User;
            public uint Flags, Loops;
            public IntPtr Next, Reserved;
        }

        [DllImport("winmm.dll", ExactSpelling = true)] private static extern uint waveInOpen(out IntPtr handle, uint device, ref WaveFormat format, IntPtr callback, IntPtr instance, uint flags);
        [DllImport("winmm.dll", ExactSpelling = true)] private static extern uint waveInPrepareHeader(IntPtr handle, IntPtr header, uint size);
        [DllImport("winmm.dll", ExactSpelling = true)] private static extern uint waveInAddBuffer(IntPtr handle, IntPtr header, uint size);
        [DllImport("winmm.dll", ExactSpelling = true)] private static extern uint waveInStart(IntPtr handle);
        [DllImport("winmm.dll", ExactSpelling = true)] private static extern uint waveInStop(IntPtr handle);
        [DllImport("winmm.dll", ExactSpelling = true)] private static extern uint waveInReset(IntPtr handle);
        [DllImport("winmm.dll", ExactSpelling = true)] private static extern uint waveInUnprepareHeader(IntPtr handle, IntPtr header, uint size);
        [DllImport("winmm.dll", ExactSpelling = true)] private static extern uint waveInClose(IntPtr handle);

        private const int MaxSeconds = 20;
        private const int BufferMilliseconds = 200;
        private const uint HeaderDone = 0x00000001;
        private IntPtr handle;
        private IntPtr[] data;
        private IntPtr[] headers;
        private int rate;
        private int preparedCount;
        private int nextLevelBuffer;
        private bool finished;

        public void Start()
        {
            if (handle != IntPtr.Zero || finished) throw new InvalidOperationException("The microphone is already in use.");
            uint result = 1;
            foreach (int candidate in new[] { 16000, 48000 })
            {
                WaveFormat format = new WaveFormat
                {
                    FormatTag = 1, Channels = 1, SamplesPerSecond = (uint)candidate,
                    AverageBytesPerSecond = (uint)(candidate * 2), BlockAlign = 2,
                    BitsPerSample = 16, ExtraSize = 0
                };
                result = waveInOpen(out handle, 0xffffffffU, ref format, IntPtr.Zero, IntPtr.Zero, 0);
                if (result == 0) { rate = candidate; break; }
                handle = IntPtr.Zero;
            }
            if (handle == IntPtr.Zero) throw new InvalidOperationException("Windows could not open the default microphone (code " + result + "). Check microphone access and input selection.");
            try
            {
                int count = MaxSeconds * 1000 / BufferMilliseconds;
                int capacity = checked(rate * 2 * BufferMilliseconds / 1000);
                data = new IntPtr[count];
                headers = new IntPtr[count];
                uint size = (uint)Marshal.SizeOf(typeof(WaveHeader));
                for (int i = 0; i < count; i++)
                {
                    data[i] = Marshal.AllocHGlobal(capacity);
                    headers[i] = Marshal.AllocHGlobal((int)size);
                    Marshal.StructureToPtr(new WaveHeader { Data = data[i], BufferLength = (uint)capacity }, headers[i], false);
                    Check(waveInPrepareHeader(handle, headers[i], size), "prepare");
                    preparedCount++;
                    Check(waveInAddBuffer(handle, headers[i], size), "queue");
                }
                Check(waveInStart(handle), "start");
            }
            catch { Dispose(); throw; }
        }

        public byte[] Finish()
        {
            if (finished || handle == IntPtr.Zero) throw new InvalidOperationException("No microphone recording is active.");
            finished = true;
            Check(waveInStop(handle), "stop");
            Check(waveInReset(handle), "flush");
            using (MemoryStream stream = new MemoryStream())
            {
                for (int i = 0; i < headers.Length; i++)
                {
                    WaveHeader recorded = (WaveHeader)Marshal.PtrToStructure(headers[i], typeof(WaveHeader));
                    int count = checked((int)recorded.BytesRecorded);
                    if (count < 0 || count > recorded.BufferLength || (count & 1) != 0)
                        throw new InvalidOperationException("Windows returned an invalid microphone recording length.");
                    if (count == 0) continue;
                    byte[] chunk = new byte[count];
                    Marshal.Copy(data[i], chunk, 0, count);
                    stream.Write(chunk, 0, chunk.Length);
                    Array.Clear(chunk, 0, chunk.Length);
                }
                return BuildWave(stream.ToArray(), rate);
            }
        }

        // Only buffers marked done by the device are inspected. No native callback
        // calls back into Windows multimedia or WPF while capture is active.
        public int[] ReadCompletedLevels()
        {
            if (finished || handle == IntPtr.Zero) return new int[0];
            System.Collections.Generic.List<int> levels = new System.Collections.Generic.List<int>();
            while (nextLevelBuffer < headers.Length)
            {
                WaveHeader recorded = (WaveHeader)Marshal.PtrToStructure(headers[nextLevelBuffer], typeof(WaveHeader));
                if ((recorded.Flags & HeaderDone) == 0) break;
                int count = checked((int)recorded.BytesRecorded);
                if (count < 0 || count > recorded.BufferLength || (count & 1) != 0)
                    throw new InvalidOperationException("Windows returned an invalid microphone buffer.");
                byte[] chunk = new byte[count];
                if (count > 0) Marshal.Copy(data[nextLevelBuffer], chunk, 0, count);
                levels.Add(RootMeanSquare(chunk));
                Array.Clear(chunk, 0, chunk.Length);
                nextLevelBuffer++;
            }
            return levels.ToArray();
        }

        internal static int RootMeanSquare(byte[] pcm)
        {
            if (pcm == null || (pcm.Length & 1) != 0) throw new ArgumentException("Invalid PCM audio.");
            int samples = pcm.Length / 2;
            if (samples == 0) return 0;
            double squareSum = 0;
            for (int i = 0; i < pcm.Length; i += 2)
            {
                short sample = (short)(pcm[i] | (pcm[i + 1] << 8));
                squareSum += (double)sample * sample;
            }
            return (int)Math.Sqrt(squareSum / samples);
        }

        internal static byte[] BuildWave(byte[] pcm, int sampleRate)
        {
            if (pcm == null || (pcm.Length & 1) != 0 || (sampleRate != 16000 && sampleRate != 48000) || pcm.Length > sampleRate * 2 * MaxSeconds)
                throw new ArgumentException("Invalid bounded microphone audio.");
            using (MemoryStream stream = new MemoryStream(44 + pcm.Length))
            using (BinaryWriter writer = new BinaryWriter(stream))
            {
                writer.Write(new[] { 'R', 'I', 'F', 'F' });
                writer.Write((uint)(36 + pcm.Length));
                writer.Write(new[] { 'W', 'A', 'V', 'E' });
                writer.Write(new[] { 'f', 'm', 't', ' ' });
                writer.Write((uint)16);
                writer.Write((ushort)1);
                writer.Write((ushort)1);
                writer.Write((uint)sampleRate);
                writer.Write((uint)(sampleRate * 2));
                writer.Write((ushort)2);
                writer.Write((ushort)16);
                writer.Write(new[] { 'd', 'a', 't', 'a' });
                writer.Write((uint)pcm.Length);
                writer.Write(pcm);
                writer.Flush();
                return stream.ToArray();
            }
        }

        private static void Check(uint result, string action)
        { if (result != 0) throw new InvalidOperationException("Windows could not " + action + " the microphone (code " + result + ")."); }

        public void Dispose()
        {
            if (handle != IntPtr.Zero)
            {
                waveInStop(handle);
                waveInReset(handle);
                if (headers != null)
                    for (int i = 0; i < preparedCount; i++)
                        waveInUnprepareHeader(handle, headers[i], (uint)Marshal.SizeOf(typeof(WaveHeader)));
                waveInClose(handle);
                handle = IntPtr.Zero;
            }
            if (headers != null)
                foreach (IntPtr item in headers) if (item != IntPtr.Zero) Marshal.FreeHGlobal(item);
            if (data != null)
                foreach (IntPtr item in data) if (item != IntPtr.Zero) Marshal.FreeHGlobal(item);
            headers = null;
            data = null;
            preparedCount = 0;
            finished = true;
        }
    }
}

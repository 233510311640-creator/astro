using System;

namespace Cypher.CorePreview
{
    // Conservative end-of-utterance detector for 200 ms PCM blocks. It may
    // leave a quiet speaker on the normal timeout, but never cuts off a pause
    // until actual microphone activity has first been observed.
    internal sealed class VoiceActivityGate
    {
        private int blocks;
        private int loudBlocks;
        private int quietBlocks;
        private bool speechSeen;

        public bool Observe(int rootMeanSquare)
        {
            if (rootMeanSquare < 0) throw new ArgumentOutOfRangeException("rootMeanSquare");
            blocks++;
            if (rootMeanSquare >= 600)
            {
                loudBlocks++;
                quietBlocks = 0;
                if (loudBlocks >= 2) speechSeen = true;
            }
            else
            {
                loudBlocks = 0;
                if (speechSeen) quietBlocks = rootMeanSquare < 300 ? quietBlocks + 1 : 0;
            }
            return speechSeen && blocks >= 8 && quietBlocks >= 6;
        }

        public static bool SelfTest()
        {
            VoiceActivityGate gate = new VoiceActivityGate();
            for (int i = 0; i < 20; i++) if (gate.Observe(0)) return false;
            gate = new VoiceActivityGate();
            if (gate.Observe(900) || gate.Observe(900) || gate.Observe(900)) return false;
            for (int i = 0; i < 5; i++) if (gate.Observe(0)) return false;
            if (!gate.Observe(0)) return false;
            gate = new VoiceActivityGate();
            gate.Observe(900); gate.Observe(900);
            for (int i = 0; i < 4; i++) if (gate.Observe(0)) return false;
            gate.Observe(900);
            for (int i = 0; i < 5; i++) if (gate.Observe(0)) return false;
            return gate.Observe(0);
        }
    }
}

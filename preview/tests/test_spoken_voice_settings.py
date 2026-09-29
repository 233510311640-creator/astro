from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SpokenVoiceSettingsTests(unittest.TestCase):
    def test_same_selected_voice_is_used_for_greeting_and_reply(self):
        source = (ROOT / "windows" / "Cypher.CorePreview" / "VoiceHost.cs").read_text(encoding="utf-8")
        greeting = source.split("private void AcknowledgeWake()", 1)[1].split("private void MaybeSpeakWakeReply()", 1)[0]
        reply = source.split("private void ToggleReadAloud()", 1)[1].split("private static string SpeechSafeText", 1)[0]
        self.assertIn("ConfigureVoiceSpeaker();", greeting)
        self.assertIn("ConfigureVoiceSpeaker();", reply)
        self.assertIn("voiceSpeaker.SelectVoice(name)", source)

    def test_voice_picker_is_local_and_explicit(self):
        voice = (ROOT / "windows" / "Cypher.CorePreview" / "VoiceHost.cs").read_text(encoding="utf-8")
        host = (ROOT / "windows" / "Cypher.CorePreview" / "CypherCoreHost.cs").read_text(encoding="utf-8")
        self.assertIn("Spoken voice settings...", host)
        self.assertIn("previewSpeaker.GetInstalledVoices()", voice)
        self.assertIn("save.Click += delegate", voice)
        self.assertIn('settings["speech_voice_name"]', voice)
        self.assertIn('settings["speech_rate"]', voice)
        self.assertNotIn("HttpClient", voice)

    def test_upgrade_keeps_voice_preference(self):
        installer = (ROOT / "scripts" / "install_cypher_core_preview_windows.ps1").read_text(encoding="utf-8")
        self.assertIn('speech_voice_name = ""', installer)
        self.assertIn("speech_rate = 0", installer)
        self.assertIn("$previousCloud.speech_voice_name", installer)
        self.assertIn("$previousCloud.speech_rate", installer)


if __name__ == "__main__":
    unittest.main()

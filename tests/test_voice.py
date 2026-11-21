"""Audio pipeline contract tests with fakes (no microphone/models required)."""
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from voice_pipeline import process_turn


class ASR:
    def transcribe(self, audio, language):
        return "Olá" if language == "pt" else "Hello"


class MT:
    def translate(self, text, src, tgt):
        return "Hello" if src == "pt" else "Olá"


class TTS:
    def synthesize(self, text, language):
        return b"RIFF" + b"\0" * 32


class VoiceTests(unittest.TestCase):
    def test_pt_to_en(self):
        r = process_turn(b"fake.wav", "pt", "en", ASR(), MT(), TTS())
        self.assertEqual((r.original_text, r.translated_text), ("Olá", "Hello"))
        self.assertTrue(r.wav_bytes.startswith(b"RIFF"))

    def test_en_to_pt(self):
        r = process_turn(b"fake.wav", "en", "pt", ASR(), MT(), TTS())
        self.assertEqual((r.original_text, r.translated_text), ("Hello", "Olá"))

    def test_same_language_rejected(self):
        with self.assertRaises(ValueError):
            process_turn(b"fake.wav", "en", "en", ASR(), MT(), TTS())

    def test_empty_audio_rejected(self):
        with self.assertRaises(ValueError):
            process_turn(b"", "en", "pt", ASR(), MT(), TTS())

    def test_asr_empty_prevents_mt_tts(self):
        class EmptyASR:
            def transcribe(self, *args):
                return " "
        with self.assertRaisesRegex(ValueError, "NO_SPEECH"):
            process_turn(b"fake.wav", "en", "pt", EmptyASR(), MT(), TTS())

    def test_translation_empty_prevents_tts(self):
        class EmptyMT:
            def translate(self, *args):
                return ""
        with self.assertRaisesRegex(ValueError, "EMPTY_TRANSLATION"):
            process_turn(b"fake.wav", "en", "pt", ASR(), EmptyMT(), TTS())

    def test_invalid_wav_rejected(self):
        class BadTTS:
            def synthesize(self, *args):
                return b"bad"
        with self.assertRaisesRegex(ValueError, "INVALID_TTS_WAV"):
            process_turn(b"fake.wav", "en", "pt", ASR(), MT(), BadTTS())


if __name__ == "__main__":
    unittest.main()

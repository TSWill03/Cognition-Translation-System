"""CTS voice research pilot: manually recorded single turns, PT <-> EN."""
from pathlib import Path

import streamlit as st

from voice_pipeline import ArgosMT, PiperTTS, WhisperASR, process_turn

st.set_page_config(page_title="CTS | Voice pilot", page_icon="🎙️", layout="centered")
st.title("CTS — Voz bidirecional (experimental)")
st.caption("Um turno de fala por vez, PT ↔ EN; ASR + tradução + voz sintetizada no servidor local")
st.warning("Não é tradução simultânea, chamada, clonagem de voz nem sistema validado. "
           "A gravação é transmitida ao servidor Streamlit configurado. Use apenas localmente com consentimento.")
source = st.radio("Quem está falando?", ["pt", "en"], format_func=lambda c: {"pt": "Português → Inglês", "en": "Inglês → Português"}[c], horizontal=True)
target = "en" if source == "pt" else "pt"
voice_dir = Path(__file__).resolve().parent / "models" / "voices"
prefix = "en_" if target == "en" else "pt_"
voices = sorted(f for f in voice_dir.glob("*.onnx") if f.name.lower().startswith(prefix)) if voice_dir.is_dir() else []
if not voices:
    st.info(f"Adicione um modelo Piper {target} (*.onnx e *.onnx.json) em models/voices/ após verificar sua licença.")
voice = st.selectbox("Modelo de voz para o idioma de destino", voices, format_func=lambda p: p.name) if voices else None
recording = st.audio_input("Grave uma frase", sample_rate=16000)
if st.button("Transcrever → Traduzir → Falar", type="primary", disabled=recording is None or voice is None):
    with st.spinner("Processando localmente (pode demorar no primeiro turno)…"):
        try:
            result = process_turn(recording.getvalue(), source, target,
                                  WhisperASR("small"), ArgosMT(), PiperTTS(voice))
        except Exception as exc:
            st.error(f"Falha no processamento: {type(exc).__name__}: {exc}")
        else:
            st.text_area("Transcrição", result.original_text, height=90)
            st.text_area("Tradução", result.translated_text, height=90)
            st.audio(result.wav_bytes, format="audio/wav")
            st.caption(f"ASR {result.asr_ms:.1f} ms · MT {result.mt_ms:.1f} ms · TTS {result.tts_ms:.1f} ms (exclui carga de modelo).")
            st.download_button("Baixar WAV traduzido", result.wav_bytes, "cts_voice.wav", "audio/wav")
st.markdown("Instruções de instalação e licenciamento: " + "[docs/BIDIRECTIONAL_VOICE_MVP.md](https://github.com/TSWill03/Cognition-Translation-System/blob/feature/bidirectional-text-voice-pilot/docs/BIDIRECTIONAL_VOICE_MVP.md).")

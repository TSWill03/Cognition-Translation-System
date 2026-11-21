# CTS — teste bidirecional e piloto de voz (experimental)

**Estado:** implementação em branch de pesquisa. Ensaios com modelos reais e áudio real ainda precisam ser executados em máquina com os modelos instalados. Não alterar as estatísticas do CTS Text-300 nem afirmar tradução simultânea disponível.

## Protocolos textuais novos

O estudo inicial mediu 20 entradas originais EN × 15 destinos = 300 traduções EN→X.

**Modo independente (padrão, EN↔PT).** Usa as 20 frases inglesas do estudo original e 20 outras frases redigidas originalmente em português (ver arquivo prompts_reverse.json). Planejado: **20 EN→PT + 20 PT→EN = 40 traduções**. Essas frases PT são material de pesquisa assistido por IA, não revisão humana validada e não formam corpus paralelo às frases EN. Não se deve calcular BLEU/COMET com dois conjuntos não equivalentes.

**Modo roundtrip (EN↔15).** Para cada frase, mede EN→X e utiliza o texto gerado na ida como entrada X→EN. Planejado: **300 idas + 300 voltas = 600 chamadas**. A fonte X não é humana nem independente. Semelhança após roundtrip não comprova fidelidade. Cada registro distingue sua procedência.

O runner grava entradas/saídas brutas, erros e status por direção, aquecimento/carga, inferência em ms, inventário dos modelos, ambiente, SHA-256 e diagnósticos numéricos heurísticos. Pacotes Argos **diretos** são exigidos por direção (sem pivôs implícitos). Êxito operacional = texto não vazio; não prova tradução correta. Não mistura dados novos no resultado histórico.

## Rodar experimento bidirecional

Executar no repositório com Python 3.11/3.12:

~~~bash
python -m pip install -r requirements.txt
# Pacote EN→PT deve estar instalado pelo laboratório original.
python install_reverse_models.py --langs pt
python benchmark_bidirectional.py --mode independent --langs pt --out results/bidirectional-pt
# Rápido: dois casos por direção. Não equivale a estudo completo:
python benchmark_bidirectional.py --mode independent --langs pt --limit 2 --out smoke/bidirectional-pt

# Opcional: para 15 pares, instalando reversos disponíveis explicitamente:
python install_reverse_models.py --langs pt es fr de ja zh ar eo eu ga gl ky sw ur bn
python benchmark_bidirectional.py --mode roundtrip --out results/roundtrip-15
~~~

Ausências de modelo são registradas como erro; nunca substituídas por traduções simuladas. Para testar entrada B independente de outros idiomas, adicione corpus originalmente redigido e revisado naquele idioma ao JSON (ou use --reverse-corpus), com IDs únicos, domínio e texto, e registre procedência e revisores. Não apresente traduções geradas por modelos como material nativo humano.

## Protótipo de voz PT↔EN: um turno por vez

Fluxo em código: **microfone Streamlit → gravação WAV → faster-whisper (ASR) → Argos (MT) → Piper (TTS) → WAV reproduzível**. Não há streaming, reunião, controle de eco, múltiplos interlocutores, clonagem de voz ou desempenho simultâneo garantido.

### Instalação e execução local explícita

~~~bash
python -m pip install -r requirements-voice.txt
python install_reverse_models.py --langs pt
# Pré-download do modelo ASR: a inferência posterior usa apenas cache local:
python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
# Confira a licença e MODEL_CARD dos modelos de voz exatos antes de baixar:
python -m piper.download_voices --download-dir models/voices en_US-joe-medium pt_BR-cadu-medium
python -m streamlit run cts_voice_ui.py --server.address 127.0.0.1
~~~

O modelo original EN→PT também precisa estar instalado. Grave uma frase curta, selecione a direção e clique para transcrever, traduzir e reproduzir. O áudio passa para o servidor Streamlit que hospeda a interface; **mantenha 127.0.0.1**, não publique a interface na Internet nem grave fala sem consentimento. Após baixar modelos, a execução não faz chamada deliberada a APIs de tradução ou voz; verifique dependências e configurações da máquina.

**Licenciamento:** versões contemporâneas de Piper1-GPL usam GPLv3 e as vozes possuem licenças independentes. A documentação do projeto lista en_US-joe-medium e pt_BR-cadu-medium com dados de treinamento CC0, mas a procedência e a versão exatas do arquivo devem ser verificadas pelo MODEL_CARD antes de redistribuição/comercialização. A voz lessac tem restrição de pesquisa. Não presumir compatibilidade comercial de componentes GPL com redistribuição em produto proprietário.

## Testes e limites

~~~bash
python -m unittest discover -s tests -v
python -m compileall -q benchmark_bidirectional.py install_reverse_models.py voice_pipeline.py cts_voice_ui.py tests
~~~

Testes unitários usam fakes e **não medem qualidade real**. Para relatório científico novo, registrar pares/direções, versões/licenças, hardware, entradas originais e sintéticas, latência por etapa e p95, falhas, números, nomes, omissões, avaliação humana de tradução, transcrição de referência e WER/CER, qualidade percebida TTS e consentimento. Gravações devem permanecer privadas até decisão explícita. O Veredra permanece intocado.

## Referências técnicas

- Argos Translate: https://argos-translate.readthedocs.io/en/latest/
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- Streamlit audio input: https://docs.streamlit.io/develop/api-reference/widgets/st.audio_input
- Piper Python API: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md
- Piper voice licensing: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/LICENSING.md
- Piper commercial use: https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/COMMERCIAL_USE.md

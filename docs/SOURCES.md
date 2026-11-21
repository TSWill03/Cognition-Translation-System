# Fontes, ferramentas e status de utilização

**Ferramentas efetivamente utilizadas na execução das 300 traduções**
- Argos Translate 1.11.0: https://github.com/argosopentech/argos-translate — motor offline en→15 idiomas, pacotes de língua com versões em `model_installation.json`.
- CTranslate2 4.9.0: https://opennmt.net/CTranslate2/performance.html — runtime de inferência usado pelo Argos; sem confirmação de aceleração CUDA nesta rodada.
- Python 3.11 + biblioteca padrão: `csv`, `json`, `unittest`, `time.perf_counter`, `hashlib`; Streamlit é interface opcional, não utilizado para gerar o benchmark.

**Literatura e dados consultados, NÃO usados como motores/benchmarks no CTS-Text-300**
- Costa-jussà et al. (2024), *Scaling neural machine translation to 200 languages*, Nature. https://doi.org/10.1038/s41586-024-07335-x — estado da arte e idiomas com menos recursos.
- NLLB Team (2022), *No Language Left Behind: Scaling Human-Centered Machine Translation*. https://ai.meta.com/research/publications/no-language-left-behind-scaling-human-centered-machine-translation/ — base científica; pesos NLLB 600M têm **licença CC-BY-NC**, não utilizados: https://huggingface.co/facebook/nllb-200-distilled-600M.
- Goyal et al. (2022), *FLORES-101 Evaluation Benchmark for Low-Resource and Multilingual Machine Translation*. https://aclanthology.org/2022.tacl-1.30/ — protocolo de avaliação humana/multilingue; o conjunto FLORES-200 **não foi incorporado aos 300 casos**. https://github.com/facebookresearch/flores
- Rei et al. (2020), *COMET: A Neural Framework for MT Evaluation*. https://aclanthology.org/2020.emnlp-main.213/ — métrica de referência para trabalho futuro; **nenhum COMET score** foi calculado.
- JOSS (política editorial): https://joss.readthedocs.io/en/latest/submitting.html — sem APC, requer software de pesquisa maduro; ainda não submetemos.
- CERN/Zenodo: https://openscience.cern/doi/ — possibilidade de arquivar materiais e obter DOI gratuitamente; ainda não depositamos.

**Fontes dos dados do experimento**
- `prompts.json`: 20 frases originais criadas para o CTS (com assistência de IA; não extraídas de livros ou revistas).
- `results/translations.csv`: 300 saídas realmente produzidas pelos modelos Argos instalados.
- `results/manifest.json` / `results/summary.json`: configuração, versões, contagens e medições.
- `results/numeric_diagnostic_migration.json`: proveniência da correção do verificador de números, sem alteração das traduções.
- **Nenhum resultado de áudio, API online, modelos NLLB ou FLORES foi medido.**

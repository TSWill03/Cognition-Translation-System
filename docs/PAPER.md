# Cognition Translation System (CTS): estudo exploratório de tradução automática offline em 15 idiomas

**Autor:** Wicolly Pedro Alcântara (desenvolvedor e pesquisador independente; afiliação formal a confirmar)  
**Data do experimento:** 20 de novembro de 2026  
**Versão do estudo:** CTS Text-300 v1 / código de análise v0.3  
**Estado editorial:** manuscrito técnico preliminar, **não revisado por pares**, adequado para divulgação fundamentada após revisão autoral.  
**Dados e código:** https://github.com/TSWill03/Cognition-Translation-System

## Resumo

Este trabalho apresenta os resultados iniciais do Cognition Translation System (CTS), projeto de uma plataforma reutilizável de tradução contextual e multimodal, cuja primeira etapa experimental é exclusivamente textual. Avaliamos a execução de 300 traduções automáticas de 20 frases originais em inglês para 15 idiomas, usando o Argos Translate 1.11.0 em execução local. O protocolo inclui idiomas com diferentes sistemas de escrita e idiomas menos destacados em benchmarks de produtos convencionais, tais como esperanto, basco, irlandês, galego, quirguiz, suaíli, urdu e bengali. Todas as 300 chamadas produziram saídas não vazias sem erro de execução (300/300), mas isso **não implica correção linguística**. A mediana de inferência por frase, após aquecimento, foi de 82,932 ms (P95 empírico de 175,552 ms), enquanto a mediana de aquecimento inicial de cada idioma foi 6,927 s. Uma inspeção dos resultados evidenciou problemas potenciais de fidelidade numérica e omissões, incluindo uma alteração de US$ 12,50 para 1,50 na tradução basca de uma frase financeira. Um diagnóstico heurístico de números sinalizou 17 de 75 casos após correções de compatibilidade com algarismos Unicode, mas esses alertas exigem revisão linguística. Concluímos que a disponibilidade operacional de modelos não equivale à qualidade mensurada, e estabelecemos um protocolo aberto de avaliação humana e extensão futura para documentos e reuniões.

**Palavras-chave:** tradução automática; idiomas de menor recurso; NLP; Argos Translate; benchmark; engenharia de software; reprodutibilidade.

## 1. Introdução e motivação

A tradução automática neural permite novos fluxos de acesso ao conhecimento, mas diferenças de disponibilidade, terminologia e qualidade persistem entre idiomas. O projeto CTS surge da necessidade de traduzir textos longos, artigos e, futuramente, diálogos bidirecionais em reuniões, preservando contexto e oferecendo autonomia entre motores locais e APIs externas. O CTS não propõe, nesta etapa, um novo modelo fundacional: combina bibliotecas existentes, definição de protocolos de teste, coleta íntegra de medições e engenharia de regressão.

O projeto *No Language Left Behind* (NLLB) documenta a importância da avaliação de idiomas com menos dados e modelos multilíngues de ampla abrangência [3, 4]. A presente experiência, porém, **não utiliza os pesos NLLB**. O motor efetivamente executado foi o Argos Translate, que opera offline por pacotes de idiomas [1].

## 2. Objetivos e questões de pesquisa

O objetivo primário foi verificar, de modo reprodutível, se um conjunto real de modelos locais consegue executar traduções para idiomas tipologicamente diversos, registrando saída, latência e falhas sem transformar métricas operacionais em afirmações indevidas de qualidade.

Q1: Os 15 pares inglês→idioma de destino fornecem uma saída textual para cada um dos 20 casos de teste?  
Q2: Quanto tempo o processo de tradução leva após o carregamento do modelo, e qual é a magnitude do aquecimento inicial?  
Q3: Que problemas podem ser identificados por verificações de contrato e inspeção de exemplos, e quais limitações persistem?

## 3. Materiais e métodos

### 3.1 Ambiente e ferramentas

- **Motor avaliado:** Argos Translate 1.11.0 [1], usando CTranslate2 4.9.0 [2] e os pacotes de idioma cujas versões constam no arquivo `model_installation.json`.
- **Ambiente:** Windows, processador Intel Core i7-12700H, cerca de 42,6 GB de RAM física. Há GPU NVIDIA RTX 3050 Ti no computador, **mas o experimento não demonstra uso de GPU**.
- **Parâmetros:** `ARGOS_INTRA_THREADS=4`; `ARGOS_INTER_THREADS=1`; dispositivo padrão CPU. Traduções sequenciais por idioma, em ordem fixa.
- **Corpus:** 20 frases em inglês, redigidas especificamente para o CTS, com domínios de ciência, saúde, redes, agricultura, texto narrativo, finanças e comunicação. Não há capítulos de livros ou conteúdo privado publicado neste conjunto.
- **Idiomas de destino:** português, espanhol, francês, alemão, japonês, chinês, árabe, esperanto, basco, irlandês, galego, quirguiz, suaíli, urdu e bengali. Chamamos oito desses idiomas de *candidatos a contextos de menor disponibilidade de recursos*, e **não** os classificamos formalmente pela quantidade de falantes.
- **Matriz:** 15 destinos × 20 frases = 300 traduções executadas, uma observação por combinação, sem repetição estatística dos mesmos pares.
- **Aquecimento:** uma frase de aquecimento por modelo, cronometrada separadamente; em seguida, cronometragem de cada invocação de tradução.
- **Arquivos:** entradas `prompts.json`, resultados íntegros `results/translations.csv`, versão de modelo `model_installation.json`, metadados `results/manifest.json` e agregados `results/summary.json`.

Todas as entradas e saídas da matriz são publicadas, permitindo checagem e revisão independente. Não foram usadas referências de tradução humanas, portanto não calculamos BLEU, chrF, COMET ou métricas que dependam de referência neste estudo.

### 3.2 Variáveis e interpretação das métricas

**Execução bem-sucedida:** retorno de string não vazia sem exceção. Trata-se de robustez operacional, e não de fidelidade semântica.

**Latência após aquecimento:** tempo `perf_counter` em milissegundos por chamada individual, excluindo download, instalação e aquecimento do idioma. Resumo por mediana e percentil empírico 95. Este desenho não estima carga concorrente, desempenho em textos longos nem latência de áudio.

**Diagnóstico de valores numéricos:** comparação heurística de tokens numéricos entre origem e saída, incluindo algarismos decimais Unicode e vírgula/ponto decimal. A primeira versão produziu falsos positivos em textos com ideogramas adjacentes e algarismos bengalis; a versão **unicode_decimal_v2** recalculou apenas os diagnósticos, sem modificar tradução ou tempo. Ainda há falsos positivos quando datas, moedas ou horas mudam legitimamente de forma, ou números são escritos por extenso. A correção de um número não implica correção semântica da frase inteira.

### 3.3 Regressão e governança experimental

As entradas têm IDs fixos, o corpus tem SHA-256, a matriz é determinística, e testes automatizados verificam quantidade de casos, unicidade, correspondência com entradas originais, status, conteúdo, idioma, metadados e normalização numérica. O workflow do GitHub Actions executa testes unitários em Windows e Linux, com Python 3.11 e 3.12. Execuções neurais com modelos baixados continuam separadas do CI por custo, tempo e dependências.

## 4. Resultados

### 4.1 Cobertura operacional

Foram **300 traduções executadas com sucesso em 300 tentativas**, isto é, **15 idiomas × 20 entradas cada** e **0 exceções do motor**. Todas as saídas não vazias e seus textos de origem constam no CSV público. Essa taxa não representa precisão linguística.

### 4.2 Desempenho

| Indicador | Resultado observado |
|---|---:|
| Traduções invocadas | 300 |
| Saídas não vazias sem exceção | 300 |
| Idiomas | 15 |
| Frases de origem distintas | 20 |
| Tempo acumulado de inferência (exclui aquecimento) | 28,282 s |
| Média de inferência por frase | 94,272 ms |
| Mediana de inferência por frase | 82,932 ms |
| Percentil empírico 95 de inferência | 175,552 ms |
| Aquecimento acumulado dos 15 modelos | 107,214 s |
| Mediana de aquecimento por modelo | 6,927 s |
| Duração total registrada para o processo | 140,21 s |

O aquecimento inicial concentrou parcela significativa da duração total. Isso reforça a necessidade de distinguir *cold start* de latência de inferência ao planejar interfaces de documentos e, futuramente, reuniões. Essa observação não assegura o mesmo comportamento com outros dispositivos, modelos, quantização ou entradas longas.

### 4.3 Cobertura por idioma e tempo agregado de inferência

| Idioma | Código | Casos executados | Inferência acumulada (s) |
|---|---|---:|---:|
| Português | pt | 20 | 1,914 |
| Espanhol | es | 20 | 1,124 |
| Francês | fr | 20 | 1,680 |
| Alemão | de | 20 | 3,211 |
| Japonês | ja | 20 | 3,102 |
| Chinês | zh | 20 | 2,623 |
| Árabe | ar | 20 | 1,557 |
| Esperanto | eo | 20 | 1,897 |
| Basco | eu | 20 | 1,498 |
| Irlandês | ga | 20 | 1,367 |
| Galego | gl | 20 | 1,362 |
| Quirguiz | ky | 20 | 1,636 |
| Suaíli | sw | 20 | 1,284 |
| Urdu | ur | 20 | 2,448 |
| Bengali | bn | 20 | 1,578 |

Não é válido usar essa tabela para classificar qualidade, pois contém apenas latências e as características de tokenização/escrita diferem entre os idiomas.

### 4.4 Alertas de consistência e revisão qualitativa preliminar

Dos **75 casos com números na origem**, **17 geraram alertas pelo detector heurístico v2**. Isso não equivale a 17 erros comprovados: alguns podem decorrer de reformatação legítima. Porém, existem evidências pontuais de problemas importantes:

1. Em **CTS-eu-S19**, a frase inglesa “The price increased from $9.99 to $12.50.” gerou “Prezioa 9,99tik 1,50era igo zen.”. O segundo valor parece ter perdido o dígito 2, e o símbolo monetário não foi mantido.
2. Em **CTS-bn-S19**, o mesmo enunciado gerou “৯.৯ ডলার থেকে বাড়িয়ে ১.”, uma saída aparentemente incompleta. A confirmação da adequação linguística depende de revisão por falante competente.
3. Em **CTS-pt-S04**, “72.5 percent” foi traduzido por “72,5%”, uma adaptação regionalmente plausível que não deve ser marcada automaticamente como perda numérica.
4. Em **CTS-*-S02**, o tratamento de “Selia Fastarrow” e “Fallen Wall” variou entre preservação, transliteração e tradução. O protocolo atual não impõe glossário editorial, logo não é correto atribuir equivalência sem avaliação especializada.

A existência de casos problemáticos, inclusive com execução sem exceção, é a principal razão para não anunciar o CTS como tradutor já validado para contextos financeiros, jurídicos ou de saúde.

## 5. Discussão

O teste demonstra disponibilidade operacional real dos 15 pares de idioma examinados no catálogo Argos, mas **não demonstra que o CTS cobre mais idiomas do que todos os concorrentes**, nem uma inovação algorítmica inédita. O NLLB [3, 4], por exemplo, foi desenvolvido justamente para ampliar cobertura e avaliação multilingue. O diferencial pretendido do CTS permanece como hipótese de engenharia: motor independente, política de glossários, memória contextual, relatórios reproduzíveis e eventual processamento de reuniões.

Conforme o trabalho de avaliação humana em tradução automática [5, 6], a fluência e a adequação exigem referências e/ou especialistas. Uma futura etapa deverá empregar avaliações cegas por falantes competentes, métricas de qualidade como COMET quando aplicáveis e corpora paralelos licenciados, como o FLORES-200 [4, 5]. O NLLB-200 600M é citado como literatura de comparação, mas seus pesos publicados possuem licença **CC-BY-NC**, incompatível com pressupor uso comercial irrestrito [7]. Não foram utilizados nesta execução.

O CTS pretende futuramente oferecer tradução bidirecional de reuniões (áudio→texto→tradução→voz), porém **nenhuma captura, transcrição ou síntese de áudio foi testada neste experimento**. As 300 observações são somente de texto curto para texto.

## 6. Limitações

Amostra curta e sintética com 20 frases; único idioma de origem (inglês); 15 modelos de um mesmo mecanismo; observações singulares por combinação, sem repetições; ordem fixa dos idiomas; sem medidas de energia/custo, saturação, concorrência, BLEU/chrF/COMET ou avaliação de especialistas; latências sem processamento de arquivos, sincronização ou rede; métricas heurísticas numéricas limitadas; modelos potencialmente com diferentes domínios de treinamento; rótulos de menor disponibilidade não validados quantitativamente. O estudo não prova preservação contextual intercapítulos, superioridade a plataformas existentes nem prontidão comercial.

## 7. Conclusão e trabalho futuro

A etapa textual do CTS comprovou a execução reproduzível de 300 traduções em 15 idiomas, com logs completos e testes de regressão. Demonstrou também que *sucesso de execução não implica qualidade de tradução*, documentando casos de deformação numérica e risco de omissão. O desenvolvimento futuro deve priorizar revisores nativos e referências multilíngues, glossários por contexto, testes em documentos longos e comparação entre motores com licenças comerciais adequadas. A integração com reuniões e com o Veredra permanece proposta, não conclusão deste artigo.

## 8. Transparência, dados e declaração de uso de IA

Os scripts, corpus sintético e saídas brutas estão públicos em https://github.com/TSWill03/Cognition-Translation-System. Não foram empregados textos privados de usuários ou livros protegidos como fonte das 300 observações divulgadas. O desenvolvimento de código, o desenho da matriz, a pesquisa bibliográfica e a redação tiveram auxílio de **OpenAI ChatGPT**; as métricas e exemplos reportados foram extraídos de execução efetiva do Argos Translate, não estimados por um LLM. A assinatura autoral e afiliação institucional deverão ser confirmadas antes de submissão formal. Nenhuma revisão por pares ou validação por falantes nativos ocorreu até o momento.

## Referências

[1] ARGOS OPEN TECH. **Argos Translate: open-source offline translation library**. GitHub, documentação do projeto. https://github.com/argosopentech/argos-translate. Acesso em 20 nov. 2026.

[2] OPENNMT. **CTranslate2: Performance tips and documentation**, versão 4.9. https://opennmt.net/CTranslate2/performance.html. Acesso em 20 nov. 2026.

[3] NLLB TEAM; COSTA-JUSSÀ, Marta R. et al. **Scaling neural machine translation to 200 languages**. *Nature*, v. 630, p. 841–846, 2024. DOI: https://doi.org/10.1038/s41586-024-07335-x.

[4] META AI. **No Language Left Behind: Scaling Human-Centered Machine Translation**, 2022. https://ai.meta.com/research/publications/no-language-left-behind-scaling-human-centered-machine-translation/.

[5] GOYAL, Naman et al. **The FLORES-101 Evaluation Benchmark for Low-Resource and Multilingual Machine Translation**. *Transactions of the Association for Computational Linguistics*, 2022. https://aclanthology.org/2022.tacl-1.30/. Conjunto FLORES-200: https://github.com/facebookresearch/flores.

[6] REI, Ricardo et al. **COMET: A Neural Framework for MT Evaluation**. *Proceedings of EMNLP*, 2020. https://aclanthology.org/2020.emnlp-main.213/.

[7] META AI. **NLLB-200 distilled 600M model card**. Hugging Face, licença CC-BY-NC 4.0. https://huggingface.co/facebook/nllb-200-distilled-600M. Acesso em 20 nov. 2026.

[8] JOURNAL OF OPEN SOURCE SOFTWARE. **Submission requirements and no-fee policy**. https://joss.readthedocs.io/en/latest/submitting.html. Acesso em 20 nov. 2026.

## Possíveis canais de divulgação

- **LinkedIn:** publicar resultados operacionais, limitações e convite a revisores de idiomas, com link ao repositório.
- **Zenodo:** arquivar uma versão estável do código/dados e obter DOI gratuitamente, após criar submissão e confirmar licenças; **não é revisão por pares**.
- **JOSS:** revista sem taxas de publicação que exige software de pesquisa maduro e completo; **o protótipo atual não deve ser anunciado como elegível ou aceito** sem cumprir os requisitos de software, documentação, relevância e contribuição.

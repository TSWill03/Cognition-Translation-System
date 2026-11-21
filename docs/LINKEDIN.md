# CTS: traduções em 15 idiomas — publicação para LinkedIn

Durante os testes do Cognition Translation System (CTS), transformei um problema de tradução de livros e documentos numa pergunta maior: como construir um motor aberto, independente de um único aplicativo e preparado para diferentes idiomas?

Concluímos o primeiro experimento **exclusivamente com texto**, com **300 traduções reais**: 20 frases de diferentes domínios, traduzidas do inglês para 15 idiomas.

O conjunto inclui português, japonês, chinês, árabe, basco, irlandês, galego, esperanto, quirguiz, suaíli, urdu e bengali, além de espanhol, francês e alemão.

Executamos os testes localmente com **Argos Translate 1.11.0** e publicamos o código, os textos de origem, os resultados e o protocolo para reprodução.

**O que encontramos:**
- 300 de 300 execuções produziram uma saída de texto, sem exceção do motor.
- Mediana de 82,9 ms por frase curta, depois que cada modelo já estava carregado.
- Mediana de 6,93 segundos para aquecer um idioma.
- E o resultado mais importante: sucesso de execução **não significa** tradução correta. Encontramos casos de erro em números financeiros, alteração de nomes e possíveis omissões que precisamos investigar.

Esse ponto é essencial. Não quero apresentar a ferramenta como pronta só porque executa sem falhar. Quero construir uma base que melhore de maneira mensurável.

A visão para o **Cognition Translation System** é uma plataforma com tradução contextual para documentos, sites e, no futuro, reuniões bilíngues em tempo real. **Hoje mostramos apenas a etapa de tradução textual**, sem microfone, reconhecimento de fala ou síntese de áudio.

Estou abrindo o projeto, os dados brutos e a documentação para receber críticas, colaboradores e revisores que dominem idiomas menos frequentemente avaliados. Também quero conversar com pesquisadores, empresas e possíveis parceiros interessados em tradução acessível e engenharia de IA.

**Código, dados e artigo técnico preliminar:**
https://github.com/TSWill03/Cognition-Translation-System

Os resultados não têm revisão por pares nem avaliação formal por falantes nativos; esse é justamente um dos próximos passos.

#OpenSource #InteligenciaArtificial #NLP #MachineTranslation #Pesquisa #CTS

---

## Nota editorial

Texto preparado para revisão e publicação manual pelo autor. Os 300 testes são casos de texto curto, não 300 documentos, não 300 testes de áudio e não uma comparação de acurácia com outras plataformas. Não mencionar revista científica, certificação ou investimento já obtido.

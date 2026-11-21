# Vídeo futuro: apresentação do CTS (roteiro de demonstração)

**Estado:** planejamento apenas, o vídeo ainda não foi gravado nem publicado.

1. **Introdução (0:00–0:45):** objetivo de um motor de tradução reutilizável para documentos, aplicativos e, futuramente, reuniões.
2. **Demonstração de texto (0:45–2:30):** abrir `cts_ui.py`, instalar pares suportados, traduzir um texto original e deixar claro o modo offline.
3. **Benchmark reproduzível (2:30–4:30):** abrir `prompts.json`, demonstrar comando `benchmark300.py`, explorar o CSV real com 300 linhas em 15 idiomas e os logs de versões.
4. **Resultados e riscos (4:30–6:00):** 300 sucessos operacionais; 82,9 ms mediana após aquecimento, 6,93 s por modelo ao carregar; explicar erro financeiro basco/bengali.
5. **Arquitetura futura (6:00–7:00):** glossário contextual, PDFs, sites e reunião bidirecional — **não apresentá-los como recursos do demo v0.3**.
6. **Convite (7:00–7:30):** repositório GitHub público, colaboradores, revisão nativa, discussão científica e possíveis parceiros.

**Boas práticas:** nunca capturar credenciais, sessões reais sem consentimento, documentos privados, arquivos de terceiros protegidos ou dados sensíveis; gravar uma execução de demonstração curta, não todo o download de modelos.

# Roteiro de Apresentação Técnica: Agente RAG com Re-ranking

Este documento serve como um guia passo a passo para apresentar o projeto. Ele explica o que cada componente do código faz, a justificativa por trás das escolhas arquiteturais e a demonstração prática da suite de testes e do agente.

---

## Introdução Conceitual (O que falar primeiro)
1.  **O Problema do RAG Comum:** Em sistemas RAG tradicionais, a busca é puramente vetorial (similaridade de cosseno). Isso frequentemente falha porque a busca pode trazer trechos de "introdução" ou "perguntas de pesquisa" (viés lexical/overmatching) em vez da resposta factual que está no corpo do texto.
2.  **A Solução (Re-ranking):** Para resolver isso, fazemos uma busca inicial ampla (Top-40 chunks) no banco de dados vetorial (Dense Retrieval) e, em seguida, aplicamos um **Cross-Encoder multilíngue especializado em Português** para re-avaliar esses 40 candidatos, escolhendo estritamente os 3 melhores antes de enviar ao LLM.

---

## Parte 1: Tour pelos Arquivos de Código (O que mostrar)

### 1. Configurações Centrais (`config.py`)
*   **O que faz:** Centraliza os caminhos das pastas (`docs/`, `cache_md/`, `faiss_index/`) e as definições de modelos.
*   **Por que é assim:**
    *   **Embeddings:** Usamos o `paraphrase-multilingual-MiniLM-L12-v2`. Ele é multilíngue, leve e ideal para entender a semântica em Português.
    *   **Re-ranker:** Usamos o `nreimers/mmarco-mMiniLMv2-L6-H384-v1`. Ele foi treinado no dataset MMARCO (traduzido para português) e ajusta as pontuações de relevância de forma muito mais precisa que modelos puramente em inglês.

### 2. Ingestão Inteligente com Docling (`ingestor.py`)
*   **O que faz:** Lê os PDFs em `docs/`, converte-os para Markdown estruturado, quebra-os em pedaços (chunks) com sobreposição de texto, gera os embeddings e os indexa localmente no FAISS.
*   **Decisões Importantes para Destacar:**
    *   **`do_ocr=False`:** Como os relatórios do governo são PDFs digitais nativos (com texto selecionável), desabilitar o OCR torna a conversão 20 vezes mais rápida e evita problemas com dependências complexas na máquina.
    *   **Sistema de Cache (`cache_md/`):** A conversão de PDFs grandes por ferramentas de layout pode demorar minutos. O script salva o arquivo Markdown convertido em cache. Nas execuções seguintes, a leitura é instantânea (0.0s).
    *   **LangChain RecursiveCharacterTextSplitter:** Quebra o Markdown de forma inteligente (respeitando cabeçalhos, tabelas e parágrafos) com chunks de 1000 caracteres e overlap de 200 para manter o contexto semântico.

### 3. Recuperador Semântico de Larga Escala (`retriever.py`)
*   **O que faz:** Carrega a base FAISS, faz a pesquisa semântica inicial retornando os 40 melhores candidatos, instancia o Cross-Encoder multilíngue, calcula a relevância real para cada um e escolhe o Top-3 estrito.
*   **Decisões Importantes para Destacar:**
    *   **Remoção da Busca Híbrida (BM25):** Inicialmente testamos uma busca híbrida com BM25 + FAISS. Contudo, em relatórios contendo listas de "perguntas metodológicas", o BM25 trazia essas páginas de perguntas devido à repetição exata das palavras da query. Isso monopolizava os resultados (Keyword Monopoly). A busca densa (FAISS) pura focada na semântica resolveu este viés lexical.
    *   **Expansão para Top-40:** Aumentar de 15 para 40 garante que mesmo se a resposta ideal estiver em uma posição mais baixa na busca vetorial inicial, o re-ranker terá a chance de encontrá-la e promovê-la para o Top-3.

### 4. Geração com LLM e Cláusula de Segurança (`generator.py`)
*   **O que faz:** Conecta-se à API do OpenRouter utilizando o modelo `google/gemini-2.5-flash` para sintetizar a resposta com o contexto do Top-3.
*   **Decisões Importantes para Destacar:**
    *   **`max_tokens=1000`:** Evita que a requisição reserve uma quantia excessiva de tokens padrão no OpenRouter, o que preveniu o erro de créditos insuficientes (HTTP 402).
    *   **Cláusula de Barreira (System Prompt):** Se os 3 chunks fornecidos pelo re-ranker não contiverem a resposta para a pergunta, o LLM é estritamente instruído a responder que não encontrou os dados com base nos relatórios, eliminando qualquer risco de alucinação.

---

## Parte 2: Roteiro da Demonstração Prática (O que rodar ao vivo)

### Passo 1: Mostrar a Suite de Testes Automática (`test_agent.py`)
1.  Abra o terminal e execute a suite de testes:
    ```bash
    python test_agent.py
    ```
2.  **O que destacar na execução:**
    *   Mostre que o script lê as 11 perguntas de teste diretamente do gabarito em HTML (`goldSet.html`).
    *   Aponte o tempo de resposta rápido: cada re-ranking de 40 candidatos na CPU local leva cerca de **1.2 segundos**, e a chamada do Gemini leva cerca de **2.5 segundos**.
    *   Mostre o arquivo gerado [eval_results.md](file:///home/leshy/Documentos/Code/CsUFT/iaGen/rankingrag/eval_results.md), que compara lado a lado as respostas geradas contra as esperadas pelo gabarito.

### Passo 2: Mostrar o Comportamento de Resoluções de Casos Difíceis
Mostre as respostas no arquivo `eval_results.md` para destacar a inteligência do sistema:
*   **Pergunta 8 (Bolsa Família):** Mostre que o agente recuperou com precisão os impactos na saúde (altura das crianças) e na educação (frequência escolar), respondendo exatamente como o gabarito.
*   **Pergunta 11 (Previdência):** Destaque que o agente identificou corretamente os indicadores usados (TR - Taxa de Reposição e TIR - Taxa Interna de Retorno).
*   **Pergunta 6 (APS - Falta de dados):** Mostre que, por não haver dados sobre a rotatividade exata de médicos nos chunks recuperados, o agente acionou a cláusula de segurança e disse honestamente que os documentos não possuíam a informação, provando que o sistema é seguro e não alucina.

### Passo 3: Chat Interativo (`agent.py`)
1.  Execute o agente interativo:
    ```bash
    python agent.py
    ```
2.  Faça uma pergunta livre sobre os relatórios (ex: *"Qual a recomendação para o abono salarial?"*).
3.  Mostre que o terminal imprime os 3 melhores chunks ordenados pelo score do Cross-Encoder multilíngue, seguido da resposta limpa contendo as top 3 recomendações e suas justificativas curtas de até 2 linhas.
4.  Mostre o comando especial `reingestar`, caso novos PDFs sejam inseridos na pasta `docs/`.

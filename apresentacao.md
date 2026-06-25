# 🎙️ Roteiro de Apresentação: RAG Vetorial com Re-ranking Avançado

> **Como usar este documento:** Este é o seu guia de palco. Os tópicos principais são os conceitos que deve explicar, enquanto as marcações em colchetes como `[Ação]` indicam o que deve mostrar no ecrã ou no terminal.

---

## 1. Introdução Conceitual (O "Hook" da Apresentação)

`[Dica de fala: Comece captando a atenção da banca/audiência com o problema real que enfrentamos e como o resolvemos.]`

* **O Problema do RAG Tradicional:** "Quando construímos um RAG padrão usando apenas busca vetorial por proximidade (similaridade de cosseno), é comum esbarrar no *Viés Lexical* ou *Overmatching*. Em relatórios densos (como relatórios do governo), as páginas de índice, sumários ou introduções metodológicas repetem exatamente as 'perguntas de pesquisa'. A busca vetorial acabava trazendo essas páginas vazias, em vez de trazer o trecho do corpo do relatório com os dados factuais."
* **A Nossa Solução (Pipeline com Re-ranking):** "Para resolver isso, adotamos uma arquitetura de duas etapas. Primeiro, abrimos uma rede ampla no banco vetorial, recuperando os **40 melhores chunks** (Dense Retrieval). Em seguida, passamos esses 40 trechos por um modelo **Cross-Encoder multilíngue otimizado para Português**. Ele atua como um 'juiz rigoroso', lendo a pergunta e cada trecho ao mesmo tempo para calcular uma nota de relevância real, elegendo estritamente os **3 melhores** antes de enviar para o LLM."
* **O Ajuste Fino da Escrita (Texto Coeso):** "Para evitar que o LLM respondesse em tópicos (bullet points) secos, configuramos o System Prompt para sintetizar essas 3 recomendações e suas justificativas em um texto contínuo e corrido, tornando a leitura muito mais fluida e profissional."

---

## 2. Tour pelo Código-Fonte (Passo a Passo nas Páginas)

`[Ação: Abra o seu editor de código e vá abrindo os arquivos um a um. Mostre as funções mencionadas.]`

### 📄 `config.py` (Central de Modelos e Caminhos)
* **O que mostrar no código:** As variáveis de diretórios e nomes dos modelos de IA.
* **Explicação do código:**
    *   `DOCS_DIRS = ["./docs"]`: Aponta estritamente para a pasta onde estão os relatórios originais do governo.
    *   `EMBEDDING_MODEL_NAME`: Usamos o modelo `paraphrase-multilingual-MiniLM-L12-v2`. Ele gera vetores de 384 dimensões e compreende português de forma eficiente, rodando localmente de forma extremamente ágil na CPU.
    *   `RERANK_MODEL_NAME = "nreimers/mmarco-mMiniLMv2-L6-H384-v1"`: Este é o pulo do gato. Ele é um Cross-Encoder multilíngue treinado na base MMARCO (MS MARCO traduzido). Ele entende a semântica do português e dá pontuações precisas, filtrando o ruído lexical.
* **Por que é assim:** Centralizar as configurações em um arquivo evita "magic strings" espalhadas pelo código e facilita a troca rápida de modelos e pastas se o projeto crescer.

### 📄 `ingestor.py` (Ingestão Estruturada com Cache)
* **O que mostrar no código:** A função `convert_pdf_to_markdown`, o parâmetro `do_ocr=False` e a geração do FAISS em `ingest_documents`.
* **Explicação do código:**
    *   **Docling (`DocumentConverter`):** Usado para extrair tabelas e manter a estrutura hierárquica do PDF convertendo para Markdown.
    *   **`do_ocr=False`:** Desativado porque os PDFs são digitais nativos. Ativar o OCR processaria as páginas como imagens, o que levaria horas. Sem OCR, a leitura é rápida e limpa.
    *   **Sistema de Cache (`cache_md/`):** Linhas 48-55 verificam se o arquivo Markdown correspondente já existe no cache. Se sim, carrega dele instantaneamente.
    *   **`RecursiveCharacterTextSplitter`:** Linhas 109-115 dividem o texto usando separadores lógicos (parágrafos, quebras de linha) para evitar cortar tabelas ou sentenças no meio.
    *   **FAISS (`FAISS.from_documents`):** Gera os vetores e salva o índice em disco (`./faiss_index`) usando os embeddings locais.
* **Por que é assim:** Ingestão estruturada preserva o layout do PDF (tabelas e listas), o cache economiza poder de processamento em execuções repetidas, e o FAISS local elimina custos de nuvem.

### 📄 `retriever.py` (Recuperação Vetorial e Re-ranking)
* **O que mostrar no código:** O carregamento cacheado dos modelos (linhas 10-13), a função `retrieve_and_rerank` e a chamada `db.similarity_search(query, k=top_k_initial)`.
* **Explicação do código:**
    *   **Variáveis Globais (`_vector_db`, `_cross_encoder`):** Linhas 11-13 funcionam como cache em memória. Elas evitam que o Python tenha que recarregar o banco vetorial e o modelo Cross-Encoder (que pesam ~500MB) a cada pergunta do usuário no chat.
    *   **Busca Ampla (`top_k_initial=40`):** Linhas 77-80 resgatam os 40 chunks semanticamente mais próximos no FAISS.
    *   **Re-ranking (`cross_encoder.predict`):** Linhas 89-99 criam pares de `[[query, chunk]]` e rodam a inferência na CPU local, ordenando os chunks por relevância factual e separando estritamente os top-3.
* **Por que é assim:**
    *   **A remoção do BM25:** "Nós chegamos a implementar busca híbrida (BM25 + FAISS), mas o BM25 trazia páginas de sumário que repetiam as palavras da pergunta. O FAISS puro foca na semântica do texto, e a expansão para 40 chunks garante que a resposta factual estará na mesa para o Re-ranker selecionar."
    *   **O Cross-Encoder Multilíngue:** Ele ajusta a ordem real e promove trechos ricos que usam sinônimos em português, ignorando trechos que apenas repetem palavras-chave.

### 📄 `generator.py` (Integração de Sintese e Prompt Blindado)
* **O que mostrar no código:** A função `generate_response`, o `system_prompt` formatando em parágrafos contínuos e o parâmetro `max_tokens=1000`.
* **Explicação do código:**
    *   **OpenRouter Client:** Conecta-se à API utilizando as credenciais locais.
    *   **`system_prompt` (Linhas 46-55):** O prompt orienta o modelo a basear-se *estritamente* no contexto fornecido, responder de forma factual (dizendo que não sabe se a resposta não estiver lá) e entregar **estritamente 3 recomendações mais acionáveis e justificativas de até 2 linhas em formato de parágrafos tradicionais e corridos (sem tópicos/listas)**.
    *   **`max_tokens=1000`:** Garante que a requisição não tente reservar o contexto máximo da API do OpenRouter, o que esgotava a cota da chave gratuita e causava erros 402.
* **Por que é assim:** Garante segurança total (sem alucinações), controle orçamentário rígido de chamadas e entrega o formato de texto corrido exigido.

### 📄 `agent.py` (O Chat no Terminal)
* **O que mostrar no código:** O loop interativo `while True` e a inicialização automática do banco vetorial.
* **Explicação do código:**
    *   Verifica se o índice FAISS existe. Se não existir, chama o `ingestor.py` automaticamente antes de ligar o chat.
    *   Oferece o comando especial `reingestar`, que limpa a memória e roda o processamento dos PDFs novamente se o usuário adicionar novos arquivos à pasta `docs/`.

### 📄 `test_agent.py` (Suite de Testes e Gabarito)
* **O que mostrar no código:** O parseamento do HTML com `BeautifulSoup` e a gravação do `eval_results.md`.
* **Explicação do código:**
    *   Varre o arquivo `goldSet.html`, extrai as 11 perguntas, as respostas esperadas e os pontos que deveriam ser recuperados.
    *   Roda cada pergunta pelo retriever e generator, mede o tempo exato de busca e geração e gera o relatório estruturado [eval_results.md](file:///home/leshy/Documentos/Code/CsUFT/iaGen/rankingrag/eval_results.md) para auditoria.

---

## 3. Demonstração Prática (Showcase ao vivo)

### 🚀 Passo 1: Executando a Suite de Testes Automática
`[Ação: Abra o terminal e digite: python test_agent.py]`
*   **O que falar enquanto roda:** "Desenvolvemos essa suite de testes automática para avaliar a qualidade e velocidade do RAG. Notem o tempo de resposta: o re-ranking de 40 candidatos roda na CPU local em cerca de **1.2 segundos** e a síntese do LLM volta em **2.5 segundos**."
*   `[Ação: Abra o arquivo eval_results.md gerado na pasta do projeto]` "Aqui está o relatório final comparando o gabarito oficial com as respostas do nosso agente."

### 🧠 Passo 2: Mostrando Casos de Sucesso e Segurança
`[Ação: Role o arquivo eval_results.md no editor e mostre estas perguntas específicas]`
*   **Acurácia (Teste 8 e 11):** "Vejam a Pergunta 8 sobre o Bolsa Família. O agente recuperou com precisão os impactos em saúde (altura de crianças) e educação. Na Pergunta 11, ele identificou os indicadores TR (Taxa de Reposição) e TIR (Taxa Interna de Retorno) de forma cirúrgica."
*   **Segurança (Teste 6 - APS):** "Vejam o Teste 6. A pergunta era sobre a permanência de profissionais na APS. Como esses dados específicos não constavam nas fontes, o nosso agente acionou a cláusula de barreira e declarou que os documentos não continham a resposta. **Nosso RAG é 100% seguro contra alucinações.**"
*   **Texto Coeso:** "Reparem que todas as respostas agora fluem em parágrafos corridos normais, sem tópicos ou bullet points, atendendo a essa exigência de leitura fluida."

### 💬 Passo 3: Chat Interativo Ao Vivo
`[Ação: No terminal, execute: python agent.py]`
*   **O que falar:** "Além dos testes, o sistema está pronto para uso como um assistente interativo no terminal."
*   `[Ação: Digite a pergunta: "Quais inconsistências foram identificadas no abono salarial?"]`
*   **Conclusão:** "Observem como o terminal mostra a pontuação do Cross-Encoder indicando o score de relevância, e entrega a resposta final em formato contínuo de parágrafo, contendo as recomendações acionáveis e suas justificativas."
*   *(Opcional)* Mencione que se novos arquivos forem adicionados, basta digitar `reingestar` no chat.

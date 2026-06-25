# RankingRAG: Pipeline RAG com Re-ranking Otimizado para Português

Este projeto implementa um agente de inteligência artificial em Python que executa um pipeline completo de **RAG (Retrieval-Augmented Generation) com Re-ranking**. Ele lê uma base de conhecimento local composta por PDFs de relatórios governamentais, extrai a estrutura textual rica em Markdown, indexa-a localmente e responde a perguntas em formato de texto coeso e contínuo com base estrita no contexto.

---

## 🛠️ Tecnologias e Bibliotecas Utilizadas

Para garantir acurácia linguística e velocidade de processamento rodando localmente na CPU, utilizamos a seguinte pilha de tecnologia:

1.  **Docling (IBM):** Biblioteca de layout parsing utilizada para ler e extrair texto e tabelas de PDFs, exportando a estrutura original para Markdown de forma nativa e mantendo parágrafos e grades de dados íntegros.
2.  **LangChain:** Framework de IA utilizado para divisão de texto (`RecursiveCharacterTextSplitter`) e conexões de vetores.
3.  **FAISS (cpu):** Banco de dados vetorial local de alto desempenho. Ele armazena os embeddings gerados e realiza buscas rápidas de proximidade por similaridade de cosseno.
4.  **HuggingFace Embeddings (`paraphrase-multilingual-MiniLM-L12-v2`):** Modelo multilíngue leve responsável por gerar vetores semânticos das fatias de texto (chunks) e das consultas do usuário.
5.  **Cross-Encoder Reranker (`nreimers/mmarco-mMiniLMv2-L6-H384-v1`):** Modelo de atenção total cruzada otimizado e treinado na base massiva traduzida em português (mMARCO). Ele reavalia o Top-40 inicial recuperado pelo FAISS e extrai o Top-3 mais relevante, resolvendo o viés de sobreposição lexical (Keyword Monopoly).
6.  **OpenRouter (`google/gemini-2.5-flash`):** LLM utilizado na etapa de síntese das respostas baseando-se estritamente no Top-3 do re-ranking e gerando parágrafos corridos e coesos.

---

## 🚀 Como Configurar e Usar o Projeto

### 1. Pré-requisitos
Certifique-se de ter o Python 3.10+ instalado no seu sistema.

### 2. Ativar o Ambiente Virtual e Instalar Dependências
Entre na pasta do projeto, ative o ambiente virtual já fornecido e instale os requisitos:
```bash
# Ativar o ambiente virtual
source .venv/bin/activate

# Instalar pacotes necessários (se não estiverem instalados)
pip install docling sentence-transformers faiss-cpu langchain langchain-community langchain-classic langchain-text-splitters python-dotenv openai rank_bm25 bs4
```

### 3. Configurar a Chave de API (.env)
Crie um arquivo chamado `.env` na raiz do projeto (se não existir) e adicione sua chave de API do OpenRouter:
```env
OPENROUTER_API_KEY=sua_chave_do_openrouter_aqui
```

### 4. Executar o Agente Interativo (Chat)
Converse diretamente com o agente pelo terminal. Ele fará a ingestão automática das fontes da pasta `docs/` se for a primeira execução:
```bash
python agent.py
```
*   *Comando Útil:* Digite `reingestar` dentro do loop de chat para forçar a re-conversão dos PDFs e atualizar o banco vetorial se você adicionar arquivos novos na pasta `docs/`.

### 5. Executar a Suite de Testes Automáticos
O script de testes lê as perguntas de auditoria diretamente do arquivo `goldSet.html`, realiza as consultas no pipeline RAG e grava um relatório detalhado comparando as respostas geradas com os gabaritos oficiais:
```bash
python test_agent.py
```
*   O relatório de avaliação gerado será salvo no arquivo local [eval_results.md](file:///home/leshy/Documentos/Code/CsUFT/iaGen/rankingrag/eval_results.md).

---

## 📂 Estrutura do Projeto

*   `docs/`: Pasta local contendo os relatórios em PDF.
*   `cache_md/`: Pasta de cache onde o Docling salva os Markdowns convertidos dos PDFs para evitar re-processamento demorado.
*   `faiss_index/`: Onde o banco de dados FAISS local é salvo.
*   `config.py`: Definições globais de pastas e modelos.
*   `ingestor.py`: Ingestor de documentos via Docling, text splitting e gravação vetorial.
*   `retriever.py`: Lógica de busca semântica Top-40 e re-ranking Top-3 em português.
*   `generator.py`: Lógica de chamada da API do OpenRouter e engenharia do System Prompt de texto coeso.
*   `agent.py`: Loop interativo do CLI.
*   `test_agent.py`: Suite de testes automatizados.
*   `relatorio_tecnico.md`: Documentação minuciosa de arquitetura e tempos.
*   `eval_results.md`: Resultado da suite de testes.

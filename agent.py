import os
import sys
import argparse
from typing import List

import config
import ingestor
import retriever
import generator

def run_ingestion_pipeline():
    """
    Orchestrates the ingestion of PDFs.
    """
    print("\n" + "="*60)
    print("INICIANDO INGESTÃO E PROCESSAMENTO DE DOCUMENTOS")
    print("="*60)
    
    # Ensure source directories exist
    for d in config.DOCS_DIRS:
        os.makedirs(d, exist_ok=True)
        
    try:
        success = ingestor.ingest_documents()
        if success:
            print("\n Ingestão concluída com sucesso! Banco vetorial atualizado.")
            return True
        else:
            print("\n Ingestão falhou ou nenhum documento foi processado.")
            return False
    except Exception as e:
        print(f"\n Erro crítico durante a ingestão: {e}")
        return False

def show_welcome():
    print("""
======================================================================
               AGENTE RAG DE RE-RANKING POR ANTIGRAVITY
======================================================================
Este agente lê os documentos locais, gera embeddings, busca os top-15
trechos mais relevantes, aplica o Re-ranking (Cross-Encoder) para obter
os top-3 e sintetiza as principais recomendações com o LLM.

Comandos Especiais:
  'sair' ou 'exit'  - Encerra o agente
  'reingestar'      - Processa os documentos novamente (atualiza o banco)
======================================================================
""")

def main():
    parser = argparse.ArgumentParser(description="Agente RAG com Re-ranking e Docling")
    parser.add_argument("--force-ingest", action="store_true", help="Força o processamento dos documentos antes de iniciar")
    args = parser.parse_args()
    
    # 1. Check API Key
    if not config.OPENROUTER_API_KEY:
        print("ERRO CRÍTICO: OPENROUTER_API_KEY não foi encontrada.")
        print("Por favor, configure sua chave no arquivo .env na raiz do projeto:")
        print("OPENROUTER_API_KEY=sua_chave_aqui")
        sys.exit(1)
        
    # 2. Check Database or Run Ingestion
    db_exists = os.path.exists(os.path.join(config.FAISS_DB_PATH, "index.faiss"))
    
    if args.force_ingest or not db_exists:
        if not db_exists:
            print("Banco de dados FAISS não encontrado. Iniciando ingestão automática...")
        else:
            print("Forçando ingestão conforme solicitado...")
            
        success = run_ingestion_pipeline()
        if not success:
            if not db_exists:
                print("ERRO: Não foi possível criar a base de dados vetorial. O agente não pode iniciar.")
                sys.exit(1)
            else:
                print("AVISO: A re-ingestão falhou. Tentando iniciar com o banco de dados existente.")

    # 3. Verify that DB exists now
    try:
        retriever.load_vector_db()
        print("Banco de dados vetorial carregado com sucesso.")
    except Exception as e:
        print(f"Erro ao carregar o banco de dados vetorial: {e}")
        print("Verifique se você colocou arquivos PDF na pasta 'docs' ou 'documentos' e execute novamente.")
        sys.exit(1)
        
    show_welcome()
    
    # 4. Interactive Loop
    while True:
        try:
            query = input("\nPergunta: ").strip()
            
            if not query:
                continue
                
            if query.lower() in ["sair", "exit", "quit"]:
                print("Encerrando o agente. Até logo!")
                break
                
            if query.lower() == "reingestar":
                run_ingestion_pipeline()
                # Clear cached vector database to force reload
                retriever._vector_db = None
                continue
                
            print("\n[1/3] Buscando trechos relevantes e executando Re-ranking...")
            top_chunks = retriever.retrieve_and_rerank(query, top_k_initial=40, top_k_final=3)
            
            if not top_chunks:
                print("\n[AVISO] Nenhum trecho relevante foi retornado pelo sistema de busca.")
                print("Por favor, verifique se a pergunta está alinhada com o conteúdo dos documentos.")
                continue
                
            print("[2/3] Enviando os 3 melhores trechos selecionados para o LLM...")
            response = generator.generate_response(query, top_chunks)
            
            print("\n[3/3] Resposta da IA:")
            print("-" * 80)
            print(response)
            print("-" * 80)
            
            # Print sources for verification
            print("\nFontes utilizadas:")
            sources = set()
            for doc, score in top_chunks:
                filename = doc.metadata.get("filename", "Desconhecido")
                sources.add(filename)
            for src in sources:
                print(f"  - {src}")
                
        except KeyboardInterrupt:
            print("\nEncerrando o agente. Até logo!")
            break
        except Exception as e:
            print(f"\nOcorreu um erro inesperado: {e}")

if __name__ == "__main__":
    main()

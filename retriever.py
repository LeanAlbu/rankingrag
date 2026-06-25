import os
from typing import List, Tuple, Dict, Any
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

import config

# Global variables for caching models in memory
_embeddings = None
_vector_db = None
_cross_encoder = None

def load_embeddings() -> HuggingFaceEmbeddings:
    """
    Loads and caches the embedding model in memory.
    """
    global _embeddings
    if _embeddings is None:
        print(f"Loading embedding model for retrieval: {config.EMBEDDING_MODEL_NAME}...")
        _embeddings = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL_NAME,
            model_kwargs={'device': 'cpu'}
        )
    return _embeddings

def load_vector_db() -> FAISS:
    """
    Loads the FAISS index from disk.
    """
    global _vector_db
    if _vector_db is None:
        if not os.path.exists(os.path.join(config.FAISS_DB_PATH, "index.faiss")):
            raise FileNotFoundError(
                f"FAISS index not found at '{config.FAISS_DB_PATH}'. "
                f"Please run Ingestion first to build the database."
            )
        embeddings = load_embeddings()
        print(f"Loading FAISS index from '{config.FAISS_DB_PATH}'...")
        _vector_db = FAISS.load_local(
            config.FAISS_DB_PATH, 
            embeddings, 
            allow_dangerous_deserialization=True
        )
    return _vector_db

def load_cross_encoder() -> CrossEncoder:
    """
    Loads and caches the Cross-Encoder model in memory.
    """
    global _cross_encoder
    if _cross_encoder is None:
        print(f"Loading Cross-Encoder model: {config.RERANK_MODEL_NAME}...")
        _cross_encoder = CrossEncoder(config.RERANK_MODEL_NAME, device='cpu')
    return _cross_encoder

def retrieve_and_rerank(
    query: str, 
    top_k_initial: int = 40, 
    top_k_final: int = 3
) -> List[Tuple[Document, float]]:
    """
    Performs standard vector search (FAISS) followed by Cross-Encoder re-ranking.
    Returns: List of tuples (Document, re-ranking_score) sorted by score.
    """
    try:
        db = load_vector_db()
        cross_encoder = load_cross_encoder()
    except FileNotFoundError as e:
        print(f"Retrieval Error: {e}")
        return []
    except Exception as e:
        print(f"Error loading models or database: {e}")
        return []
        
    print(f"Performing vector similarity search for top-{top_k_initial} chunks...")
    try:
        # Retrieve the top-K chunks using similarity search
        retrieved_docs = db.similarity_search(query, k=top_k_initial)
    except Exception as e:
        print(f"Error during similarity search: {e}")
        return []
        
    if not retrieved_docs:
        print("Vector search returned zero results.")
        return []
        
    print(f"Re-ranking {len(retrieved_docs)} chunks using Cross-Encoder ({config.RERANK_MODEL_NAME})...")
    try:
        # Prepare pairs for cross-encoder evaluation: (query, text)
        pairs = [[query, doc.page_content] for doc in retrieved_docs]
        
        # Predict relevancy scores (higher score means more relevant)
        scores = cross_encoder.predict(pairs)
        
        # Pair documents with their scores and sort in descending order
        doc_score_pairs = list(zip(retrieved_docs, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # Take the top_k_final chunks
        final_docs = doc_score_pairs[:top_k_final]
        
        print("\nTop 3 Re-ranked Chunks (after semantic search):")
        for idx, (doc, score) in enumerate(final_docs, 1):
            source = doc.metadata.get('filename', 'Unknown')
            snippet = doc.page_content[:60].replace('\n', ' ')
            print(f"  {idx}. [Score: {score:.4f}] [{source}] {snippet}...")
            
        return final_docs
    except Exception as e:
        print(f"Error during re-ranking: {e}")
        # In case of failure, return the top-K from similarity search with mock scores
        return [(doc, 0.0) for doc in retrieved_docs[:top_k_final]]

if __name__ == "__main__":
    # Test execution
    test_query = "Qual a recomendação para o abono salarial?"
    results = retrieve_and_rerank(test_query)
    if results:
        print(f"\nRetrieved {len(results)} docs for '{test_query}'")
    else:
        print("Could not retrieve documents. Ensure the database is created.")

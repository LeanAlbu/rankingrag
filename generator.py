import os
from typing import List, Tuple
from openai import OpenAI
from langchain_core.documents import Document

import config

def get_openai_client() -> OpenAI:
    """
    Initializes and returns the OpenAI client configured for OpenRouter.
    """
    if not config.OPENROUTER_API_KEY or not config.OPENROUTER_API_KEY.strip():
        raise ValueError(
            "OPENROUTER_API_KEY is not set. Please set it in your .env file."
        )
    
    return OpenAI(
        base_url=config.OPENROUTER_BASE_URL,
        api_key=config.OPENROUTER_API_KEY,
    )

def generate_response(
    query: str, 
    contexts_with_scores: List[Tuple[Document, float]]
) -> str:
    """
    Constructs the prompt, calls the LLM with the context, and returns the response.
    """
    if not contexts_with_scores:
        return (
            "Não foi possível encontrar informações relevantes nos documentos "
            "para responder a essa pergunta."
        )
        
    # Format the context from top chunks
    formatted_contexts = []
    for idx, (doc, score) in enumerate(contexts_with_scores, 1):
        filename = doc.metadata.get("filename", "desconhecido")
        content = doc.page_content.strip()
        formatted_contexts.append(
            f"--- Contexto {idx} (Origem: {filename}, Score Re-ranking: {score:.4f}) ---\n{content}"
        )
        
    context_text = "\n\n".join(formatted_contexts)
    
    system_prompt = (
        "Você é um assistente de IA especializado. Responda estritamente com base nos documentos fornecidos. "
        "Não invente informações e não use conhecimento externo que não esteja presente nos documentos. "
        "Se o contexto fornecido não contiver informações suficientes para responder à pergunta, diga claramente "
        "que não encontrou a resposta com base estrita nos documentos fornecidos.\n\n"
        "A partir do contexto fornecido, extraia as informações e entregue ESTRITAMENTE as top 3 recomendações "
        "mais acionáveis formatadas em um texto corrido, contínuo e coeso (parágrafos tradicionais, SEM o uso de listas, hífens, asteriscos ou bullet points). "
        "Para cada recomendação, inclua de forma natural no fluxo do texto uma justificativa curta (máximo de 2 linhas) explicando sua viabilidade no curto prazo."
    )
    
    user_prompt = f"Pergunta: {query}\n\nContexto dos Documentos:\n{context_text}"
    
    try:
        client = get_openai_client()
        print(f"Sending query to OpenRouter using model '{config.LLM_MODEL}'...")
        
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            # extra headers recommended for OpenRouter
            extra_headers={
                "HTTP-Referer": "https://github.com/google/deepmind", # Site name
                "X-Title": "Antigravity RAG Agent", 
            },
            temperature=0.1, # Keep it deterministic and factual
            max_tokens=1000,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        error_msg = f"Erro na chamada do LLM (OpenRouter): {e}"
        print(error_msg)
        return f"Desculpe, ocorreu um erro ao gerar a resposta. Detalhes: {e}"

if __name__ == "__main__":
    # Test execution
    mock_doc = Document(
        page_content="Recomendação 1: Implementar sistema automatizado de triagem de abono salarial para reduzir o tempo de resposta.\n"
                     "Recomendação 2: Realizar treinamentos semanais para a equipe técnica sobre as novas normas da previdência.\n"
                     "Recomendação 3: Unificar os cadastros do PBF e BPC em uma única plataforma digital para evitar pagamentos duplicados.\n"
                     "Recomendação 4: Ampliar a distribuição de merenda escolar descentralizada.",
        metadata={"filename": "relatorio_teste.pdf"}
    )
    res = generate_response("Quais as recomendações acionáveis?", [(mock_doc, 0.95)])
    print("\nLLM Response:\n", res)

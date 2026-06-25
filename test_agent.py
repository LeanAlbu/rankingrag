import os
import time
from bs4 import BeautifulSoup
import retriever
import generator

def parse_gold_set(html_path: str):
    """
    Parses the goldSet.html file and extracts questions, expected answers, and expected recovery points.
    """
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")
        
    sections = soup.find_all("div", class_="section")
    
    test_cases = []
    
    # We want to trace the topic based on headers or order
    # Let's map sections
    for sec in sections:
        h2 = sec.find("h2")
        if not h2:
            continue
            
        p_tags = sec.find_all("p")
        if len(p_tags) < 2:
            continue
            
        # First <p> is usually the question text wrapped in <strong>
        q_strong = p_tags[0].find("strong")
        if not q_strong:
            continue
        question = q_strong.get_text().strip()
        
        # Second <p> is usually "Resposta esperada", and the third is the text
        expected_answer = ""
        for i, p in enumerate(p_tags):
            if "Resposta esperada" in p.get_text():
                if i + 1 < len(p_tags):
                    expected_answer = p_tags[i+1].get_text().strip()
                    break
        
        # Find expected recovery bullet points
        expected_recovery = []
        ul = sec.find("ul")
        if ul:
            expected_recovery = [li.get_text().strip() for li in ul.find_all("li")]
            
        # Try to guess the document topic from context or headers
        topic = "Geral"
        # We can guess topic by checking keywords in the question
        q_lower = question.lower()
        if "mac" in q_lower or "média e alta complexidade" in q_lower:
            topic = "MAC (Média e Alta Complexidade)"
        elif "abono" in q_lower:
            topic = "Abono Salarial"
        elif "atenção primária" in q_lower or "aps" in q_lower:
            topic = "Atenção Primária à Saúde (APS)"
        elif "bolsa família" in q_lower or "pbf" in q_lower:
            topic = "Programa Bolsa Família (PBF)"
        elif "pnae" in q_lower or "alimentação escolar" in q_lower:
            topic = "PNAE (Alimentação Escolar)"
        elif "previdenciário" in q_lower or "rgps" in q_lower or "rpps" in q_lower:
            topic = "Previdência (RGPS/RPPS)"
            
        test_cases.append({
            "id": sec.get("id", "sec"),
            "title": h2.get_text().strip(),
            "topic": topic,
            "question": question,
            "expected_answer": expected_answer,
            "expected_recovery": expected_recovery
        })
        
    return test_cases

def run_tests():
    html_path = "goldSet.html"
    if not os.path.exists(html_path):
        print(f"Error: {html_path} not found.")
        return
        
    print(f"Loading and parsing test cases from '{html_path}'...")
    test_cases = parse_gold_set(html_path)
    print(f"Found {len(test_cases)} test cases.")
    
    results = []
    
    # Pre-load DB and Cross-Encoder to avoid counting load time in first test case
    print("Pre-loading Vector Database and Re-ranker model...")
    start_load = time.time()
    retriever.load_vector_db()
    retriever.load_cross_encoder()
    load_time = time.time() - start_load
    print(f"Model load time: {load_time:.2f}s")
    
    for idx, tc in enumerate(test_cases, 1):
        print(f"\n--- Running Test {idx}/{len(test_cases)}: {tc['title']} ({tc['topic']}) ---")
        print(f"Q: {tc['question']}")
        
        # 1. Retrieval + Re-ranking
        start_ret = time.time()
        top_chunks = retriever.retrieve_and_rerank(tc['question'], top_k_initial=40, top_k_final=3)
        ret_time = time.time() - start_ret
        
        # 2. LLM Generation
        start_gen = time.time()
        generated_answer = generator.generate_response(tc['question'], top_chunks)
        gen_time = time.time() - start_gen
        
        print(f"Retrieved in {ret_time:.3f}s. Generated in {gen_time:.3f}s.")
        print("-" * 50)
        print(generated_answer)
        print("-" * 50)
        
        sources = [doc.metadata.get("filename", "unknown") for doc, _ in top_chunks]
        scores = [score for _, score in top_chunks]
        
        results.append({
            "index": idx,
            "topic": tc['topic'],
            "question": tc['question'],
            "expected_answer": tc['expected_answer'],
            "expected_recovery": tc['expected_recovery'],
            "generated_answer": generated_answer,
            "retrieval_time": ret_time,
            "generation_time": gen_time,
            "sources": sources,
            "scores": scores
        })
        
    # Write Markdown Evaluation Report
    report_path = "/home/leshy/.gemini/antigravity-cli/brain/d9fe674b-7a79-4b31-80f4-a6b79027efbc/eval_results.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Relatório de Avaliação do Agente RAG com Re-ranking\n\n")
        f.write("Este relatório contém os resultados dos testes automatizados utilizando as perguntas e respostas esperadas do arquivo `goldSet.html`.\n\n")
        
        # Summary of times
        avg_ret = sum(r['retrieval_time'] for r in results) / len(results)
        avg_gen = sum(r['generation_time'] for r in results) / len(results)
        
        f.write("## 1. Resumo do Desempenho Temporal\n")
        f.write(f"- **Tempo de Carregamento Inicial (Modelos & DB)**: {load_time:.2f} segundos\n")
        f.write(f"- **Tempo Médio de Recuperação + Re-ranking**: {avg_ret:.3f} segundos\n")
        f.write(f"- **Tempo Médio de Geração (LLM)**: {avg_gen:.3f} segundos\n")
        f.write(f"- **Tempo Médio Total por Pergunta**: {avg_ret + avg_gen:.3f} segundos\n\n")
        
        f.write("## 2. Detalhes dos Casos de Teste\n\n")
        
        for r in results:
            f.write(f"### Teste {r['index']}: {r['question']}\n\n")
            f.write(f"**Área Temática**: {r['topic']}\n\n")
            f.write(f"**Tempo de Execução**:\n")
            f.write(f"- Busca e Re-ranking: `{r['retrieval_time']:.3f}s`\n")
            f.write(f"- Geração LLM: `{r['generation_time']:.3f}s`\n\n")
            
            f.write("**Documentos Utilizados (Top 3 Re-ranked)**:\n")
            for src, score in zip(r['sources'], r['scores']):
                f.write(f"- `{src}` (Score de relevância: `{score:.4f}`)\n")
            f.write("\n")
            
            f.write("**Resposta Esperada (Gabarito)**:\n")
            f.write(f"> {r['expected_answer']}\n\n")
            
            f.write("**Pontos que deveriam ser recuperados**:\n")
            for pt in r['expected_recovery']:
                f.write(f"- {pt}\n")
            f.write("\n")
            
            f.write("**Resposta Gerada pelo Agente (Strict Top 3 Recomendações)**:\n")
            f.write("```markdown\n")
            f.write(f"{r['generated_answer']}\n")
            f.write("```\n")
            f.write("\n" + "-"*80 + "\n\n")
            
    print(f"Evaluation report successfully written to '{report_path}'")

if __name__ == "__main__":
    run_tests()

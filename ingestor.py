import os
import glob
from typing import List, Dict, Any
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

import config

def get_pdf_files() -> List[str]:
    """
    Finds all PDF files in the configured search directories.
    """
    pdf_files = []
    for directory in config.DOCS_DIRS:
        if os.path.exists(directory):
            # Find all pdfs recursively or directly
            pattern = os.path.join(directory, "**", "*.pdf")
            found = glob.glob(pattern, recursive=True)
            pdf_files.extend(found)
            print(f"Found {len(found)} PDFs in '{directory}'")
    
    # Remove duplicates preserving order
    seen = set()
    unique_files = []
    for f in pdf_files:
        abs_path = os.path.abspath(f)
        if abs_path not in seen:
            seen.add(abs_path)
            unique_files.append(f)
            
    return unique_files

def convert_pdf_to_markdown(pdf_path: str) -> str:
    """
    Converts a single PDF to markdown using Docling, with caching.
    """
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    
    # Generate cached md file path
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    md_path = os.path.join(config.CACHE_DIR, f"{base_name}.md")
    
    # If cached version exists and is not empty, use it
    if os.path.exists(md_path) and os.path.getsize(md_path) > 0:
        print(f"Loading '{pdf_path}' from cache: '{md_path}'")
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading cache for '{pdf_path}': {e}. Re-converting...")

    # Configure Docling
    print(f"Converting '{pdf_path}' using Docling DocumentConverter...")
    try:
        pipeline_options = PdfPipelineOptions(do_ocr=False)
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        result = converter.convert(pdf_path)
        markdown_content = result.document.export_to_markdown()
        
        # Save to cache
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"Successfully converted and cached: '{md_path}'")
        return markdown_content
    except Exception as e:
        print(f"ERROR: Failed to process document '{pdf_path}' via Docling: {e}")
        # Return empty string or raise exception depending on requirements.
        # We raise/return empty to let the main caller handle it.
        raise e

def ingest_documents() -> bool:
    """
    Main ingestion pipeline:
    1. Find all PDFs in the search directories.
    2. Convert them to Markdown using Docling (or load from cache).
    3. Split markdown text into chunks.
    4. Generate embeddings and save to FAISS Vector Database.
    """
    pdf_files = get_pdf_files()
    if not pdf_files:
        print("No PDF files found to ingest. Please make sure PDFs are placed in './documentos' or './docs'.")
        return False
        
    documents = []
    
    print(f"Starting conversion for {len(pdf_files)} files...")
    for pdf_path in pdf_files:
        try:
            md_content = convert_pdf_to_markdown(pdf_path)
            if md_content.strip():
                # Store the PDF filename in the metadata
                doc = Document(
                    page_content=md_content,
                    metadata={"source": pdf_path, "filename": os.path.basename(pdf_path)}
                )
                documents.append(doc)
        except Exception as e:
            print(f"Skipping '{pdf_path}' due to ingestion error.")
            
    if not documents:
        print("No documents were successfully converted.")
        return False
        
    # Text splitting
    print("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Generated {len(chunks)} chunks from {len(documents)} documents.")
    
    # Embedding generation
    print(f"Initializing embedding model: {config.EMBEDDING_MODEL_NAME}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL_NAME,
        model_kwargs={'device': 'cpu'} # Can change to 'cuda' if GPU is available
    )
    
    print("Generating embeddings and building FAISS index...")
    try:
        db = FAISS.from_documents(chunks, embeddings)
        db.save_local(config.FAISS_DB_PATH)
        print(f"FAISS index successfully saved to '{config.FAISS_DB_PATH}'")
        return True
    except Exception as e:
        print(f"ERROR saving FAISS database: {e}")
        return False

if __name__ == "__main__":
    # Create the docs folders if they don't exist
    for d in config.DOCS_DIRS:
        os.makedirs(d, exist_ok=True)
    ingest_documents()

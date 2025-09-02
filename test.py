import os
from pathlib import Path
from src.document_analyzer.data_ingestion import DocumentHandler
from src.document_analyzer.data_analysis import DocumentAnalyzer


pdf_path = r"/Users/subbulakshmisankaran/AgenticAI/LLMOps/document_portal/data/document_analysis/Attention_is_all_you_need.pdf"

def main():
    print("Testing Data Ingestion pipeline")
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        ## STEP 1: DATA INGESTION
        print("1. Data Ingestion")
        doc_handler = DocumentHandler(session_id="test_ingestion")
        saved_path = doc_handler.save_document(pdf_path,
                                               pdf_bytes)
        text_content = doc_handler.read_document(saved_path)
        print(f"Extracted text length: {len(text_content)} chars\n")

        ## STEP 2: DATA ANALYSIS
        print("2. Data Analysis")
        doc_analyzer = DocumentAnalyzer() # Loads LLM and parser
        result = doc_analyzer.analyse_document(text_content)

        ## STEP 3: RESULTS
        print("3. Metadata Analysis Result")
        for key, val in result.items():
            print(f"{key}: {val}")

    except Exception as e:
        print(f"Document analysis failed: {e}")

main()



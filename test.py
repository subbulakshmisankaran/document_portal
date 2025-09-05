# import os
# from pathlib import Path
# from src.document_analyzer.data_ingestion import DocumentHandler
# from src.document_analyzer.data_analysis import DocumentAnalyzer


# pdf_path = r"/Users/subbulakshmisankaran/AgenticAI/LLMOps/document_portal/data/document_analysis/Attention_is_all_you_need.pdf"

# def main():
#     print("Testing Data Ingestion pipeline")
#     try:
#         with open(pdf_path, "rb") as f:
#             pdf_bytes = f.read()

#         ## STEP 1: DATA INGESTION
#         print("1. Data Ingestion")
#         doc_handler = DocumentHandler(session_id="test_ingestion")
#         saved_path = doc_handler.save_document(pdf_path,
#                                                pdf_bytes)
#         text_content = doc_handler.read_document(saved_path)
#         print(f"Extracted text length: {len(text_content)} chars\n")

#         ## STEP 2: DATA ANALYSIS
#         print("2. Data Analysis")
#         doc_analyzer = DocumentAnalyzer() # Loads LLM and parser
#         result = doc_analyzer.analyse_document(text_content)

#         ## STEP 3: RESULTS
#         print("3. Metadata Analysis Result")
#         for key, val in result.items():
#             print(f"{key}: {val}")

#     except Exception as e:
#         print(f"Document analysis failed: {e}")

# if __name__ == "__main()__":
#     main()


import io
from pathlib import Path
from src.document_compare.data_ingestion import DocumentIngestion
from src.document_compare.document_comparator import DocumentComparatorLLM

def load_fake_uploaded_file(filepath: Path)-> io.BytesIO:
    return io.BytesIO(filepath.read_bytes())

def test_compare_documents():
    ref_path = Path(__file__).parent / "data/document_compare/Long_Report_V1.pdf"
    actual_path = Path(__file__).parent / "data/document_compare/Long_Report_V2.pdf"

    class FakeUpload:
        def __init__(self, file_path: Path) -> None:
            self.name = file_path.name
            self._buffer = file_path.read_bytes()
        
        def get_buffer(self):
            return self._buffer
    
    ref_upload = FakeUpload(ref_path)
    actual_upload = FakeUpload(actual_path)

    doc_ingestion = DocumentIngestion()
    ref_file, actual_file = doc_ingestion.save_uploaded_files(ref_upload, actual_upload)

    ref_file_content = doc_ingestion.read_pdf(ref_file)
    actual_file_content = doc_ingestion.read_pdf(actual_file)

    #combined_text = doc_ingestion.combine_documents()
    
    #print("\n Combined Text Preview (First 1000 chars): \n")
    #print(combined_text[:1000])

    llm_comparator = DocumentComparatorLLM()
    comparison_df = llm_comparator.compare_documents(ref_file_content, actual_file_content)
    assert not comparison_df.empty, "Comparison dataframe is empty"
    assert "Changes" in comparison_df.columns, "Missing 'Changes' column"

    print("\n=== COMPARISON RESULT ===\n")
    print(comparison_df)

    print("\n=== COMPARISON CHANGES (First Row) ===\n")
    print(comparison_df.iloc[0]['Changes'])

    doc_ingestion.cleanup_sessions()

if __name__ == "__main__":
    test_compare_documents()
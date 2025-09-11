## Test code for document ingestion and analysis using PDFHandler and DocumentAnlayzer
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


## Test code for comparing documents using LLM
# import io
# from pathlib import Path
# from src.document_compare.data_ingestion import DocumentIngestion
# from src.document_compare.document_comparator import DocumentComparatorLLM

# def load_fake_uploaded_file(filepath: Path)-> io.BytesIO:
#     return io.BytesIO(filepath.read_bytes())

# def test_compare_documents():
#     ref_path = Path(__file__).parent / "data/document_compare/Long_Report_V1.pdf"
#     actual_path = Path(__file__).parent / "data/document_compare/Long_Report_V2.pdf"

#     class FakeUpload:
#         def __init__(self, file_path: Path) -> None:
#             self.name = file_path.name
#             self._buffer = file_path.read_bytes()
        
#         def get_buffer(self):
#             return self._buffer
    
#     ref_upload = FakeUpload(ref_path)
#     actual_upload = FakeUpload(actual_path)

#     doc_ingestion = DocumentIngestion()
#     ref_file, actual_file = doc_ingestion.save_uploaded_files(ref_upload, actual_upload)

#     ref_file_content = doc_ingestion.read_pdf(ref_file)
#     actual_file_content = doc_ingestion.read_pdf(actual_file)

#     #combined_text = doc_ingestion.combine_documents()
    
#     #print("\n Combined Text Preview (First 1000 chars): \n")
#     #print(combined_text[:1000])

#     llm_comparator = DocumentComparatorLLM()
#     comparison_df = llm_comparator.compare_documents(ref_file_content, actual_file_content)
#     assert not comparison_df.empty, "Comparison dataframe is empty"
#     assert "Changes" in comparison_df.columns, "Missing 'Changes' column"

#     print("\n=== COMPARISON RESULT ===\n")
#     print(comparison_df)

#     print("\n=== COMPARISON CHANGES (First Row) ===\n")
#     print(comparison_df.iloc[0]['Changes'])

#     doc_ingestion.cleanup_old_sessions()

# if __name__ == "__main__":
#     test_compare_documents()

## Test code for document chat functionality
import os
from pathlib import Path
from utils.model_loader import ModelLoader
from langchain_community.vectorstores import FAISS
from src.single_document_chat.data_ingestion import SingleDocIngestor
from src.single_document_chat.retrieval import ConversationalRAG
import sys

FAISS_INDEX_PATH = Path("faiss_index")

def test_conversational_rag_on_pdf(pdf_path:str,
                                   question:str):
    
    try:
        model_loader = ModelLoader()
        if FAISS_INDEX_PATH.exists():
            print("Loading existing FAISS index...")

            embedding_model = model_loader.load_embedding_model()
            vector_store = FAISS.load_local(folder_path=str(FAISS_INDEX_PATH),
                                            embeddings=embedding_model,
                                            allow_dangerous_deserialization=True)
            retriever = vector_store.as_retriever(search_type="similarity",
                                                  search_kwargs={"k": 5})
        else:
            print("FAISS index not found. Hence creating one")
            with open(pdf_path, "rb") as f:
                uploaded_files = [f]
                ingestor = SingleDocIngestor()
                retriever = ingestor.ingest_files(uploaded_files)

        print("Running Conversational RAG...")
        session_id = "test_conversational_rag"
        rag = ConversationalRAG(session_id=session_id,
                                retriever=retriever)
        response = rag.invoke(question)
        print(f"\nQuestion: {question}\nAnswer: {response}")
    except Exception as e:
        print(f"Test failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # Example PDF path and question
    pdf_path = "/Users/subbulakshmisankaran/AgenticAI/LLMOps/document_portal/data/single_document_chat/Attention_is_all_you_need.pdf"
    question = "What is the main topic of the document?"

    if not Path(pdf_path).exists():
        print(f"PDF file doesnt exist at: {pdf_path}")
        sys.exit(1)

    # Run the test
    test_conversational_rag_on_pdf(pdf_path,
                                   question)
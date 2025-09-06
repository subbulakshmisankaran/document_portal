import uuid
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from utils.model_loader import ModelLoader

class SingleDocIngestor:
    def __init__(self):
        self.logger = CustomLogger().get_logger(__name__)
        try:
            pass
        except Exception as e:
            self.logger.error(f"Error in initializing in single doc ingestor: {e}")
            raise DocumentPortalException(e)
    
    def ingest_files(self):
        try:
            pass
        except Exception as e:
            self.logger.error(f"Error in ingesting files: {e}")
            raise DocumentPortalException(e)

    def _create_retriever(self):
        try:
            pass
        except Exception as e:
            self.logger.error(f"Error in creating retriever : {e}")
            raise DocumentPortalException(e)            
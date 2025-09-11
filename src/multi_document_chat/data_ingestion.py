from exception.custom_exception import DocumentPortalException
from logger.custom_logger import CustomLogger
from pathlib import Path
from datetime import datetime, timezone
import uuid
from utils.model_loader import ModelLoader

class MultiDocIngestor:
    SUPPORTED_FILE_TYPES = {'.pdf', '.docx', '.txt', '.md'}
    def __init__(self, 
                 temp_dir:str = "data/multi_document_chat",
                 faiss_dir:str = "faiss_index",
                 session_id:str = None):
        self.logger = CustomLogger().get_logger(__name__)
        try:
            self.temp_dir = Path(temp_dir)
            self.faiss_dir = Path(faiss_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.faiss_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique session ID with timestamp and random component
            self.session_id = session_id or f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            self.session_temp_dir = self.temp_dir / self.session_id
            self.session_faiss_dir = self.faiss_dir / self.session_id
            self.session_temp_dir.mkdir(parents=True, exist_ok=True)
            self.session_faiss_dir.mkdir(parents=True, exist_ok=True)


            self.model_loader = ModelLoader()
            self.logger.info("Multi-Document Ingestor initialized",
                             temp_base = str(self.temp_dir),
                             faiss_base = str(self.faiss_dir),
                             session_id = self.session_id,
                             session_tmp_path = self.session_temp_dir,
                             session_faiss_path = self.session_faiss_dir)
        except Exception as e:
            error_message = f"Failed to initialize multi doc ingestor: {str(e)}"
            self.logger.error(error_message)
            raise DocumentPortalException(error_message)
    
    def ingest_files(self):
        try:
            pass
        except Exception as e:
            error_message = f"Failed to ingest files: {str(e)}"
            self.logger.error(error_message)
            raise DocumentPortalException(error_message)
    
    def _create_retriever(self, documents):
        try:
            pass
        except Exception as e:
            error_message = f"Failed to create retriever    : {str(e)}"
            self.logger.error(error_message)
            raise DocumentPortalException(error_message)

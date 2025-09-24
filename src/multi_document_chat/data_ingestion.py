from exception.custom_exception import DocumentPortalException
from logger.custom_logger import CustomLogger
from pathlib import Path
from datetime import datetime, timezone
import uuid
from utils.model_loader import ModelLoader
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from typing import Optional, List, Any
import logging
import shutil

class MultiDocIngestor:
    """
    Enhanced multi-document ingestor with memory efficiency and robust error handling.
    
    Supports PDF, DOCX, TXT, and MD files with session-based isolation,
    streaming file handling, and automatic cleanup capabilities.
    """

    SUPPORTED_FILE_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md'}
    DEFAULT_CHUNK_SIZE = 64 * 1024  # 64KB for file streaming

    def __init__(self, 
                 temp_dir:str = "data/multi_document_chat",
                 faiss_dir:str = "faiss_index",
                 session_id: Optional[str] = None):
        """
        Initialize MultiDocIngestor with session management.
        
        Args:
            temp_dir (str): Base directory for temporary file storage
            faiss_dir (str): Base directory for FAISS indices
            session_id (str, optional): Session identifier. Auto-generated if None.
            
        Raises:
            DocumentPortalException: If initialization fails
        """
            
        # Initialize logger first with fallback
        self._init_logger()
        
        try:
            # Initialize directory paths
            self.temp_dir = Path(temp_dir)
            self.faiss_dir = Path(faiss_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.faiss_dir.mkdir(parents=True, exist_ok=True)

            # Generate unique session ID with timestamp and random component
            self.session_id = session_id or f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

            # Create session-specific directories
            self.session_temp_dir = self.temp_dir / self.session_id
            self.session_faiss_dir = self.faiss_dir / self.session_id
            self.session_temp_dir.mkdir(parents=True, exist_ok=True)
            self.session_faiss_dir.mkdir(parents=True, exist_ok=True)


            # Initialize model loader
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
            raise DocumentPortalException(error_message) from e

    def _init_logger(self):
        """Initialize logger with fallback to basic logging"""
        try:
            self.logger = CustomLogger().get_logger(__name__)
        except Exception:
            # Fallback to basic logging if CustomLogger fails
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.INFO)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
            self.logger.warning("CustomLogger failed, using basic logger fallback")

    def ingest_files(self, uploaded_files: List[any], max_size_mb_per_file: int = 50) -> any:
        """
        Ingest multiple files and create a vector store retriever.
        
        Args:
            uploaded_files (List): List of uploaded file objects with .name and .read() methods
            max_size_mb_per_file (int): Maximum file size in MB per file
            
        Returns:
            FAISS retriever object for similarity search
            
        Raises:
            DocumentPortalException: If ingestion fails
        """
        try:
            self.logger.info(
                "Starting file ingestion process",
                session_id=self.session_id,
                num_files=len(uploaded_files),
                max_size_mb=max_size_mb_per_file
            )
            
            documents = []
            processed_files = 0
            
            for uploaded_file in uploaded_files:
                try:
                    # Validate file
                    file_info = self._validate_file(uploaded_file)
                    
                    # Save file with streaming
                    temp_path, file_size = self._save_uploaded_file(
                        uploaded_file, 
                        file_info['extension'],
                        max_size_mb_per_file
                    )
                    
                    self.logger.info(
                        "File saved for ingestion",
                        file_name=uploaded_file.name,
                        saved_as=str(temp_path),
                        file_size_mb=f"{file_size / (1024*1024):.2f}",
                        session_id=self.session_id
                    )
                    
                    # Load document based on file type
                    docs = self._load_document(temp_path, file_info['extension'])
                    documents.extend(docs)
                    processed_files += 1
                    
                except DocumentPortalException as e:
                    self.logger.warning(
                        "Failed to process file",
                        file_name=getattr(uploaded_file, 'name', 'unknown'),
                        error=str(e),
                        session_id=self.session_id
                    )
                    continue  # Skip failed files, continue with others
                
                except Exception as e:
                    self.logger.error(
                        "Unexpected error processing file",
                        file_name=getattr(uploaded_file, 'name', 'unknown'),
                        error=str(e),
                        session_id=self.session_id
                    )
                    continue

            if not documents:
                error_msg = "No valid documents could be loaded from uploaded files"
                self.logger.error(error_msg, session_id=self.session_id)
                raise DocumentPortalException(error_msg)

            self.logger.info(
                "Document loading completed",
                total_docs=len(documents),
                processed_files=processed_files,
                total_files=len(uploaded_files),
                session_id=self.session_id
            )

            return self._create_retriever(documents)
            
        except DocumentPortalException:
            # Re-raise DocumentPortalException as-is
            raise
        except Exception as e:
            error_message = f"Failed to ingest files: {e}"
            self.logger.error(error_message, session_id=self.session_id)
            raise DocumentPortalException(error_message) from e

    def _validate_file(self, uploaded_file) -> dict:
        """
        Validate uploaded file and extract information.
        
        Args:
            uploaded_file: File object with .name attribute
            
        Returns:
            dict: File information including name and extension
            
        Raises:
            DocumentPortalException: If file is invalid
        """
        try:
            # Check if file has a name
            if not hasattr(uploaded_file, 'name') or not uploaded_file.name:
                raise DocumentPortalException("File has no name attribute")
            
            # Check file extension
            file_path = Path(uploaded_file.name)
            extension = file_path.suffix.lower()
            
            if extension not in self.SUPPORTED_FILE_EXTENSIONS:
                raise DocumentPortalException(
                    f"Unsupported file type: {extension}. "
                    f"Supported types: {', '.join(self.SUPPORTED_FILE_EXTENSIONS)}"
                )
            
            return {
                'name': uploaded_file.name,
                'extension': extension,
                'stem': file_path.stem
            }
            
        except DocumentPortalException:
            raise
        except Exception as e:
            raise DocumentPortalException(f"File validation failed: {e}") from e


    def _save_uploaded_file(self, uploaded_file, extension: str, max_size_mb: int) -> tuple:
        """
        Save uploaded file with streaming to handle large files efficiently.
        
        Args:
            uploaded_file: File object with .read() method
            extension (str): File extension
            max_size_mb (int): Maximum file size in MB
            
        Returns:
            tuple: (file_path, file_size_bytes)
            
        Raises:
            DocumentPortalException: If save operation fails or file too large
        """
        try:
            # Generate unique filename
            unique_filename = Path(uploaded_file.name).name
            temp_path = self.session_temp_dir / unique_filename
            
            # Stream file with size checking
            max_bytes = max_size_mb * 1024 * 1024
            total_size = 0
            
            try:
                with open(temp_path, "wb") as f:
                    while True:
                        # Read in chunks to manage memory
                        chunk = uploaded_file.read(self.DEFAULT_CHUNK_SIZE)
                        if not chunk:
                            break
                        
                        # Check size limit
                        total_size += len(chunk)
                        if total_size > max_bytes:
                            # Clean up partial file
                            temp_path.unlink(missing_ok=True)
                            raise DocumentPortalException(
                                f"File too large: {total_size / (1024*1024):.1f}MB exceeds limit of {max_size_mb}MB"
                            )
                        
                        f.write(chunk)
                    
                    # Ensure data is written to disk
                    f.flush()
                
                return temp_path, total_size

            except Exception as e:
                # Clean up on any error
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)
                raise
                
        except DocumentPortalException:
            raise
        except Exception as e:
            raise DocumentPortalException(f"Failed to save file: {e}") from e


    def _load_document(self, file_path: Path, extension: str) -> List:
        """
        Load document using appropriate loader based on file extension.
        
        Args:
            file_path (Path): Path to the document file
            extension (str): File extension
            
        Returns:
            List: Loaded document objects
            
        Raises:
            DocumentPortalException: If document loading fails
        """
        try:
            self.logger.debug(
                "Loading document",
                file_path=str(file_path),
                extension=extension,
                session_id=self.session_id
            )
            
            # Select appropriate loader
            if extension == ".pdf":
                loader = PyPDFLoader(str(file_path))
            elif extension == ".docx":
                loader = Docx2txtLoader(str(file_path))
            elif extension in [".txt", ".md"]:
                loader = TextLoader(str(file_path), encoding="utf-8")
            else:
                raise DocumentPortalException(f"No loader available for extension: {extension}")
            
            # Load documents
            docs = loader.load()
            
            if not docs:
                raise DocumentPortalException(f"No content could be extracted from file: {file_path.name}")
            
            self.logger.debug(
                "Document loaded successfully",
                file_path=str(file_path),
                num_docs=len(docs),
                session_id=self.session_id
            )
            
            return docs
            
        except DocumentPortalException:
            raise
        except Exception as e:
            raise DocumentPortalException(f"Failed to load document {file_path.name}: {e}") from e


    def _create_retriever(self, documents: List) -> Any:
        """
        Create FAISS retriever from loaded documents.
        
        Args:
            documents (List): List of loaded document objects
            
        Returns:
            FAISS retriever for similarity search
            
        Raises:
            DocumentPortalException: If retriever creation fails
        """
        try:
            self.logger.info(
                "Creating document retriever",
                total_documents=len(documents),
                session_id=self.session_id
            )

            # Split documents into chunks
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000,
                                                      chunk_overlap=400)
            chunks = splitter.split_documents(documents)

            self.logger.info("Documents split into chunks",
                             total_chunks=len(chunks),
                             session_id=self.session_id)

            # Load embedding model
            embedding_model = self.model_loader.load_embedding_model()
        
            # Create FAISS vector store
            vector_store = FAISS.from_documents(embedding=embedding_model,
                                                documents=chunks)

            # Save vector store to disk
            vector_store.save_local(str(self.session_faiss_dir))

            self.logger.info("FAISS index saved to disk",
                             path=str(self.session_faiss_dir),
                             session_id=self.session_id)

            # Create and return retriever
            retriever = vector_store.as_retriever(search_type="similarity",
                                                  search_kwargs={"k": 5})
            self.logger.info("FAISS retriever created and ready to use",
                             session_id=self.session_id)
            return retriever

        except Exception as e:
            error_message = f"Failed to create retriever    : {str(e)}"
            self.logger.error(error_message)
            raise DocumentPortalException(error_message)



    def cleanup_old_sessions(self, keep_latest: int = 3):
        """
        Remove old session directories while keeping the most recent ones.
    
        Automatically cleans up disk space by deleting older session directories,
        preserving only the specified number of most recent sessions for debugging
        and operational purposes.

        """
        try:
            # Validate input to prevent accidental deletion of all sessions
            if keep_latest < 1:
                self.logger.warning(f"Invalid keep_latest value: {keep_latest}, using default of 3")
                keep_latest = 3
            
            self.logger.info(
                "Starting session cleanup", 
                session_dir=str(self.temp_dir), 
                keep_latest=keep_latest
            )
            
            # Check if base directory exists
            if not self.temp_dir.exists():
                self.logger.info("Session base directory does not exist, nothing to clean")
                return

            # Get all session directories and sort by creation time (newest first)
            # Using creation time ensures we keep the most recently created sessions
            sessions = sorted(
                [f for f in self.temp_dir.iterdir() if f.is_dir()], 
                key=lambda x: x.stat().st_ctime,  # Sort by creation time
                reverse=True  # Most recent first
            )
            self.logger.info(f"Found {len(sessions)} session directories")

            # Delete old session directories
            for folder in sessions[keep_latest:]:
                # Use shutil.rmtree for efficient directory deletion
                # ignore_errors=True ensures individual file permission issues 
                # don't stop the entire cleanup process
                shutil.rmtree(folder, ignore_errors=True)

                # Verify deletion was successful
                if not folder.exists():
                    self.logger.info("Old session folder deleted", path=str(folder))
                else:
                    self.logger.warning("Failed to completely delete session", path=str(folder))

        except Exception as e:
            self.logger.error("Error cleaning old sessions", error=str(e))
            raise DocumentPortalException("Error cleaning old sessions", e) from e
        

    def load_existing_retriever(self) -> any:
        """
        Load an existing FAISS retriever from saved index.
        
        Returns:
            FAISS retriever if index exists, None otherwise
            
        Raises:
            DocumentPortalException: If loading fails
        """
        try:
            if not self.session_faiss_dir.exists():
                self.logger.info(
                    "No existing FAISS index found",
                    session_id=self.session_id,
                    path=str(self.session_faiss_dir)
                )
                return None
            
            # Load embedding model
            embedding_model = self.model_loader.load_embedding_model()
            
            # Load FAISS index
            vector_store = FAISS.load_local(
                str(self.session_faiss_dir),
                embedding_model,
                allow_dangerous_deserialization=True
            )
            
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
            
            self.logger.info(
                "Existing FAISS retriever loaded successfully",
                session_id=self.session_id
            )
            
            return retriever
            
        except Exception as e:
            error_message = f"Failed to load existing retriever: {e}"
            self.logger.error(error_message, session_id=self.session_id)
            raise DocumentPortalException(error_message) from e

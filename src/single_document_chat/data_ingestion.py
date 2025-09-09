import uuid
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from utils.model_loader import ModelLoader
from datetime import datetime, timezone


class SingleDocIngestor:
    def __init__(self,
                 data_dir = "./data/single_document_chat",
                 faiss_dir:str = "faiss_index"):
        """
        Initialize the SingleDocIngestor with specified directories for data and index storage.
        
        Creates the necessary directory structure for storing uploaded files and FAISS indices.
        Sets up logging and model loading utilities for the ingestion pipeline.
        
        Args:
            data_dir (str, optional): Path to directory for storing uploaded PDF files.
                Defaults to "./data/single_document_chat".
            faiss_dir (str, optional): Path to directory for storing FAISS vector indices.
                Defaults to "faiss_index".
                
        Raises:
            DocumentPortalException: If initialization fails due to directory creation
                errors or other setup issues.
                
        Example:
            >>> ingestor = SingleDocIngestor(
            ...     data_dir="./custom_data",
            ...     faiss_dir="./custom_index"
            ... )

        """
        self.logger = CustomLogger().get_logger(__name__)
        try:
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(parents=True, 
                                exist_ok=True)

            self.faiss_dir = Path(faiss_dir)
            self.faiss_dir.mkdir(parents=True,
                                 exist_ok=True)
            
            self.model_loader =ModelLoader()
            self.logger.info("SingleDocIngestor initialized successfully",
                             data_path=str(self.data_dir),
                             faiss_path=str(self.faiss_dir))

        except Exception as e:
            self.logger.error("Error in initializing in SingleDocIngestor",
                              error=str(e))
            raise DocumentPortalException(e)
    
    def ingest_files(self, uploaded_files):
        """
        Process and ingest multiple PDF files into the vector store for retrieval.
        
        This method handles the complete ingestion pipeline:
        1. Saves uploaded files with unique session-based names to prevent conflicts
        2. Loads PDF content using PyPDFLoader
        3. Creates a retriever from the processed documents
        
        Each uploaded file is given a unique name using timestamp and UUID components
        to ensure no naming conflicts across different sessions.
        
        Args:
            uploaded_files (List[UploadedFile]): List of uploaded PDF file objects.
                Each file object should have a 'read()' method and 'name' attribute.
                
        Returns:
            Retriever: A configured FAISS retriever object for similarity-based document search.
            The retriever is set up with similarity search and returns top 5 results by default.
            
        Raises:
            DocumentPortalException: If file processing, document loading, or retriever
                creation fails at any stage.
                
        Example:
            >>> retriever = ingestor.ingest_files([uploaded_pdf1, uploaded_pdf2])
            >>> results = retriever.get_relevant_documents("search query")
        """

        try:
            documents = []

            for uploaded_file in uploaded_files:
                # Generate session based unique filename with timestamp and random component
                session_file_name = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.pdf"
                temp_path = self.data_dir / session_file_name

                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.read())

                self.logger.info("PDF saved for ingestion", file_name = uploaded_file.name)
                loader = PyPDFLoader(str(temp_path))
                documents.extend(loader.load())
            
            self.logger.info("All PDF files are loaded successfully", count=len(documents))
            return self._create_retriever(documents)
        except Exception as e:
            self.logger.error("Error in ingesting files",
                              error=str(e))
            raise DocumentPortalException(e)

    def _create_retriever(self, documents):
        """
        Create a FAISS-based retriever from processed document chunks.
        
        This private method handles the vector store creation pipeline:
        1. Splits documents into overlapping chunks for optimal retrieval
        2. Generates embeddings using the configured embedding model
        3. Creates and saves a FAISS vector index
        4. Configures a retriever with similarity search parameters
        
        The chunking strategy uses overlapping segments to ensure context preservation
        across chunk boundaries, improving retrieval quality.
        
        Args:
            documents (List[Document]): List of loaded document objects from PyPDFLoader.
                Each document contains page content and metadata.
                
        Returns:
            Retriever: A FAISS retriever configured for similarity search with k=5,
            meaning it returns the top 5 most similar document chunks for queries.
            
        Raises:
            DocumentPortalException: If document chunking, embedding generation,
                FAISS index creation, or retriever configuration fails.
                
        Note:
            - Chunk size: 1000 characters for balanced context and performance
            - Chunk overlap: 300 characters to maintain context across boundaries
            - Search type: Similarity-based matching
            - Default k: 5 most relevant chunks returned per query
        """
        try:
            # Configure text splitter for optimal chunking strategy
            # chunk_size=1000: Balance between context preservation and processing efficiency
            # chunk_overlap=300: Overlap ensures context continuity across chunk boundaries

            splitter = RecursiveCharacterTextSplitter(chunk_size = 1000,
                                                      chunk_overlap = 300)
            
            # Split documents into smaller chunks for better retrieval performance
            # Smaller chunks allow for more precise similarity matching
            chunks = splitter.split_documents(documents)
            self.logger.info("Documents are split into chunks successfully", 
                             count=len(chunks))
            
            # Load the embedding model for converting text to vector representations
            embedding_model = self.model_loader.load_embedding_model()

            # Create FAISS vector store from document chunks
            # FAISS provides efficient similarity search capabilities
            vector_store = FAISS.from_documents(documents=chunks,
                                                embedding=embedding_model)

            # Persist the vector store to disk for future use
            # This allows loading the index without re-processing documents
            vector_store.save_local(str(self.faiss_dir))
            self.logger.info("FAISS index created and saved",
                             faiss_path=str(self.faiss_dir))
            
            # Configure retriever for similarity-based document search
            # search_type="similarity": Use cosine similarity for matching
            # k=5: Return top 5 most relevant chunks per query
            retriever = vector_store.as_retriever(search_type="similarity",
                                                  search_kwargs={"k": 5})
            self.logger.info("Retriever is created successfully",
                             retriever_type=str(type(retriever)))
            
            return retriever
        except Exception as e:
            self.logger.error("Error in creating retriever",
                              error=str(e))
            raise DocumentPortalException(e)            
import os
from operator import itemgetter
from typing import Optional, Any, List
from pathlib import Path
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage

from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from prompt.prompt_library import PROMPT_REGISTRY
from data_model.schemas import PromptType

class ConversationalRAG:
    """
    Enhanced conversational RAG system with flexible retriever management.

    Supports both initialization with existing retriever or loading from FAISS index,
    with robust error handling and logging throughout the pipeline.
    """
    def __init__(self,
                 session_id: str,
                 retriever: Optional[Any] = None,
                 faiss_index_path: Optional[str] = None):
        """
        Initialize ConversationalRAG system.
        
        Args:
            session_id (str): Unique session identifier
            retriever (optional): Pre-built retriever object
            faiss_index_path (str, optional): Path to FAISS index directory
            
        Note:
            Either retriever OR faiss_index_path must be provided, not both.
            
        Raises:
            DocumentPortalException: If initialization fails
        """

        # Initialize logger first
        self.logger = CustomLogger().get_logger(__name__)
        try:
            self.session_id = session_id
            self.retriever = None

            # Validate input params
            self._validate_init_params(retriever, faiss_index_path)

            # Initialize model components
            self._init_models()

            # Load prompts
            self._load_prompts()

            # Set up retriever
            if retriever is not None:
                self.retriever = retriever
                self.logger.info(
                    "Using provided retriever",
                    session_id=self.session_id
                )
            elif faiss_index_path is not None:
                self.load_retriever_from_faiss(faiss_index_path)
            
            self.chain = None # Lazy initialization

            self.logger.info("Conversational RAG initialized successfully", 
                             session_id = self.session_id,
                             has_retriever = self.retriever is not None,
                             chain_status = "not_built_yet")

        except DocumentPortalException:
            raise
        except Exception as e:
            error_message = f"Failed to initialize ConversationalRAG: {str(e)}"
            self.logger.error(error_message)
            raise DocumentPortalException(error_message) from e


    def _validate_init_params(self, 
                              retriever: Optional[Any], 
                              faiss_index_path: Optional[str]):

        """Validate initialization parameters"""
        if retriever is None and faiss_index_path is None:
            raise DocumentPortalException("Either retriever or faiss_index_path must be provided")
        
        if retriever is not None and faiss_index_path is not None:
            raise DocumentPortalException("Cannot provide both retriever and faiss_index_path")

        if faiss_index_path is not None and not Path(faiss_index_path).exists():
            raise DocumentPortalException(f"FAISS index path does not exist: {faiss_index_path}")


    def _init_models(self):
        """Initialize model loader and load required models"""
        try:
            self.model_loader = ModelLoader()

            # Load embedding model
            self.embedding_model= self.model_loader.load_embedding_model()
            if self.embedding_model is None:
                raise DocumentPortalException("Failed to load embedding model")
            
            # Load LLM
            self.llm = self._load_llm()

            self.logger.debug(
                "Models initialized successfully!",
                session_id=self.session_id,
            )

        except DocumentPortalException:
            raise
        except Exception as e:
            raise DocumentPortalException(f"Model initialization failed: {str(e)}")

    def _load_prompts(self):
        """Load required prompts from PROMPT registry"""
        try:
            self.standalone_question_prompt = PROMPT_REGISTRY.get(PromptType.STANDALONE_QUESTION.value, None)
            self.grounded_qa_prompt = PROMPT_REGISTRY.get(PromptType.GROUNDED_QA.value, None)

            if self.standalone_question_prompt is None:
                raise DocumentPortalException("Standalone question prompt not found in the PROMPT registry")
        
            if self.grounded_qa_prompt is None:
                raise DocumentPortalException("Grounded QA prompt not found in the PROMPT registry")
            
            self.logger.info("All prompts are loaded successfully",
                             session_id = self.session_id)
        except DocumentPortalException:
            raise
        except Exception as e:
            raise DocumentPortalException(f"Failed to load prompts: {str(e)}") from e

    def load_retriever_from_faiss(self, index_path: str):
        """
        Load retriever from existing FAISS index.
        
        Args:
            index_path (str): Path to FAISS index directory
            
        Returns:
            Retriever object
            
        Raises:
            DocumentPortalException: If loading fails
        """
        try:
            if not os.path.isdir(index_path):
                raise FileNotFoundError(f"FAISS directory not found: {index_path}")

            # Load FAISS vector store
            vector_store = FAISS.load_local(index_path,
                                            embeddings=self.embedding_model,
                                            allow_dangerous_deserialization=True)
            
            # Create retriever
            self.retriever = vector_store.as_retriever(search_type="similarity",
                                                       search_kwargs={"k": 5})
            
            self.logger.info("FAISS retriever loaded successfully from the disk",
                             index_path = index_path,
                             session_id = self.session_id)

            # Mark chain for reinitialization with new retriever
            self.chain = None
            
            return self.retriever

        except DocumentPortalException:
            raise

        except Exception as e:
            error_message = f"Failed to load retriever from FAISS index: {str(e)}"
            self.logger.error(error_message)
            raise DocumentPortalException(error_message) from e

    def invoke(self, user_input:str, chat_history: Optional[List[BaseMessage]] = None)->str:
        """
        Invoke the conversational RAG chain.
        
        Args:
            input_text (str): User input/question
            chat_history (Optional[List[BaseMessage]], optional): Previous conversation history
            
        Returns:
            str: Generated response
            
        Raises:
            DocumentPortalException: If invocation fails
        """
        try:
            # Initialize RAG chain if not already built
            if self.chain is None:
                self._build_lcel_chain()

            # Prepare input data
            chat_history = chat_history or []
            payload = {
                "input": user_input,
                "chat_history": chat_history,
            }

            # Invoke the RAG chain
            answer = self.chain.invoke(payload)
            if not answer:
                self.logger.warning("No answer generated",
                                    user_input=user_input,
                                    session_id=self.session_id)
                return "No answer generated"
            
            self.logger.info("Chain invoked and generated an answer",
                             user_input=user_input,
                             session_id=self.session_id,
                             answer_len=len(answer),
                             answer_preview = answer[:100])
            return answer

        except Exception as e:
            error_message = f"Failed to invoke ConversationalRAG chain: {str(e)}"
            self.logger.error(error_message)
            raise DocumentPortalException(error_message) from e
       
    def _load_llm(self):
        """
        Load LLM model with proper validation.
        
        Returns:
            LLM model instance
            
        Raises:
            DocumentPortalException: If LLM loading fails
        """
        try:
            if self.model_loader is None:
                raise DocumentPortalException(f"Model loader is not initialized")

            llm = self.model_loader.load_llm()
            if llm is None:
                raise DocumentPortalException(f"LLM model could not be loaded")

            self.logger.info("LLM loaded successfully",
                             session_id = self.session_id)
            return llm
        except DocumentPortalException:
            raise
        except Exception as e:
            error_message = f"Failed to load LLM model for ConversationalRAG: {str(e)}"
            self.logger.error(error_message)
            raise DocumentPortalException(error_message) from e
        
    @staticmethod
    def _format_docs(docs: List[Document])->str:
        """
        Format retrieved documents into a single string.
        
        Args:
            docs (List[Document]): Retrieved documents
            
        Returns:
            str: Formatted document content
        """
        if not docs:
            return "No relevant documents found."

        return "\n\n".join(doc.page_content for doc in docs if doc.page_content)

    def _build_lcel_chain(self):
        """
        Build the LangChain Expression Language (LCEL) chain.
        
        Creates a complete RAG pipeline with question rewriting and grounded QA.
        
        Raises:
            DocumentPortalException: If chain building fails
        """
        def tap(name):
            def _tap(x):
                # log, then pass-through unchanged
                preview = x
                if isinstance(x, str):
                    preview = x[:200]
                elif isinstance(x, list):
                    preview = [getattr(d, "page_content", "")[:120] for d in x[:3]]
                self.logger.info(f"[TAP] {name}", session_id=self.session_id, preview=preview)
                return x
            return RunnableLambda(_tap)
        try:
            if self.retriever is None:
                raise DocumentPortalException("Retriever must be initialized before building chain")
            
            if self.llm is None:
                raise DocumentPortalException("LLM must be loaded before building chain")

            self.logger.info(
                "Building LCEL chain",
                session_id=self.session_id
            )

            # Question rewriter chain
            question_rewriter = (
                {
                    "input": itemgetter("input"), 
                    "chat_history": itemgetter("chat_history"), 
                }
                | self.standalone_question_prompt
                | self.llm
                | StrOutputParser()
#                | tap("rewritten_question")
            )

            # Document retrieval chain
            retrieve_docs = (
                question_rewriter
#                | tap("pre_retriever_input")
                | self.retriever
#                | tap("retrieved_docs")
                | RunnableLambda(self._format_docs)
#                | tap("formatted_context")
            )
            #retrieve_docs = question_rewriter | self.retriever | self._format_docs

            # Final RAG chain

            self.chain = (
                {
                    "context": retrieve_docs,
                    "input": itemgetter("input"),
                    "chat_history": itemgetter("chat_history"),
                }
                | self.grounded_qa_prompt
                | self.llm
                | StrOutputParser()
            )

            self.logger.info(
                "LCEL chain built successfully",
                session_id=self.session_id
            )
        except DocumentPortalException:
            raise
        except Exception as e:
            error_message = f"Failed to build lcel chain: {str(e)}"
            self.logger.error(error_message, session_id=self.session_id)
            raise DocumentPortalException(error_message) from e
        
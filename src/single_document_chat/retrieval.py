import os
from dotenv import load_dotenv
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.vectorstores import FAISS
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from prompt.prompt_library import PROMPT_REGISTRY
from data_model.schemas import PromptType

class ConversationalRAG:
    def __init__(self, session_id:str, retriever)-> None:
        self.logger = CustomLogger().get_logger(__name__)
        try:
            pass
        except Exception as e:
            self.logger.error("Error while initializing Conversational RAG", 
                              error=str(e),
                              session_id=session_id)
            raise DocumentPortalException(e)

    def _load_llm(self):
        try:
            pass
        except Exception as e:
            self.logger.error("Error while loading LLM", 
                              error=str(e))
            raise DocumentPortalException(e)

    def _get_session_history(self, session_id:str):
        try:
            pass
        except Exception as e:
            self.logger.error("Failed to load the session history",
                              error=str(e),
                              session_id=session_id)
            raise DocumentPortalException(e)

    def load_retriever_from_faiss(self, session_id:str):
        try:
            pass
        except Exception as e:
            self.logger.error("Failed to load retriever from FAISS vectordb",
                              error=str(e))
            raise DocumentPortalException(e)
    
    def invoke(self):
        try:
            pass
        except Exception as e:
            self.logger.error("Failed to invoke conversational RAG",
                              error=str(e),
                              session_id=self.session_id)
            raise DocumentPortalException(e)
                
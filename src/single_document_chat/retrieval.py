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
import streamlit as st


load_dotenv()

class ConversationalRAG:
    def __init__(self, session_id:str, retriever)-> None:
        self.logger = CustomLogger().get_logger(__name__)
        try:
            self.session_id = session_id
            self.llm = self._load_llm()
            self.retriever = retriever

            self.contextualize_prompt = PROMPT_REGISTRY[PromptType.CONTEXTUALIZE_QUESTION]
            self.qa_prompt = PROMPT_REGISTRY[PromptType.CONTEXT_QA]

            self.history_aware_retriever = create_history_aware_retriever(
                self.llm, self.retriever, self.contextualize_prompt)

            self.logger.info("Created history aware retriever",
                             session_id=session_id)

            self.qa_chain = create_stuff_documents_chain(self.llm, self.qa_prompt)
            self.rag_chain = create_retrieval_chain(self.history_aware_retriever, self.qa_chain)
            self.logger.info("Created RAG chain",
                             session_id=session_id)
            
            self.chain = RunnableWithMessageHistory(
                self.rag_chain,
                lambda _: self._get_session_history(),
                input_messages_key="input",
                history_messages_key="chat_history",
                output_messages_key="answer"
            )
            self.logger.info("Wrapped chain with message history",
                             session_id=session_id)
        except Exception as e:
            self.logger.error("Error while initializing Conversational RAG", 
                              error=str(e),
                              session_id=session_id)
            raise DocumentPortalException(e)

    def _load_llm(self):
        try:
            llm = ModelLoader().load_llm()
            self.logger.info("LLM loaded successfully",
                             class_name = llm.__class__.__name__)
            return llm
        except Exception as e:
            self.logger.error("Error while loading LLM", 
                              error=str(e))
            raise DocumentPortalException(e)

    def _get_session_history(self) -> BaseChatMessageHistory:
        try:
            if "store" not in st.session_state:
                st.session_state.store = {}

            if self.session_id not in st.session_state.store:
                st.session_state.store[self.session_id] = ChatMessageHistory()
                self.logger.info("New chat session history created",
                                 session_id=self.session_id)
            
            history = st.session_state.store[self.session_id]
            self.logger.info(f"Retrieved history with {len(history.messages)} messages",
                     session_id=self.session_id)
            return history
        except Exception as e:
            self.logger.error("Failed to load the session history",
                              error=str(e),
                              session_id=self.session_id)
            raise DocumentPortalException(e)

    def load_retriever_from_faiss(self, index_path:str):
        try:
            embedding_model = ModelLoader().load_embedding_model()
            if not os.path.isdir(index_path):
                raise FileNotFoundError(f"FAISS index directory not found here --> {index_path}")
            
            vector_store = FAISS.load_local(index_path, embedding_model)
            self.logger.info(f"Loaded vector store from FAISS index successfully",
                             index_path = index_path)
            return vector_store.as_retriever(search_type="similarity",
                                      search_kwargs={"k": 5})
        except Exception as e:
            self.logger.error("Failed to load retriever from FAISS vectordb",
                              error=str(e))
            raise DocumentPortalException(e)

    def invoke(self, user_input:str)-> str:
        try:
            response = self.chain.invoke(
                {"input": user_input},
                config = {"configurable": {"session_id": self.session_id}}
            )
            answer = response.get("answer", "No answer.")
            if not answer:
                self.logger.warning("Empty answer received",
                                    session_id=self.session_id)
            self.logger.info("Chain invoked successfully",
                             session_id=self.session_id,
                             user_input=user_input,
                             answer_preview=answer[:150])
            return answer
        except Exception as e:
            self.logger.error("Failed to invoke conversational RAG",
                              error=str(e),
                              session_id=self.session_id)
            raise DocumentPortalException(e)
                
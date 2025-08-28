import os, sys
from typing import Dict, Any
from dotenv import load_dotenv
from utils.config_loader import load_config

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

# For logging and Exception handling
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

# Instantiate CustomLogger
logger = CustomLogger().get_logger(__name__)

class ModelLoader:
    """
    Load embeddings and LLMs from configuration and environment variables.

    Expected (example) config schema:
    {
        "embedding_model": {
            "model_name": "text-embedding-004"
        },
        "llm": {
            "groq": {
                "provider": "groq",
                "model_name": "llama-3.1-70b-versatile",
                "temperature": 0.2,
                "max_output_tokens": 2048   # (we normalize below)
            },
            "google": {
                "provider": "google",
                "model_name": "gemini-1.5-pro",
                "temperature": 0.2,
                "max_output_tokens": 2048
            },
            "openai": {
                "provider": "openai",
                "model_name": "gpt-4o-mini",
                "temperature": 0.2,
                "max_output_tokens": 2048
            }
        }
    }

    Environment variables:
      - GROQ_API_KEY  (required when provider == "groq")
      - GOOGLE_API_KEY (required for Google embeddings or Google LLM)
      - OPENAI_API_KEY (required when provider == "openai")
      - LLM_PROVIDER (optional; defaults to "groq"; must be a key in config["llm"])
    """

    def __init__(self)-> None:
        """Initialize loader, load .env, validate config, and prepare keys."""

        load_dotenv()
        self.config: Dict[str, Any] = load_config()
        if not isinstance(self.config, dict):
            logger.error("Config loader did not return a dictionary")
            raise DocumentPortalException(
                TypeError("Config must be a dictionary")
            )
        logger.info("Configuration successfully loaded!", config_keys=list(self.config.keys()))


    def _require_api_key(self, key_name: str) -> str:
        """
        Get a required API key from environment variables.

        Parameters
        ----------
        key_name : str
            The environment variable name to read.

        Returns
        -------
        str
            The API key value.

        Raises
        ------
        DocumentPortalException
            If the key is missing or empty.
        """

        val = os.getenv(key_name)
        if not val:
            logger.error("Missing environment variable", missing_var=key_name)
            try:
                raise ValueError(f"Missing environmemt variable: {key_name}")
            except Exception as e:
                # Wrap with custom exception for consistent handling
                raise DocumentPortalException(e) from e
        return val

    def load_embeddings(self)-> GoogleGenerativeAIEmbeddings:
        """
        Load and return the embedding model specified in the configuration.

        Returns
        -------
        GoogleGenerativeAIEmbeddings
            A LangChain embeddings instance.

        Raises
        ------
        DocumentPortalException
            If the configuration is invalid or the model fails to load.
        """

        try:
            logger.info("Loading the embedding model")
            emb_cfg = self.config.get("embedding_model") or {}
            model_name = emb_cfg.get("model_name")
            if not model_name:
                raise KeyError("embedding_model.model_name not set in config")
            
            # Ensure Google key present since we are going to use Google Embeddings
            google_key = self._require_api_key("GOOGLE_API_KEY")

            return GoogleGenerativeAIEmbeddings(
                model=model_name,
                google_api_key=google_key)
        except Exception as e:
            logger.exception("Failed to load embedding model")
            raise DocumentPortalException(e) from e

    def load_llm(self):
        """
        Load and return an LLM based on the provider block in the config and LLM_PROVIDER env.

        Environment
        -----------
        LLM_PROVIDER:
            - Defaults to "groq".
            - Must match a key under config["llm"].

        Returns
        -------
        BaseLanguageModel
            A LangChain chat model instance.

        Raises
        ------
        DocumentPortalException
            If configuration is missing/invalid or the model fails to initialize.
        """
        try:

            llm_block = self.config.get("llm")
            if not isinstance(llm_block, dict) or not llm_block:
                raise KeyError("Missing or invalid 'llm' block in config")
            
            # Default provider: Groq if no LLM_PROVIDER is set .env
            provider_key = os.getenv("LLM_PROVIDER", "groq")
            if provider_key not in llm_block:
                raise KeyError(f"Provider '{provider_key} not found in the config['llm']")
        
            llm_config = llm_block[provider_key] or {}
            provider = llm_config.get("provider")
            model_name = llm_config.get("model_name")
            temperature = float(llm_config.get("temperature", 0.2))
            max_output_tokens = int(llm_config.get("max_output_tokens", 2048))

            if not provider or not model_name:
                raise KeyError(f"Missing provider/model_name in llm['{provider_key}']")

            logger.info(
                "Loading LLM",
                provider=provider,
                model_name=model_name,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )

            # Normalize token parameter names:
            #  - ChatGoogleGenerativeAI uses `max_output_tokens`
            #  - ChatGroq and ChatOpenAI use `max_tokens`
            if provider == "google":
                self._require_api_key("GOOGLE_API_KEY")  # Ensure present
                return ChatGoogleGenerativeAI(
                    model=model_name,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )

            if provider == "groq":
                groq_key = self._require_api_key("GROQ_API_KEY")
                return ChatGroq(
                    model=model_name,
                    api_key=groq_key,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                )

            if provider == "openai":
                openai_key = self._require_api_key("OPENAI_API_KEY")
                return ChatOpenAI(
                    model=model_name,
                    api_key=openai_key,
                    temperature=temperature,
                    max_tokens=max_output_tokens, 
                )

            raise ValueError(f"Unsupported LLM provider: {provider}")

        except Exception as e:
            logger.exception("Failed to load LLM")
            raise DocumentPortalException(e) from e

        
if __name__ == "__main__":
    try:
        mdl_loader = ModelLoader()

        # test embedding model
        emb_model = mdl_loader.load_embeddings()
        print(f"Embedding model loaded: {emb_model}")

        # LLM loading
        llm_model = mdl_loader.load_llm()
        print(f"LLM loaded: {llm_model}")

        # Test the working of LLM model
        result = llm_model.invoke("Hello, How are you doing today?")
        print(f"LLM response: {getattr(result, 'content', result)}")

    except DocumentPortalException as e:
        # Custom exception already captures rich context/traceback.
        # logger.exception will include stacktrace in structured logs.
        logger.exception("Fatal error during model loading or inference", error=str(e))
        raise
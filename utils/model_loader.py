import os, sys
from dotenv import load_dotenv
from utils.config_loader import load_config

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

# For logging and Exception handling
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

# Instantiate CustomLogger
logger = CustomLogger().get_logger(__name__)

class ModelLoader:
    def __init__(self):
        load_dotenv()
        self._validate_env()
        self.config = load_config()
        logger.info("Configuration successfully loaded!", config_keys=list(self.config.keys()))

    def _validate_env(self):
        """
        Validate necessary env variables.
        Ensure API key exists
        """
        required_vars = ["GROQ_API_KEY", "GOOGLE_API_KEY"]
        self.api_keys = {key: os.getenv(key) for key in required_vars}
        missing = [ k for k, v in self.api_keys.items() if not v]
        if missing:
            logger.error("Missing environmental variables", missing_vars = missing)
            raise DocumentPortalException(f"Missing environment variables: {missing}")

    def load_embeddings(self):
        """
        Load the embedding model from the configuration and return the same
        """

        try:
            logger.info("Loading the embedding model")
            model_name = self.config["embedding_model"]["model_name"]
            return GoogleGenerativeAIEmbeddings(model=model_name)
        except Exception as e:
            raise DocumentPortalException("Failed to load embedding model", e)

    def load_llm(self):
        """
        Load and return the llm model
        """
        llm_block = self.config["llm"]
        logger.info("Loading LLM config...")

        # Default provider: Groq if no LLM_PROVIDER is set .env
        provider_key = os.getenv("LLM_PROVIDER", "groq")

        if provider_key not in llm_block:
            logger.error("LLM provider not found in config", provider_key=provider_key)
            raise ValueError(f"Provider '{provider_key} not found in the config")
        
        llm_config = llm_block[provider_key]
        provider = llm_config.get("provider")
        model_name = llm_config.get("model_name")
        temperature = llm_config.get("temperature", 0.2)
        max_output_tokens = llm_config.get("max_output_tokens", 2048)

        logger.info("Loading LLM", provider=provider, model_name=model_name, 
                    temperature=temperature, max_output_tokens=max_output_tokens)

        if provider == "google":
            llm = ChatGoogleGenerativeAI(
                model = model_name,
                temperature = temperature,
                max_output_tokens = max_output_tokens
            )
            return llm
        
        elif provider == "groq":
            llm = ChatGroq(
                model = model_name,
                api_key = self.api_keys["GROQ_API_KEY"],
                temperature = temperature,
                max_tokens=max_output_tokens
            )
            return llm
        
        elif provider == "openai":
            llm = ChatOpenAI(
                model=model_name,
                api_key=self.api_keys["OPENAI_API_KEY"],
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )

        else:
            logger.error("Unsupported LLM provider", provider=provider)
            raise ValueError(f"Unsupported LLM provider: {provider}")
        
if __name__ == "__main__":
    mdl_loader = ModelLoader()

    # test embedding model
    emb_model = mdl_loader.load_embeddings()
    print(f"Embedding model loaded: {emb_model}")

    # LLM loading
    llm_model = mdl_loader.load_llm()
    print(f"LLM loaded: {llm_model}")

    # Test the working of LLM model
    result = llm_model.invoke("Hello, How are you doing today?")
    print(f"LLM response: {result.content}")

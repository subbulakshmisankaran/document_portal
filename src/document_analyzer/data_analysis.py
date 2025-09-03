import os
from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from data_model.schemas import *
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser
from prompt.prompt_library import PROMPT_REGISTRY

class DocumentAnalyzer:
    """
    A document analysis service that extracts structured metadata and summaries
    from text documents using LangChain and LLM models.
    
    This class provides robust document analysis with error handling, logging,
    and automatic JSON parsing/fixing capabilities.
    """

    def __init__(self):
        self.logger = CustomLogger().get_logger(__name__)

        try:
            # Initialize the chain to None for lazy loading
            # This improves startup performance by deferring chain creation
            self._chain = None

            # Initialize model loader and load llm
            self.loader = ModelLoader()
            self.llm = self.loader.load_llm()

            # Prepare JSON output parsers for structured data extraction
            # Primary parser converts LLM output to Pydantic Metadata objects
            self.parser = JsonOutputParser(pydantic_object=Metadata)

            # Backup parser that can fix malformed JSON using the LLM
            # This provides resilience against parsing errors
            self.fixing_parser = OutputFixingParser.from_llm(
                parser=self.parser,
                llm = self.llm
                )
            
            # Store the document analysis prompt template from the registry
            # PROMPT_REGISTRY centralizes all prompt templates for maintainability
            self.prompt = PROMPT_REGISTRY["document_analysis"]
            self.logger.info("DocumentAnalyzer initialized successfully")
            
        except Exception as e:
            self.logger.error(str(e))
            raise DocumentPortalException(e)
        
    @property
    def chain(self):
        # Create chain only when first accessed (lazy initialization)
        if self._chain == None:
            # Build the processing pipeline: prompt -> LLM -> parser
            self._chain = self.prompt | self.llm | self.fixing_parser
            self.logger.info("Meta-data analysis chain initialized")

        return self._chain

    def analyse_document(self, document_text:str):
        """
        Analyze a document's text and extract structured metadata and summary
        """
        
        # Validate input parameters
        if not document_text or not document_text.strip():
            raise ValueError("Document text cannot be empty")

        # Calculate and log document characteristics for monitoring
        doc_length = len(document_text)
        word_count = len(document_text.split())
        
        self.logger.info("Starting document analysis", 
                        extra={
                            "doc_length": doc_length,
                            "word_count": word_count
                        })
        
        try:
            # Process document through the LangChain pipeline
            # The chain handles prompt formatting, LLM processing, and JSON parsing
            response = self.chain.invoke({
                "format_instructions": self.parser.get_format_instructions(),
                "document_text": document_text
            })

            # Validate response structure
            if not isinstance(response, dict):
                raise ValueError(f"Expected dict response, got {type(response)}")

            self.logger.info("Metadata extraction is successfully completed",
                             keys=list(response.keys()))


            return response
        
        except Exception as e:
            self.logger.error("Metadata analysis failed", error=str(e))
            raise DocumentPortalException(e)
    
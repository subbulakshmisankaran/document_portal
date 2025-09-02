import os
from utils.model_loader import ModelLoader
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from model.models import *
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser
from prompt.prompt_library import *

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
            # Initialize the chain to None
            self._chain = None
            # Initialize model loader 
            self.loader = ModelLoader()
            self.llm = self.loader.load_llm()

            # Prepare parsers
            self.parser = JsonOutputParser(pydantic_object=Metadata)
            self.fixing_parser = OutputFixingParser.from_llm(
                parser=self.parser,
                llm = self.llm
                )
            
            # Store prompt template
            self.prompt = prompt
            self.logger.info("DocumentAnalyzer initialized successfully")
            
        except Exception as e:
            self.logger.error(str(e))
            raise DocumentPortalException(e)
        
    @property
    def chain(self):
        if self._chain == None:
            self._chain = self.prompt | self.llm | self.fixing_parser
            self.logger.info("Meta-data analysis chain initialized")

        return self._chain

    def analyse_document(self, document_text:str):
        """
        Analyze a document's text and extract structured metadata and summary
        """
        
        if not document_text or not document_text.strip():
            raise ValueError("Document text cannot be empty")

        # Log document characteristics
        doc_length = len(document_text)
        word_count = len(document_text.split())
        
        self.logger.info("Starting document analysis", 
                        extra={
                            "doc_length": doc_length,
                            "word_count": word_count
                        })
        
        try:
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
    
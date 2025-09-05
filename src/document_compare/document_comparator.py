import sys
from dotenv import load_dotenv
import pandas as pd
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from data_model.schemas import *
from prompt.prompt_library import PROMPT_REGISTRY
from utils.model_loader import ModelLoader
from langchain_core.output_parsers import JsonOutputParser
from langchain.output_parsers import OutputFixingParser
from typing import List, Dict

class DocumentComparatorLLM:

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
            # Primary parser converts LLM output to Pydantic SummaryResponse objects
            self.parser = JsonOutputParser(pydantic_object=SummaryResponse)

            
            # Store the document analysis prompt template from the registry
            # PROMPT_REGISTRY centralizes all prompt templates for maintainability
            self.prompt = PROMPT_REGISTRY["document_comparison"]
            self.logger.info("DocumentComparatorLLM initialized successfully")
            
        except Exception as e:
            self.logger.error(str(e))
            raise DocumentPortalException(e)

    @property
    def chain(self):
        # Create chain only when first accessed (lazy initialization)
        if self._chain == None:
            # Build the processing pipeline: prompt -> LLM -> parser
            self._chain = self.prompt | self.llm | self.parser
            self.logger.info("LLM chain initialized")    

        return self._chain

    def compare_documents(self, 
                          ref_file_content:str, 
                          actual_file_content:str) -> pd.DataFrame:
        """
        Run page-wise comparison between two PDF contents using LLM.
        
        Args:
            ref_file_content: Text content of reference document (V1).
            actual_file_content: Text content of actual document (V2).
        
        Returns:
            pd.DataFrame with columns ["Page", "Changes"].
        """

        try:
            inputs = {
                "doc_v1": ref_file_content,
                "doc_v2": actual_file_content, 
                "format_instruction": self.parser.get_format_instructions()
            }

            self.logger.info("Starting document comparison", inputs=inputs)
            response = self.chain.invoke(inputs)
            self.logger.info("Documents compared successfully", response=response)
            return self._format_response(response)

        except Exception as e:
            self.logger.error(f"Error occured while comparing documents: {e}")
            raise DocumentPortalException(e)


    def _format_response(self, response_parsed: List[Dict]) -> pd.DataFrame:
        try:
            df = pd.DataFrame(response_parsed)
            self.logger.info("Response formatted into dataframe", dataframe=df)
            return df
        except Exception as e:
            self.logger.error(f"Error formatting response into Dataframe: {e}")
            raise DocumentPortalException(e)



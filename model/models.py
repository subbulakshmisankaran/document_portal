from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union

class Metadata(BaseModel):
    Summary: List[str] = Field(default_factory=list, description="Summary of the document")
    Title: str = Field(description="Document title")
    Author: str = Field(description="Document author")
    DateCreated: str = Field(description="Date the document was created")
    LastModifiedDate: str = Field(description="Date the document was last modified")
    Publisher: str = Field(description="Document publisher")
    Language: str = Field(description="Language of the document")
    PageCount: Union[int, str] = Field(description="Number of pages in the document")
    SentimentTone: str = Field(description="Overall sentiment/tone of the document")

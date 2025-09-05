from pathlib import Path
import fitz
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
from typing import Tuple, Optional, List
import os
from datetime import datetime
import uuid
import shutil

class DocumentIngestion:
    """
    Handles document ingestion operations including file management and PDF text extraction.
    
    This class provides functionality for:
    - Managing uploaded documents in a designated directory
    - Cleaning up existing files before new uploads
    - Extracting text content from PDF files
    - Validating file types and handling errors gracefully
    """
    def __init__(self, 
                 base_dir:str="./data/document_compare",
                 session_id: str=None):

        self.logger = CustomLogger().get_logger(__name__)
        try:
            self.base_dir = Path(os.getcwd()) / base_dir

            # Generate unique session ID with timestamp and random component
            self.session_id = session_id or f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

            # Create session-specific directory for file isolation
            self.session_path = self.base_dir / self.session_id
            self.session_path.mkdir(parents=True, exist_ok=True)

            self.logger.info("DocumentIngestion initialized successfully", 
                             base_directory = str(self.base_dir),
                             session_id=self.session_id, 
                             session_path=str(self.session_path))

        except Exception as e:
            error_msg = f"Error while initializing DocumentIngestion: {str(e)}"
            self.logger.error(error_msg)
            raise DocumentPortalException(error_msg)
        
    # def delete_existing_files(self)-> None:
    #     """
    #     Clean up all files in the base directory.
        
    #     Removes all files (not directories) from the base directory to prepare
    #     for new file uploads. Logs each deletion for audit trail.
        
    #     Raises:
    #         DocumentPortalException: If file deletion fails
    #     """
    #     try:
    #         # Check if directory exists and is actually a directory
    #         if not self.base_dir.exists():
    #             self.logger.warning(f"Base directory does not exist: {self.base_dir}")
    #             return

    #         if not self.base_dir.is_dir():
    #             error_msg = f"Base path is not a directory: {self.base_dir}"
    #             self.logger.error(error_msg)
    #             raise ValueError(error_msg)

    #         deleted_count = 0
    #         # Iterate through all items in the directory
    #         for file_path in self.base_dir.iterdir():
    #             if file_path.is_file():
    #                 try:
    #                     file_path.unlink()
    #                     deleted_count +=1
    #                     self.logger.info("File deleted", extra={"path": file_path.name})
    #                 except OSError as file_error:
    #                     self.logger.error(f"Could not delete file {file_path.name}: {file_error}")

    #         self.logger.info(f"Directory cleanup completed",
    #                          extra={
    #                              "directory": str(self.base_dir),
    #                              "files_deleted": deleted_count
    #                         })

    #     except Exception as e:
    #         error_msg = f"Error while deleting existing files: {str(e)}"
    #         self.logger.error(error_msg)
    #         raise DocumentPortalException(error_msg)


    def save_uploaded_files(self,
                            ref_file: Path,
                            actual_file: Path) -> Tuple[Path, Path]:
        """
        Save uploaded reference and actual files to the base directory.
        
        Validates file types, cleans existing files, and saves new uploads.
        Both files must be PDF format for processing.
        
        Args:
            ref_file: Reference file object with .name and .get_buffer() methods
            actual_file: Actual file object with .name and .get_buffer() methods
            
        Returns:
            Tuple[Path, Path]: Paths to saved reference and actual files
            
        Raises:
            ValueError: If files are not PDF format
            DocumentPortalException: If file saving fails
        """
        try:
            # Validate file extensions before processing
            if not ref_file.name.lower().endswith(".pdf"):
                raise ValueError(f"Reference file must be PDF, got: {ref_file.name}")
                
            if not actual_file.name.lower().endswith(".pdf"):
                raise ValueError(f"Actual file must be PDF, got: {actual_file.name}")


            # Construct file paths in the base directory
            ref_path = self.session_path / ref_file.name
            actual_path = self.session_path / actual_file.name

            # Check for filename conflicts
            if ref_path == actual_path:
                raise ValueError("Reference and actual files cannot have the same name")

            # Save reference file
            with open(ref_path, "wb") as f:
                f.write(ref_file.get_buffer())

            # Save actual file
            with open(actual_path, "wb") as f:
                f.write(actual_file.get_buffer())

            # Log successful saves with file sizes for monitoring
            ref_size = ref_path.stat().st_size
            actual_size = actual_path.stat().st_size
            
            self.logger.info("Files saved successfully", 
                           extra={
                               "reference_file": str(ref_path),
                               "actual_file": str(actual_path),
                               "ref_size_bytes": ref_size,
                               "actual_size_bytes": actual_size
                           })

            return ref_path, actual_path
        except ValueError:
            # Re-raise ValueError without wrapping
            raise     
        except Exception as e:
            error_msg = f"Error while saving uploaded files: {str(e)}"
            self.logger.error(error_msg)
            raise DocumentPortalException(error_msg)

    def read_pdf(self, pdf_path: Path) -> str:
        """
        Extract text content from a PDF file using PyMuPDF (fitz).
        
        Reads all pages from the PDF and combines them into a single text string
        with page separators. Handles encrypted PDFs and empty pages gracefully.
        
        Args:
            pdf_path (Path): Path object pointing to the PDF file to read
            
        Returns:
            str: Combined text content from all pages with page markers
            
        Raises:
            ValueError: If the PDF is encrypted, doesn't exist, or is invalid
            DocumentPortalException: If PDF reading fails due to file issues or corruption
        """

        # Validate input path
        if not pdf_path.exists():
            error_msg = f"PDF file does not exist: {pdf_path}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not pdf_path.is_file():
            error_msg = f"Path is not a file: {pdf_path}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        try:

            # Open PDF document using PyMuPDF's context manager
            # This ensures proper resource cleanup even if errors occur
            with fitz.open(pdf_path) as doc:
                # Check if PDF is encrypted before attempting to read
                # Encrypted PDFs require passwords which we don't handle here
                if doc.is_encrypted:
                    error_msg = f"PDF is encrypted: {pdf_path.name}"
                    self.logger.error(error_msg)
                    raise ValueError(error_msg)

                # Validate that the document has pages
                if doc.page_count == 0:
                    error_msg = f"PDF has no pages: {pdf_path.name}"
                    self.logger.warning(error_msg)
                    return ""
                
                # Initialize list to store text content from each page
                page_texts = []

                self.logger.info(f"Starting PDF text extraction from {pdf_path}", 
                           extra={"total_pages": doc.page_count})

                # Iterate through all pages in the document
                for page_num in range(doc.page_count):
                    # Load individual page object
                    page = doc.load_page(page_num)
                    # Extract text content from the page
                    page_text = page.get_text()

                    # Only include pages that contain actual text content
                    # This skips empty pages or pages with only images
                    if page_text and page_text.strip():
                        # Add page separator with page number for document structure
                        formatted_page = f"\n--- Page {page_num + 1} ---\n{page_text}"
                        page_texts.append(formatted_page)
                        
                        self.logger.debug(f"Extracted text from page {page_num + 1}", 
                                        extra={"page_text_length": len(page_text)})
                
                total_pages = doc.page_count

            # Combine all page texts into a single string
            combined_text = "\n".join(page_texts)
            
            self.logger.info(f"PDF text extraction completed successfully", 
                           extra={
                               "total_pages": total_pages,
                               "pages_with_text": len(page_texts),
                               "total_text_length": len(combined_text)
                           })
            
            return combined_text
        except ValueError:
            # Re-raise ValueError (encrypted PDF, file not found) without wrapping
            raise
        except Exception as e:
            error_msg = f"Error while reading PDF '{pdf_path.name}': {str(e)}"
            self.logger.error(error_msg, extra={"pdf_path": str(pdf_path)})
            raise DocumentPortalException(error_msg)
        

    def combine_documents(self)-> str:
        try:
            # Check if session directory exists
            if not self.session_path.exists():
                error_msg = f"Session directory does not exist: {self.session_path}"
                self.logger.error(error_msg)
                raise DocumentPortalException(error_msg)
            
            self.logger.info(f"Starting document combination from directory: {self.session_path}")

            # Dictionary to store document contents with metadata
            doc_contents_dict = {}

            # Get all PDF files in the directory (case-insensitive)
            pdf_files = sorted(
                [f for f in self.session_path.iterdir() 
                if f.is_file() and f.name.lower().endswith(".pdf")]
            )
            
            if not pdf_files:
                warning_msg = f"No PDF files found in directory: {self.session_path}"
                self.logger.warning(warning_msg)
                return ""  # Return empty string instead of raising exception
            
            self.logger.info(f"Found {len(pdf_files)} PDF files to process")

            # Process each PDF file
            successful_reads = 0
            failed_reads = 0
            
            for pdf_file in pdf_files:
                try:
                    self.logger.info(f"Processing file: {pdf_file}")
                    
                    # Extract text content from PDF
                    doc_content = self.read_pdf(pdf_file)
                    
                    # Only include documents with content
                    if doc_content and doc_content.strip():
                        # Store content with optional metadata
                        file_info = {
                            'content': doc_content,
                            'file_size': pdf_file.stat().st_size,
                            'char_count': len(doc_content)
                        }
                        doc_contents_dict[pdf_file.name] = file_info
                        successful_reads += 1
                        
                        self.logger.debug(f"Successfully processed {pdf_file.name}", 
                                        extra={
                                            "file_size": file_info['file_size'],
                                            "char_count": file_info['char_count']
                                        })
                    else:
                        self.logger.warning(f"No content extracted from {pdf_file.name}")
                        failed_reads += 1
                        
                except (ValueError, DocumentPortalException) as doc_error:
                    # Log specific document errors but continue processing other files
                    self.logger.warning(f"Failed to process {pdf_file.name}: {str(doc_error)}")
                    failed_reads += 1
                    continue
                    
                except Exception as unexpected_error:
                    # Log unexpected errors but continue processing
                    self.logger.error(f"Unexpected error processing {pdf_file.name}: {str(unexpected_error)}")
                    failed_reads += 1
                    continue

            # Check if any documents were successfully processed
            if not doc_contents_dict:
                error_msg = f"No documents could be processed successfully. Failed: {failed_reads}"
                self.logger.error(error_msg)
                raise DocumentPortalException(error_msg)

            doc_parts = []
            
            for doc_name, doc_info in doc_contents_dict.items():
                doc_parts.append(f"Document: {doc_name}\n{doc_info['content']}")

            combined_text = "\n\n".join(doc_parts)
            self.logger.info("Documents combined successfully", count=len(doc_parts))
            return combined_text
        except DocumentPortalException:
            # Re-raise DocumentPortalException without wrapping
            raise
            
        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error while combining documents: {str(e)}"
            self.logger.error(error_msg, extra={"Session Dir": str(self.session_path)})
            raise DocumentPortalException(error_msg)
        

    def cleanup_sessions(self, keep_latest: int = 3):
        try:
            # Validate input to prevent accidental deletion of all sessions
            if keep_latest < 1:
                self.logger.warning(f"Invalid keep_latest value: {keep_latest}, using default of 3")
                keep_latest = 3
            
            self.logger.info(
                "Starting session cleanup", 
                base_dir=str(self.base_dir), 
                keep_latest=keep_latest
            )
            
            # Check if base directory exists
            if not self.base_dir.exists():
                self.logger.info("Base directory does not exist, nothing to clean")
                return

            # Get all session directories and sort by creation time (newest first)
            # Using creation time ensures we keep the most recently created sessions
            sessions = sorted(
                [f for f in self.base_dir.iterdir() if f.is_dir()], 
                key=lambda x: x.stat().st_ctime,  # Sort by creation time
                reverse=True  # Most recent first
            )
            self.logger.info(f"Found {len(sessions)} session directories")

            # Delete old session directories
            for folder in sessions[keep_latest:]:
                # Use shutil.rmtree for efficient directory deletion
                # ignore_errors=True ensures individual file permission issues 
                # don't stop the entire cleanup process
                shutil.rmtree(folder, ignore_errors=True)

                # Verify deletion was successful
                if not folder.exists():
                    self.logger.info("Old session folder deleted", path=str(folder))
                else:
                    self.logger.warning("Failed to completely delete session", path=str(folder))

        except Exception as e:
            self.logger.error("Error cleaning old sessions", error=str(e))
            raise DocumentPortalException("Error cleaning old sessions", e) from e
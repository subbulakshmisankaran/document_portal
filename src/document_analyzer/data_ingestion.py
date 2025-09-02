import os
import fitz
import uuid
from datetime import datetime
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException 
import re
from typing import Optional
from pathlib import Path
_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9 _.\-()]+")

def _sanitize_filename(name: str) -> str:
    """
    Sanitize a filename for safe filesystem storage.
    
    Removes directory path components and replaces unsafe characters
    with underscores to prevent directory traversal attacks and 
    filesystem compatibility issues.
    
    Args:
        name (str): Original filename (may include path components)
        
    Returns:
        str: Sanitized filename with .pdf extension, max 255 characters
        
    Examples:
        >>> _sanitize_filename("../../../etc/passwd.pdf")
        'passwd.pdf'
        >>> _sanitize_filename("my file@#$.txt")
        'my file__.pdf'
        >>> _sanitize_filename("normal_file.pdf")
        'normal_file.pdf'
    """

    # Extract just the filename part, removing any directory path
    base = Path(name).name
    
    # Replace unsafe characters with underscores for filesystem safety
    # Prevents issues with special chars, Unicode, control characters
    safe = _SAFE_NAME_RE.sub("_", base).strip()

    # Ensure PDF extension (since this handler is PDF-focused)
    if not safe.lower().endswith(".pdf"):
        safe += ".pdf"

    # Limit to 255 chars (filesystem limit on most systems)
    return safe[:255]

class DocumentHandler:
    """
    Production-safe document handler with session management.

    Handles PDF upload, validation, and text extraction with:
    - Session-based file isolation
    - Atomic file operations
    - Input validation and sanitization
    - Size limits and security checks
    
    Designed for extension to other document formats (DOC, DOCX, etc.)
    """

    def __init__(self, 
                 data_dir: str =None,
                 session_id: str=None) -> None:
        """
        Initialize document handler with session management.
        
        Args:
            data_dir (str): Base directory for document storage
            session_id (str, optional): Session identifier. Auto-generated if None.
        """

        try:
            self.logger = CustomLogger().get_logger(__name__)
            # Get the path from env var: DATA_STORAGE_PATH or fallback to <cwd>/data/document_analysis
            # if env var is not configured.
            default_dir = os.getenv(
                "DATA_STORAGE_PATH",
                os.path.join(os.getcwd(), "data", "document_analysis")
            )

            self.data_dir = Path(data_dir or default_dir)

            # Generate unique session ID with timestamp and random component
            self.session_id = session_id or f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

            # Create session-specific directory for file isolation
            self.session_path = self.data_dir / self.session_id
            self.session_path.mkdir(parents=True, exist_ok=True)

            self.logger.info("Document Handler initialized successfully", 
                             session_id=self.session_id, 
                             data_dir=str(self.data_dir),
                             session_path=str(self.session_path))

        except Exception as e:
            raise DocumentPortalException(e) from e

    def save_document(self, 
                      file_name: str,
                      file_stream: bytes,
                      max_size_mb: int=50)->str:
        """
        Validate and save a document file safely using streaming to handle large files.
        
        Currently supports PDF files with validation. Designed for extension
        to other document formats.
        
        Args:
            filename (str): Original filename from upload
            file_stream: File-like object or bytes (supports streaming)
            max_size_mb (int): Maximum file size in megabytes
            
        Returns:
            str: Absolute path to saved file
            
        Raises:
            ValueError: If file is invalid, too large, or wrong format
        """

        try:
            # Handle both bytes and file streams
            if isinstance(file_stream, bytes):
                # Convert bytes to BytesIO for consistent streaming interface
                from io import BytesIO
                file_stream = BytesIO(file_stream)

            self.logger.info(
                "Starting document save process",
                session_id=self.session_id,
                file_name=file_name,
                max_size_mb=max_size_mb
            )

            # Currently only PDFs are allowed
            clean_name = _sanitize_filename(file_name)
            if not clean_name.lower().endswith(".pdf"):
                error_msg = "Only PDF files are currently supported"
                self.logger.error(error_msg, file_name=file_name)
                raise DocumentPortalException(error_msg)


            unique_name = f"{Path(clean_name).stem}_{uuid.uuid4().hex[:8]}.pdf"

            # Use atomic write pattern for reliability
            file_path = self.session_path / unique_name
            temp_path = file_path.with_suffix('.tmp')
            
            self.logger.debug(
                "File paths prepared",
                session_id=self.session_id,
                clean_name=clean_name,
                unique_name=unique_name,
                temp_path=str(temp_path),
                final_path=str(file_path)
            )

            # Stream file in chunks to avoid loading entire file in memory
            chunk_size = 64 * 1024  # 64KB chunks
            total_size = 0
            max_size_bytes = max_size_mb * 1024 * 1024
            pdf_header_checked = False

            with open(temp_path, 'wb') as f:
                while True:
                    chunk = file_stream.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Check size limit incrementally
                    total_size += len(chunk)
                    if total_size > max_size_bytes:
                        error_msg = f"File too large. Max {max_size_mb}MB allowed, got {total_size / (1024*1024):.1f}MB"
                        self.logger.error(error_msg, session_id=self.session_id, total_size=total_size)
                        raise DocumentPortalException(error_msg)
                    
                    # Validate PDF magic header on first chunk
                    if not pdf_header_checked:
                        if not chunk.startswith(b'%PDF-'):
                            error_msg = "File content is not a valid PDF"
                            self.logger.error(error_msg, session_id=self.session_id, file_name=file_name)
                            raise DocumentPortalException(error_msg)
                        pdf_header_checked = True
                        self.logger.debug("PDF header validation passed", session_id=self.session_id)
                    
                    # Write chunk to disk
                    f.write(chunk)
                
                # Ensure all data is written to disk
                f.flush()
                os.fsync(f.fileno())
            
            # Atomic move to final location (prevents partial writes)
            os.replace(temp_path, file_path)
            
            self.logger.info(
                "Document saved successfully",
                session_id=self.session_id,
                file_name=file_name,
                saved_path=str(file_path),
                file_size_bytes=total_size,
                file_size_mb=f"{total_size / (1024*1024):.2f}"
            )
            
            return str(file_path)

        except Exception as e:
            # Clean up temporary file on any error
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()
            
            error_msg = f"Error saving document: {e}"
            self.logger.error(error_msg, 
                              session_id=self.session_id, 
                              file_name=file_name, 
                              error=str(e))
            raise DocumentPortalException(error_msg) from e

    def read_document(self,
                      file_path: str,
                      max_pages: Optional[int] = None) -> str:
        """
        Extract text content from a document file using memory efficient streaming
        
        Currently supports PDF text extraction. Designed for extension
        to other document formats.
        
        Args:
            file_path (str): Absolute path to document file
            max_pages (int, optional): Limit number of pages to process (for large PDFs)

            
        Returns:
            str: Extracted text content with page markers
            
        Raises:
            ValueError: If file cannot be read or processed
        """
        try:

            self.logger.info(
                "Starting document read process",
                session_id=self.session_id,
                file_path=file_path,
                max_pages=max_pages
            )

            # Resolve path and ensure it exists
            path = Path(file_path).resolve(strict=True)

            self.logger.debug(
                "File path resolved",
                session_id=self.session_id,
                resolved_path=str(path)
            )

            # Use generator-based approach for memory efficiency
            def extract_text_generator():
                with fitz.open(path) as doc:
                    total_pages = len(doc)
                    pages_to_process = min(max_pages or total_pages, total_pages)

                    self.logger.debug(
                        "PDF document opened",
                        session_id=self.session_id,
                        total_pages=total_pages,
                        pages_to_process=pages_to_process
                    )

                    for page_num in range(pages_to_process):
                        page = doc[page_num]
                        yield f"\n--- Page {page_num + 1} ---\n"
                        yield page.get_text()
                        yield "\n"
                        
                        # Clear page from memory after processing
                        page = None


            # Build text in chunks to avoid large string concatenations
            text_chunks = []
            chunk_size = 0
            max_chunk_size = 1024 * 1024  # 1MB text chunks
            

            for text_piece in extract_text_generator():
                # Check if adding this piece would exceed the limit
                if chunk_size + len(text_piece) > max_chunk_size:
                    self.logger.warning(
                        "Text extraction stopped due to size limit",
                        session_id=self.session_id,
                        current_chunk_size_mb=f"{chunk_size / (1024*1024):.2f}",
                        would_be_size_mb=f"{(chunk_size + len(text_piece)) / (1024*1024):.2f}",
                        max_chunk_size_mb=f"{max_chunk_size / (1024*1024):.2f}"
                    )
                    break  # Stop BEFORE adding the piece that would exceed limit

                # Safe to add - won't exceed limit
                text_chunks.append(text_piece)
                chunk_size += len(text_piece)

            
            extracted_text = ''.join(text_chunks)

            self.logger.info(
                "Document read successfully",
                session_id=self.session_id,
                file_path=file_path,
                text_length=len(extracted_text),
                text_size_kb=f"{len(extracted_text) / 1024:.1f}"
            )
            
            return extracted_text

        except Exception as e:
            error_msg = f"Error reading document: {e}"
            self.logger.error(error_msg, session_id=self.session_id, file_path=file_path, error=str(e))
            raise DocumentPortalException(error_msg) from e


    def cleanup_session(self):
        """
        Remove all files in the current session directory.
        Useful for cleanup after processing is complete.

        Raises:
            DocumentPortalException: If cleanup fails
        """
        try:
            self.logger.info(
                "Starting session cleanup",
                session_id=self.session_id,
                session_path=str(self.session_path)
            )
            
            files_deleted = 0
            for file_path in self.session_path.iterdir():
                if file_path.is_file(): # Path exists and its a regular file
                    file_path.unlink()
                    files_deleted += 1
                    self.logger.debug(
                        "File deleted during cleanup",
                        session_id=self.session_id,
                        deleted_file=str(file_path)
                    )
            
            self.session_path.rmdir()
            
            self.logger.info(
                "Session cleanup completed successfully",
                session_id=self.session_id,
                files_deleted=files_deleted
            )
            
        except Exception as e:
            error_msg = f"Error cleaning up session: {e}"
            self.logger.error(error_msg, session_id=self.session_id, error=str(e))
            raise DocumentPortalException(error_msg) from e


if __name__ == "__main__":
    from pathlib import Path
    from io import BytesIO
    pdf_path = r"/Users/subbulakshmisankaran/AgenticAI/LLMOps/document_portal/data/document_analysis/Attention_is_all_you_need.pdf"

    doc_handler = DocumentHandler()
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        saved_path = doc_handler.save_document(pdf_path,
                                               pdf_bytes)
        content = doc_handler.read_document(saved_path)
        print("PDF content")
        print(content[:1500])
        doc_handler.cleanup_session()

    except Exception as e:
        print(f"Error: {e}")

    print(f"Session ID: {doc_handler.session_id}")
    print(f"Session Path: {doc_handler.session_path}")



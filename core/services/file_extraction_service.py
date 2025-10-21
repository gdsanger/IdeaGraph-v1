"""
File Text Extraction Service for IdeaGraph

This module provides text extraction from various file formats for storage in Weaviate.
Supports: PDF, TXT, Python, C#, DOCX, and other text-based files.
"""

import logging
import io
import re
from typing import Optional, Dict, Any, List


logger = logging.getLogger('file_extraction_service')


class FileExtractionError(Exception):
    """Base exception for File Extraction errors"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class FileExtractionService:
    """
    File Text Extraction Service
    
    Extracts plain text from various file formats:
    - Plain text files (.txt, .md, .py, .cs, .js, .java, .html, .css, .json, .xml, etc.)
    - PDF files (.pdf)
    - Word documents (.docx)
    
    Handles large files by chunking text if necessary.
    """
    
    # Maximum size for text extraction (25MB as per requirement)
    MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB in bytes
    
    # Maximum chunk size for Weaviate (considering token limits)
    # Weaviate typically supports up to ~100k characters, but we'll use 50k for safety
    MAX_CHUNK_SIZE = 50000
    
    # Text-based file extensions that can be read directly
    TEXT_EXTENSIONS = [
        '.txt', '.md', '.py', '.cs', '.js', '.java', '.c', '.cpp', '.h', '.hpp',
        '.html', '.htm', '.css', '.scss', '.json', '.xml', '.yaml', '.yml',
        '.sh', '.bash', '.sql', '.r', '.rb', '.go', '.php', '.swift', '.kt',
        '.ts', '.tsx', '.jsx', '.vue', '.conf', '.cfg', '.ini', '.log'
    ]
    
    def __init__(self):
        """Initialize the File Extraction Service"""
        pass
    
    def can_extract_text(self, filename: str) -> bool:
        """
        Check if text can be extracted from a file based on its extension
        
        Args:
            filename: Name of the file
            
        Returns:
            bool: True if text extraction is supported
        """
        lower_filename = filename.lower()
        
        # Check for text-based extensions
        for ext in self.TEXT_EXTENSIONS:
            if lower_filename.endswith(ext):
                return True
        
        # Check for PDF
        if lower_filename.endswith('.pdf'):
            return True
        
        # Check for DOCX
        if lower_filename.endswith('.docx'):
            return True
        
        return False
    
    def extract_text(self, content: bytes, filename: str) -> Dict[str, Any]:
        """
        Extract text from file content
        
        Args:
            content: File content as bytes
            filename: Name of the file (used to determine extraction method)
            
        Returns:
            Dict with:
                - success: bool
                - text: str (extracted text)
                - chunks: List[str] (text split into chunks if needed)
                - error: str (if failed)
        """
        # Validate file size
        file_size = len(content)
        if file_size > self.MAX_FILE_SIZE:
            return {
                'success': False,
                'error': f'File size {file_size} bytes exceeds maximum {self.MAX_FILE_SIZE} bytes',
                'text': '',
                'chunks': []
            }
        
        lower_filename = filename.lower()
        
        try:
            # Extract based on file type
            if any(lower_filename.endswith(ext) for ext in self.TEXT_EXTENSIONS):
                text = self._extract_text_from_text_file(content)
            elif lower_filename.endswith('.pdf'):
                text = self._extract_text_from_pdf(content)
            elif lower_filename.endswith('.docx'):
                text = self._extract_text_from_docx(content)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported file type: {filename}',
                    'text': '',
                    'chunks': []
                }
            
            # Clean up text
            text = self._clean_text(text)
            
            # Split into chunks if necessary
            chunks = self._split_into_chunks(text)
            
            logger.info(f"Successfully extracted {len(text)} characters from {filename}, split into {len(chunks)} chunk(s)")
            
            return {
                'success': True,
                'text': text,
                'chunks': chunks,
                'error': ''
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'chunks': []
            }
    
    def _extract_text_from_text_file(self, content: bytes) -> str:
        """
        Extract text from plain text files
        
        Args:
            content: File content as bytes
            
        Returns:
            str: Extracted text
        """
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                text = content.decode(encoding)
                return text
            except UnicodeDecodeError:
                continue
        
        # If all fail, use utf-8 with error handling
        return content.decode('utf-8', errors='ignore')
    
    def _extract_text_from_pdf(self, content: bytes) -> str:
        """
        Extract text from PDF files
        
        Args:
            content: PDF file content as bytes
            
        Returns:
            str: Extracted text
        """
        try:
            import PyPDF2
            
            pdf_file = io.BytesIO(content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page in pdf_reader.pages:
                text_parts.append(page.extract_text())
            
            return '\n'.join(text_parts)
            
        except ImportError:
            logger.warning("PyPDF2 not installed, PDF extraction not available")
            raise FileExtractionError("PDF extraction requires PyPDF2 library")
        except Exception as e:
            logger.error(f"Error extracting PDF text: {str(e)}")
            raise FileExtractionError(f"Failed to extract PDF text: {str(e)}")
    
    def _extract_text_from_docx(self, content: bytes) -> str:
        """
        Extract text from DOCX files
        
        Args:
            content: DOCX file content as bytes
            
        Returns:
            str: Extracted text
        """
        try:
            import docx
            
            docx_file = io.BytesIO(content)
            doc = docx.Document(docx_file)
            
            text_parts = []
            for paragraph in doc.paragraphs:
                text_parts.append(paragraph.text)
            
            return '\n'.join(text_parts)
            
        except ImportError:
            logger.warning("python-docx not installed, DOCX extraction not available")
            raise FileExtractionError("DOCX extraction requires python-docx library")
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {str(e)}")
            raise FileExtractionError(f"Failed to extract DOCX text: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text
        
        Args:
            text: Raw extracted text
            
        Returns:
            str: Cleaned text
        """
        # Remove multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove excessive whitespace
        text = re.sub(r' {2,}', ' ', text)
        
        # Trim whitespace from each line
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    def _split_into_chunks(self, text: str) -> List[str]:
        """
        Split text into chunks if it exceeds maximum chunk size
        
        Args:
            text: Text to split
            
        Returns:
            List[str]: List of text chunks
        """
        if len(text) <= self.MAX_CHUNK_SIZE:
            return [text]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        # Split by paragraphs (double newline)
        paragraphs = text.split('\n\n')
        
        for paragraph in paragraphs:
            paragraph_size = len(paragraph)
            
            # If single paragraph exceeds chunk size, split it
            if paragraph_size > self.MAX_CHUNK_SIZE:
                # Add current chunk if not empty
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Split large paragraph by sentences
                sentences = paragraph.split('. ')
                temp_chunk = []
                temp_size = 0
                
                for sentence in sentences:
                    sentence_size = len(sentence) + 2  # +2 for '. '
                    if temp_size + sentence_size > self.MAX_CHUNK_SIZE and temp_chunk:
                        chunks.append('. '.join(temp_chunk) + '.')
                        temp_chunk = []
                        temp_size = 0
                    
                    temp_chunk.append(sentence)
                    temp_size += sentence_size
                
                if temp_chunk:
                    chunks.append('. '.join(temp_chunk))
                
            # Normal paragraph processing
            elif current_size + paragraph_size + 2 > self.MAX_CHUNK_SIZE:  # +2 for '\n\n'
                # Current chunk is full, save it
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_size = paragraph_size
            else:
                current_chunk.append(paragraph)
                current_size += paragraph_size + 2
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks

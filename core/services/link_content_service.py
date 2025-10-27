"""
Link Content Extraction Service for IdeaGraph

This module provides functionality to:
- Download content from URLs
- Clean HTML content (remove scripts, styles, etc.)
- Send content to KiGate API for AI processing
- Save processed content as markdown files
- Store in Weaviate vector database
"""

import logging
import re
import requests
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from html.parser import HTMLParser
from django.db import transaction

from core.services.kigate_service import KiGateService, KiGateServiceError
from core.services.task_file_service import TaskFileService, TaskFileServiceError


logger = logging.getLogger('link_content_service')


class LinkContentServiceError(Exception):
    """Base exception for Link Content Service errors"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to structured dictionary"""
        return {
            'success': False,
            'error': self.message,
            'details': self.details or ''
        }


class HTMLCleaner(HTMLParser):
    """
    HTML parser to extract clean text content from HTML.
    Removes scripts, styles, and other non-content elements.
    """
    
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text_parts = []
        self.skip_tags = {'script', 'style', 'head', 'meta', 'link', 'noscript'}
        self.current_tag = None
    
    def handle_starttag(self, tag, attrs):
        """Handle opening tags"""
        if tag.lower() in self.skip_tags:
            self.current_tag = tag.lower()
    
    def handle_endtag(self, tag):
        """Handle closing tags"""
        if tag.lower() in self.skip_tags:
            self.current_tag = None
    
    def handle_data(self, data):
        """Handle text data"""
        # Only add text if we're not inside a skip tag
        if self.current_tag is None:
            # Clean up whitespace
            text = data.strip()
            if text:
                self.text_parts.append(text)
    
    def get_text(self) -> str:
        """Get the extracted text"""
        return '\n'.join(self.text_parts)


class LinkContentService:
    """
    Link Content Extraction Service
    
    Downloads content from URLs, cleans HTML, sends to KiGate AI for processing,
    and saves the result as markdown files in tasks.
    """
    
    # Maximum content size to send to AI (considering token limits)
    # Assuming ~4 chars per token, and kigate_max_tokens setting
    MAX_CONTENT_SIZE = 200000  # 200k characters (~50k tokens)
    
    # User agent for HTTP requests
    USER_AGENT = 'Mozilla/5.0 (compatible; IdeaGraph/1.0; +https://idea.angermeier.net)'
    
    def __init__(self, settings=None):
        """
        Initialize LinkContentService
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise LinkContentServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise LinkContentServiceError("No settings found in database")
        
        self.kigate_service = None
        self.task_file_service = None
    
    def _get_kigate_service(self) -> KiGateService:
        """Get or create KiGate Service instance"""
        if self.kigate_service is None:
            try:
                self.kigate_service = KiGateService(self.settings)
            except KiGateServiceError as e:
                raise LinkContentServiceError(
                    f"Failed to initialize KiGate service: {e.message}",
                    details=e.details
                )
        return self.kigate_service
    
    def _get_task_file_service(self) -> TaskFileService:
        """Get or create Task File Service instance"""
        if self.task_file_service is None:
            try:
                self.task_file_service = TaskFileService(self.settings)
            except TaskFileServiceError as e:
                raise LinkContentServiceError(
                    f"Failed to initialize Task File service: {e.message}",
                    details=e.details
                )
        return self.task_file_service
    
    def download_url_content(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Download content from URL
        
        Args:
            url: URL to download
            timeout: Request timeout in seconds
            
        Returns:
            Dict with:
                - success: bool
                - content: str (HTML content)
                - title: str (page title if found)
                - url: str (final URL after redirects)
                - error: str (if failed)
        """
        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise LinkContentServiceError(
                    "Invalid URL format",
                    details="URL must include scheme (http/https) and domain"
                )
            
            # Make request with user agent
            headers = {
                'User-Agent': self.USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            logger.info(f"Downloading content from: {url}")
            response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            
            # Check status code
            if response.status_code != 200:
                raise LinkContentServiceError(
                    f"Failed to download URL: HTTP {response.status_code}",
                    details=response.text[:500]
                )
            
            # Check content type
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                raise LinkContentServiceError(
                    "URL does not return HTML content",
                    details=f"Content-Type: {content_type}"
                )
            
            # Get content
            html_content = response.text
            
            # Extract title from HTML
            title = self._extract_title(html_content)
            
            logger.info(f"Successfully downloaded {len(html_content)} bytes from {url}")
            
            return {
                'success': True,
                'content': html_content,
                'title': title or 'Untitled',
                'url': response.url  # Final URL after redirects
            }
        
        except requests.exceptions.Timeout:
            error_msg = f"Request timed out after {timeout} seconds"
            logger.error(error_msg)
            raise LinkContentServiceError(error_msg)
        
        except requests.exceptions.ConnectionError as e:
            error_msg = "Failed to connect to URL"
            logger.error(f"{error_msg}: {str(e)}")
            raise LinkContentServiceError(error_msg, details=str(e))
        
        except requests.exceptions.RequestException as e:
            error_msg = "Failed to download URL"
            logger.error(f"{error_msg}: {str(e)}")
            raise LinkContentServiceError(error_msg, details=str(e))
    
    def _extract_title(self, html: str) -> Optional[str]:
        """
        Extract page title from HTML
        
        Args:
            html: HTML content
            
        Returns:
            str: Page title or None
        """
        # Limit search scope to first 10KB to prevent ReDoS
        search_html = html[:10000].lower()
        
        # Simple find-based extraction to avoid regex ReDoS issues
        # Try to extract title tag
        title_start = search_html.find('<title')
        if title_start != -1:
            # Find the end of the opening tag
            content_start = search_html.find('>', title_start)
            if content_start != -1:
                content_start += 1
                # Find the closing tag
                title_end = search_html.find('</title>', content_start)
                if title_end != -1:
                    # Extract title from original HTML (preserving case)
                    title = html[content_start:title_end].strip()
                    # Clean up whitespace
                    title = re.sub(r'\s+', ' ', title)
                    if title:
                        return title
        
        # Try to extract h1 tag as fallback
        h1_start = search_html.find('<h1')
        if h1_start != -1:
            # Find the end of the opening tag
            content_start = search_html.find('>', h1_start)
            if content_start != -1:
                content_start += 1
                # Find the closing tag
                h1_end = search_html.find('</h1>', content_start)
                if h1_end != -1:
                    # Extract from original HTML
                    h1_content = html[content_start:h1_end].strip()
                    # Remove any remaining tags (simple approach)
                    h1_text = h1_content
                    while '<' in h1_text:
                        tag_start = h1_text.find('<')
                        tag_end = h1_text.find('>', tag_start)
                        if tag_end != -1:
                            h1_text = h1_text[:tag_start] + h1_text[tag_end+1:]
                        else:
                            break
                    h1_text = h1_text.strip()
                    if h1_text:
                        return h1_text
        
        return None
    
    def clean_html_content(self, html: str) -> Dict[str, Any]:
        """
        Clean HTML content by removing scripts, styles, and extracting body text
        
        Args:
            html: Raw HTML content
            
        Returns:
            Dict with:
                - success: bool
                - text: str (cleaned text content)
                - error: str (if failed)
        """
        try:
            logger.info(f"Cleaning HTML content ({len(html)} bytes)")
            
            # Limit total HTML size to prevent excessive processing
            max_html_size = 1000000  # 1MB
            if len(html) > max_html_size:
                logger.warning(f"HTML content too large ({len(html)} bytes), truncating to {max_html_size}")
                html = html[:max_html_size]
            
            # Remove comments using simple string replacement to avoid ReDoS
            # Find and remove all HTML comments
            while '<!--' in html:
                comment_start = html.find('<!--')
                if comment_start == -1:
                    break
                comment_end = html.find('-->', comment_start)
                if comment_end == -1:
                    # Malformed comment, just remove from start
                    html = html[:comment_start]
                    break
                html = html[:comment_start] + html[comment_end + 3:]
            
            # Try to extract body content using simple find
            html_lower = html.lower()
            body_start = html_lower.find('<body')
            if body_start != -1:
                # Find the end of the opening body tag
                content_start = html_lower.find('>', body_start)
                if content_start != -1:
                    content_start += 1
                    # Find the closing body tag
                    body_end = html_lower.find('</body>', content_start)
                    if body_end != -1:
                        html = html[content_start:body_end]
            
            # Use HTML parser to extract clean text
            cleaner = HTMLCleaner()
            cleaner.feed(html)
            text = cleaner.get_text()
            
            # Additional cleanup
            # Remove extra whitespace
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            text = text.strip()
            
            logger.info(f"Cleaned HTML to {len(text)} characters of text")
            
            return {
                'success': True,
                'text': text
            }
        
        except Exception as e:
            error_msg = "Failed to clean HTML content"
            logger.error(f"{error_msg}: {str(e)}")
            raise LinkContentServiceError(error_msg, details=str(e))
    
    def process_with_ai(
        self,
        content: str,
        title: str,
        url: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Process cleaned content with KiGate AI agent
        
        Args:
            content: Cleaned text content
            title: Page title
            url: Source URL
            user_id: User ID for tracking
            
        Returns:
            Dict with:
                - success: bool
                - markdown: str (formatted markdown content)
                - error: str (if failed)
        """
        try:
            # Check token limit
            max_tokens = self.settings.kigate_max_tokens or 10000
            # Rough estimate: 4 chars per token
            max_chars = max_tokens * 4
            
            # Truncate if too large
            if len(content) > max_chars:
                logger.warning(
                    f"Content too large ({len(content)} chars), truncating to {max_chars} chars"
                )
                content = content[:max_chars]
                content += "\n\n[Content truncated due to size limit]"
            
            # Prepare message for AI agent
            message = f"""Please process and format the following web content into clean markdown format.

Source URL: {url}
Page Title: {title}

Content:
{content}

Instructions:
- Extract and structure the main content
- Remove any remaining navigation, ads, or irrelevant elements
- Format as clean, readable markdown
- Preserve important links, headings, and structure
- Keep the title and source URL at the top
"""
            
            logger.info(f"Sending content to KiGate AI agent (length: {len(message)} chars)")
            
            # Execute KiGate agent
            kigate = self._get_kigate_service()
            result = kigate.execute_agent(
                agent_name="web-content-extraction-and-formatting-agent",
                provider="openai",  # Default provider
                model="gpt-4",  # Default model
                message=message,
                user_id=user_id
            )
            
            if not result.get('success'):
                raise LinkContentServiceError(
                    "AI agent execution failed",
                    details=result.get('error', 'Unknown error')
                )
            
            markdown_content = result.get('result', '')
            
            if not markdown_content:
                raise LinkContentServiceError(
                    "AI agent returned empty result"
                )
            
            logger.info(f"Successfully processed content with AI (result: {len(markdown_content)} chars)")
            
            return {
                'success': True,
                'markdown': markdown_content
            }
        
        except KiGateServiceError as e:
            error_msg = f"KiGate AI processing failed: {e.message}"
            logger.error(error_msg)
            raise LinkContentServiceError(error_msg, details=e.details)
        
        except Exception as e:
            error_msg = "Failed to process content with AI"
            logger.error(f"{error_msg}: {str(e)}")
            raise LinkContentServiceError(error_msg, details=str(e))
    
    def normalize_filename(self, title: str) -> str:
        """
        Normalize title to create safe filename
        
        Args:
            title: Page title
            
        Returns:
            str: Normalized filename (without extension)
        """
        # Remove special characters
        filename = re.sub(r'[^\w\s-]', '', title)
        # Replace spaces with underscores
        filename = re.sub(r'\s+', '_', filename)
        # Limit length
        if len(filename) > 100:
            filename = filename[:100]
        # Remove trailing underscores
        filename = filename.strip('_')
        # Ensure not empty
        if not filename:
            filename = 'web_content'
        
        return filename
    
    def save_as_task_file(
        self,
        task,
        markdown_content: str,
        filename: str,
        user
    ) -> Dict[str, Any]:
        """
        Save markdown content as a task file
        
        Args:
            task: Task object
            markdown_content: Markdown formatted content
            filename: Filename (without extension)
            user: User object
            
        Returns:
            Dict with:
                - success: bool
                - file: TaskFile object
                - error: str (if failed)
        """
        try:
            # Add .md extension
            full_filename = f"{filename}.md"
            
            # Convert to bytes
            content_bytes = markdown_content.encode('utf-8')
            
            logger.info(f"Saving markdown content as task file: {full_filename}")
            
            # Use task file service to upload
            task_file_service = self._get_task_file_service()
            result = task_file_service.upload_file(
                task=task,
                file_content=content_bytes,
                filename=full_filename,
                content_type='text/markdown',
                user=user
            )
            
            if not result.get('success'):
                raise LinkContentServiceError(
                    "Failed to save file",
                    details=result.get('error', 'Unknown error')
                )
            
            logger.info(f"Successfully saved task file: {full_filename}")
            
            return result
        
        except TaskFileServiceError as e:
            error_msg = f"Failed to save task file: {e.message}"
            logger.error(error_msg)
            raise LinkContentServiceError(error_msg, details=e.details)
        
        except Exception as e:
            error_msg = "Failed to save task file"
            logger.error(f"{error_msg}: {str(e)}")
            raise LinkContentServiceError(error_msg, details=str(e))
    
    def process_link(
        self,
        task,
        url: str,
        user
    ) -> Dict[str, Any]:
        """
        Complete workflow: Download, clean, process, and save link content
        
        Args:
            task: Task object
            url: URL to process
            user: User object
            
        Returns:
            Dict with:
                - success: bool
                - file: TaskFile object
                - title: str (page title)
                - message: str (success message)
                - error: str (if failed)
        """
        try:
            logger.info(f"Processing link: {url} for task {task.id}")
            
            # Step 1: Download content
            download_result = self.download_url_content(url)
            html_content = download_result['content']
            title = download_result['title']
            final_url = download_result['url']
            
            # Step 2: Clean HTML
            clean_result = self.clean_html_content(html_content)
            cleaned_text = clean_result['text']
            
            # Step 3: Process with AI
            ai_result = self.process_with_ai(
                content=cleaned_text,
                title=title,
                url=final_url,
                user_id=str(user.id)
            )
            markdown_content = ai_result['markdown']
            
            # Step 4: Normalize filename
            filename = self.normalize_filename(title)
            
            # Step 5: Save as task file (this also syncs to Weaviate)
            file_result = self.save_as_task_file(
                task=task,
                markdown_content=markdown_content,
                filename=filename,
                user=user
            )
            
            logger.info(f"Successfully processed link: {url}")
            
            return {
                'success': True,
                'file': file_result.get('file'),
                'title': title,
                'message': f"Successfully processed and saved content from: {title}"
            }
        
        except LinkContentServiceError:
            raise
        
        except Exception as e:
            error_msg = "Failed to process link"
            logger.error(f"{error_msg}: {str(e)}")
            raise LinkContentServiceError(error_msg, details=str(e))

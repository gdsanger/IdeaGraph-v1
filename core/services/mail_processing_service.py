"""
Mail Processing Service for IdeaGraph

This module provides AI-powered mail processing functionality:
- Retrieves emails from mailbox via Graph API
- Matches emails to Items using RAG (Weaviate)
- Generates normalized task descriptions using AI
- Creates tasks and sends confirmation emails
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from core.services.graph_service import GraphService, GraphServiceError
from core.services.weaviate_sync_service import WeaviateItemSyncService, WeaviateItemSyncServiceError
from core.services.kigate_service import KiGateService, KiGateServiceError
from core.services.openai_service import OpenAIService, OpenAIServiceError


logger = logging.getLogger('mail_processing_service')


class MailProcessingServiceError(Exception):
    """Base exception for Mail Processing Service errors"""
    
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


class MailProcessingService:
    """
    Mail Processing Service
    
    Handles the complete workflow of:
    1. Retrieving emails from mailbox
    2. Converting HTML to Markdown
    3. Finding matching Items using RAG
    4. Generating normalized task descriptions
    5. Creating tasks
    6. Sending confirmation emails
    """
    
    def __init__(self, settings=None):
        """
        Initialize MailProcessingService with settings
        
        Args:
            settings: Settings object. If None, will fetch from database
        """
        if settings is None:
            from main.models import Settings
            try:
                settings = Settings.objects.first()
            except Exception as e:
                logger.error(f"Failed to load settings: {str(e)}")
                raise MailProcessingServiceError("Failed to load settings", details=str(e))
        
        self.settings = settings
        
        if not self.settings:
            raise MailProcessingServiceError("No settings found in database")
        
        # Initialize services
        try:
            self.graph_service = GraphService(settings)
            self.weaviate_service = WeaviateItemSyncService(settings)
            self.kigate_service = KiGateService(settings) if settings.kigate_api_enabled else None
            self.openai_service = OpenAIService(settings) if settings.openai_api_enabled else None
        except Exception as e:
            logger.error(f"Failed to initialize services: {str(e)}")
            raise MailProcessingServiceError("Failed to initialize services", details=str(e))
    
    def convert_html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML content to Markdown using KiGate agent
        
        Args:
            html_content: HTML string to convert
            
        Returns:
            Markdown string
        """
        if not self.kigate_service:
            logger.warning("KiGate service not available, using fallback HTML-to-Markdown conversion")
            return self._basic_html_to_markdown(html_content)
        
        try:
            result = self.kigate_service.execute_agent(
                agent_name='html-to-markdown-converter',
                provider='openai',
                model='gpt-4',
                message=html_content,
                user_id='system'
            )
            
            if result.get('success'):
                markdown = result.get('result', '')
                # Verify that we actually got markdown back (not HTML)
                if markdown and not (markdown.strip().startswith('<') and '>' in markdown):
                    logger.info("Successfully converted HTML to Markdown")
                    return markdown
                else:
                    logger.warning("HTML to Markdown conversion returned HTML-like content, using fallback")
                    return self._basic_html_to_markdown(html_content)
            else:
                logger.warning("HTML to Markdown conversion failed, using fallback")
                return self._basic_html_to_markdown(html_content)
                
        except KiGateServiceError as e:
            logger.warning(f"KiGate service error: {e.message}, using fallback HTML-to-Markdown conversion")
            return self._basic_html_to_markdown(html_content)
    
    def _basic_html_to_markdown(self, html_content: str) -> str:
        """
        Basic fallback method to convert HTML to Markdown
        
        Uses Python's html.parser to parse HTML and convert to markdown format.
        This is a simple converter for common HTML elements.
        
        Args:
            html_content: HTML string to convert
            
        Returns:
            Markdown string with basic formatting
        """
        from html.parser import HTMLParser
        
        class HTMLToMarkdownParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.markdown = []
                self.current_tag = []
                self.list_level = 0
                self.in_pre = False
                self.link_text = None
                self.link_href = None
                self.list_stack = []  # Track list types (ul/ol)
                self.list_item_counter = 0
                
            def handle_starttag(self, tag, attrs):
                self.current_tag.append(tag)
                
                if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    level = int(tag[1])
                    self.markdown.append('\n' + '#' * level + ' ')
                elif tag == 'p':
                    self.markdown.append('\n\n')
                elif tag == 'br':
                    self.markdown.append('  \n')
                elif tag == 'hr':
                    self.markdown.append('\n\n---\n\n')
                elif tag == 'strong' or tag == 'b':
                    self.markdown.append('**')
                elif tag == 'em' or tag == 'i':
                    self.markdown.append('*')
                elif tag == 'code':
                    if not self.in_pre:
                        self.markdown.append('`')
                elif tag == 'pre':
                    self.in_pre = True
                    self.markdown.append('\n\n```\n')
                elif tag == 'a':
                    self.link_text = []
                    for attr_name, attr_value in attrs:
                        if attr_name == 'href':
                            self.link_href = attr_value
                            break
                elif tag == 'ul':
                    self.markdown.append('\n')
                    self.list_stack.append('ul')
                    self.list_item_counter = 0
                elif tag == 'ol':
                    self.markdown.append('\n')
                    self.list_stack.append('ol')
                    self.list_item_counter = 0
                elif tag == 'li':
                    # Check if we're in an ordered or unordered list
                    if self.list_stack and self.list_stack[-1] == 'ol':
                        self.list_item_counter += 1
                        self.markdown.append(f'\n{"  " * self.list_level}{self.list_item_counter}. ')
                    else:
                        self.markdown.append('\n' + '  ' * self.list_level + '- ')
                elif tag == 'blockquote':
                    self.markdown.append('\n> ')
            
            def handle_endtag(self, tag):
                if self.current_tag and self.current_tag[-1] == tag:
                    self.current_tag.pop()
                
                if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    self.markdown.append('\n')
                elif tag == 'p':
                    pass  # Already handled in starttag
                elif tag == 'strong' or tag == 'b':
                    self.markdown.append('**')
                elif tag == 'em' or tag == 'i':
                    self.markdown.append('*')
                elif tag == 'code':
                    if not self.in_pre:
                        self.markdown.append('`')
                elif tag == 'pre':
                    self.in_pre = False
                    self.markdown.append('\n```\n\n')
                elif tag == 'a':
                    if self.link_text and self.link_href:
                        text = ''.join(self.link_text)
                        self.markdown.append(f'[{text}]({self.link_href})')
                        self.link_text = None
                        self.link_href = None
                elif tag in ['ul', 'ol']:
                    if self.list_stack:
                        self.list_stack.pop()
                    self.markdown.append('\n')
            
            def handle_data(self, data):
                # Skip whitespace-only data in certain contexts
                if data.strip() or (self.current_tag and self.current_tag[-1] in ['p', 'li', 'td', 'th']):
                    if self.link_text is not None:
                        self.link_text.append(data)
                    else:
                        self.markdown.append(data)
            
            def get_markdown(self):
                result = ''.join(self.markdown)
                # Clean up excessive newlines
                import re
                result = re.sub(r'\n{3,}', '\n\n', result)
                return result.strip()
        
        try:
            parser = HTMLToMarkdownParser()
            parser.feed(html_content)
            markdown = parser.get_markdown()
            logger.info("Applied basic HTML-to-Markdown conversion")
            return markdown
        except Exception as e:
            logger.warning(f"HTML parsing failed: {str(e)}, returning cleaned text")
            # Fallback: strip all HTML tags and return plain text
            import re
            text = re.sub(r'<[^>]+>', '', html_content)
            return text.strip()
    
    def convert_markdown_to_html(self, markdown_content: str) -> str:
        """
        Convert Markdown content to HTML using KiGate agent
        
        Args:
            markdown_content: Markdown string to convert
            
        Returns:
            HTML string
        """
        if not self.kigate_service:
            logger.warning("KiGate service not available, using basic markdown-to-html conversion")
            return self._basic_markdown_to_html(markdown_content)
        
        try:
            result = self.kigate_service.execute_agent(
                agent_name='markdown-to-html-converter',
                provider='openai',
                model='gpt-4',
                message=markdown_content,
                user_id='system'
            )
            
            if result.get('success'):
                html = result.get('result', '')
                # Verify that we actually got HTML back
                if html and ('<' in html and '>' in html):
                    logger.info("Successfully converted Markdown to HTML")
                    return html
                else:
                    logger.warning("Markdown to HTML conversion returned non-HTML content, using fallback")
                    return self._basic_markdown_to_html(markdown_content)
            else:
                logger.warning("Markdown to HTML conversion failed, using fallback")
                return self._basic_markdown_to_html(markdown_content)
                
        except KiGateServiceError as e:
            logger.warning(f"KiGate service error: {e.message}, using fallback conversion")
            return self._basic_markdown_to_html(markdown_content)
    
    def _basic_markdown_to_html(self, markdown_content: str) -> str:
        """
        Basic fallback method to convert common markdown patterns to HTML
        
        Args:
            markdown_content: Markdown string to convert
            
        Returns:
            HTML string with basic formatting
        """
        import re
        
        html = markdown_content
        
        # Convert headers (must be done before other conversions)
        html = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # Convert bold
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html)
        
        # Convert italic
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        html = re.sub(r'_(.*?)_', r'<em>\1</em>', html)
        
        # Convert links
        html = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html)
        
        # Convert unordered lists
        lines = html.split('\n')
        in_list = False
        result_lines = []
        for line in lines:
            if re.match(r'^\s*[-*+]\s+', line):
                if not in_list:
                    result_lines.append('<ul>')
                    in_list = True
                # Remove the list marker and wrap in <li>
                list_item = re.sub(r'^\s*[-*+]\s+', '', line)
                result_lines.append(f'<li>{list_item}</li>')
            else:
                if in_list:
                    result_lines.append('</ul>')
                    in_list = False
                result_lines.append(line)
        if in_list:
            result_lines.append('</ul>')
        html = '\n'.join(result_lines)
        
        # Convert ordered lists
        lines = html.split('\n')
        in_list = False
        result_lines = []
        for line in lines:
            if re.match(r'^\s*\d+\.\s+', line):
                if not in_list:
                    result_lines.append('<ol>')
                    in_list = True
                # Remove the list marker and wrap in <li>
                list_item = re.sub(r'^\s*\d+\.\s+', '', line)
                result_lines.append(f'<li>{list_item}</li>')
            else:
                if in_list:
                    result_lines.append('</ol>')
                    in_list = False
                result_lines.append(line)
        if in_list:
            result_lines.append('</ol>')
        html = '\n'.join(result_lines)
        
        # Convert horizontal rules
        html = re.sub(r'^---$', r'<hr>', html, flags=re.MULTILINE)
        html = re.sub(r'^\*\*\*$', r'<hr>', html, flags=re.MULTILINE)
        
        # Convert line breaks (double newline to paragraph)
        paragraphs = html.split('\n\n')
        formatted_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if para and not para.startswith('<'):
                # Only wrap in <p> if not already an HTML tag
                formatted_paragraphs.append(f'<p>{para}</p>')
            else:
                formatted_paragraphs.append(para)
        html = '\n'.join(formatted_paragraphs)
        
        # Convert remaining single newlines to <br> within paragraphs
        html = re.sub(r'(?<!>)\n(?!<)', '<br>', html)
        
        logger.info("Applied basic markdown-to-html conversion")
        return html
    
    def find_matching_item(self, mail_content: str, n_results: int = 5) -> Optional[Dict[str, Any]]:
        """
        Find the best matching Item for an email using RAG
        
        Args:
            mail_content: Email content (subject + body)
            n_results: Number of similar items to retrieve
            
        Returns:
            Dictionary with best matching item info, or None if no match
        """
        try:
            # Search for similar items using Weaviate
            search_result = self.weaviate_service.search_similar(
                query_text=mail_content,
                n_results=n_results
            )
            
            if not search_result.get('success') or not search_result.get('results'):
                logger.warning("No similar items found")
                return None
            
            similar_items = search_result['results']
            
            # Use OpenAI to determine the best match
            if self.openai_service and len(similar_items) > 1:
                items_context = self._format_items_for_ai(similar_items)
                
                prompt = f"""Basierend auf dem nachfolgenden E-Mail-Inhalt und der Liste verfügbarer Items, bestimme welches Item am BESTEN zu dieser E-Mail passt. Berücksichtige den Kontext und die Relevanz.

E-Mail-Inhalt:
{mail_content}

Verfügbare Items:
{items_context}

Bitte antworte NUR mit der Item-ID (UUID) des am besten passenden Items. Falls keines relevant ist, antworte mit "NONE".
"""
                
                try:
                    response = self.openai_service.chat_completion(
                        messages=[{'role': 'user', 'content': prompt}],
                        model=self.settings.openai_default_model or 'gpt-4'
                    )
                    
                    if response.get('success'):
                        ai_choice = response.get('content', '').strip()
                        
                        # Try to find the selected item
                        for item in similar_items:
                            if item['id'] in ai_choice or ai_choice == item['id']:
                                logger.info(f"AI selected best matching item: {item['id']}")
                                return item
                
                except OpenAIServiceError as e:
                    logger.warning(f"OpenAI selection failed: {e.message}, using first result")
            
            # Fallback: return the item with lowest distance (most similar)
            best_match = min(similar_items, key=lambda x: x.get('distance', float('inf')))
            logger.info(f"Returning best match by distance: {best_match['id']}")
            return best_match
            
        except WeaviateItemSyncServiceError as e:
            logger.error(f"Weaviate search failed: {e.message}")
            return None
    
    def _format_items_for_ai(self, items: List[Dict[str, Any]]) -> str:
        """Format items list for AI prompt"""
        formatted = []
        for i, item in enumerate(items, 1):
            metadata = item.get('metadata', {})
            formatted.append(
                f"{i}. ID: {item['id']}\n"
                f"   Title: {metadata.get('title', 'N/A')}\n"
                f"   Description: {metadata.get('description', 'N/A')[:200]}...\n"
                f"   Section: {metadata.get('section', 'N/A')}\n"
                f"   Status: {metadata.get('status', 'N/A')}\n"
            )
        return "\n".join(formatted)
    
    def generate_normalized_description(
        self,
        mail_subject: str,
        mail_body: str,
        item_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a normalized task description from email content using KiGate AI agent
        
        Args:
            mail_subject: Email subject
            mail_body: Email body (in Markdown)
            item_context: Optional context from the matched Item
            
        Returns:
            Normalized description string in Markdown format
        """
        if not self.kigate_service:
            logger.warning("KiGate service not available, returning original mail body")
            return f"{mail_body}\n\n---\n**Originale E-Mail:**\n\nBetreff: {mail_subject}\n\n{mail_body}"
        
        # Build context from item if available
        item_title = "N/A"
        item_description = "N/A"
        if item_context:
            metadata = item_context.get('metadata', {})
            item_title = metadata.get('title', 'N/A')
            item_description = metadata.get('description', 'N/A')[:500] if metadata.get('description') else 'No description'
        
        # Prepare context for AI agent similar to Teams integration pattern
        ai_prompt = f"""Item: {item_title}
Item Description: {item_description}

E-Mail-Betreff: {mail_subject}

E-Mail-Text:
{mail_body}

Analyze this email and create a normalized task description in Markdown format:
1. Provide a clear, actionable task description in German
2. Stay within the context of the email content
3. Use the Item context to add relevant details
4. Keep the description concise and action-oriented
5. If there are unclear or open points, list them at the end with "ggf. noch zu klären:"
6. At the very end, preserve the original email content under a section "---\\nOriginale E-Mail:"
"""
        
        try:
            logger.info("Generating normalized description with KiGate agent: teams-support-analysis-agent")
            
            # Execute KiGate agent
            result = self.kigate_service.execute_agent(
                agent_name='teams-support-analysis-agent',
                provider='openai',
                model='gpt-4',
                message=ai_prompt,
                user_id='system',
                parameters={
                    'mail_subject': mail_subject,
                    'item_id': item_context.get('id') if item_context else None,
                    'item_title': item_title
                }
            )
            
            if result.get('success'):
                normalized = result.get('result', '')
                logger.info("Successfully generated normalized description with KiGate agent")
                return normalized
            else:
                logger.warning("KiGate agent execution failed, returning formatted original")
                return f"{mail_body}\n\n---\n**Originale E-Mail:**\n\nBetreff: {mail_subject}\n\n{mail_body}"
                
        except KiGateServiceError as e:
            logger.error(f"KiGate service error: {e.message}")
            return f"{mail_body}\n\n---\n**Originale E-Mail:**\n\nBetreff: {mail_subject}\n\n{mail_body}"
    
    def process_attachments(
        self,
        message_id: str,
        task,
        user
    ) -> Dict[str, Any]:
        """
        Process attachments from an email message
        
        Downloads attachments, saves them to SharePoint in the task folder,
        and syncs readable files to Weaviate.
        
        Args:
            message_id: ID of the email message
            task: Task object to attach files to
            user: User who will be listed as uploader
            
        Returns:
            Dictionary with:
                - success: bool
                - processed: int (number of attachments processed)
                - failed: int (number of failed attachments)
                - details: list of attachment processing results
        """
        try:
            # Import TaskFileService here to avoid circular imports
            from core.services.task_file_service import TaskFileService
            
            # Get attachments list
            attachments_result = self.graph_service.get_message_attachments(message_id)
            
            if not attachments_result.get('success'):
                logger.warning("Failed to retrieve attachments")
                return {
                    'success': False,
                    'processed': 0,
                    'failed': 0,
                    'details': []
                }
            
            attachments = attachments_result.get('attachments', [])
            
            if not attachments:
                logger.info("No attachments found in message")
                return {
                    'success': True,
                    'processed': 0,
                    'failed': 0,
                    'details': []
                }
            
            logger.info(f"Processing {len(attachments)} attachment(s)")
            
            # Initialize file service
            file_service = TaskFileService(self.settings)
            
            processed = 0
            failed = 0
            details = []
            
            for attachment in attachments:
                attachment_id = attachment.get('id')
                attachment_name = attachment.get('name', 'unknown')
                attachment_size = attachment.get('size', 0)
                
                try:
                    logger.info(f"Processing attachment: {attachment_name} ({attachment_size} bytes)")
                    
                    # Download attachment
                    download_result = self.graph_service.download_attachment(
                        message_id=message_id,
                        attachment_id=attachment_id
                    )
                    
                    if not download_result.get('success'):
                        logger.error(f"Failed to download attachment {attachment_name}")
                        failed += 1
                        details.append({
                            'filename': attachment_name,
                            'success': False,
                            'error': 'Download failed'
                        })
                        continue
                    
                    # Upload to SharePoint and sync to Weaviate
                    upload_result = file_service.upload_file(
                        task=task,
                        file_content=download_result['content'],
                        filename=download_result['filename'],
                        content_type=download_result['content_type'],
                        user=user
                    )
                    
                    if upload_result.get('success'):
                        processed += 1
                        details.append({
                            'filename': attachment_name,
                            'success': True,
                            'weaviate_synced': upload_result.get('weaviate_synced', False),
                            'sharepoint_url': upload_result.get('sharepoint_url', '')
                        })
                        logger.info(f"Successfully processed attachment: {attachment_name}")
                    else:
                        failed += 1
                        details.append({
                            'filename': attachment_name,
                            'success': False,
                            'error': upload_result.get('error', 'Upload failed')
                        })
                        logger.error(f"Failed to upload attachment {attachment_name}")
                        
                except Exception as e:
                    logger.error(f"Error processing attachment {attachment_name}: {str(e)}")
                    failed += 1
                    details.append({
                        'filename': attachment_name,
                        'success': False,
                        'error': str(e)
                    })
            
            logger.info(f"Attachment processing complete: {processed} processed, {failed} failed")
            
            return {
                'success': True,
                'processed': processed,
                'failed': failed,
                'details': details
            }
            
        except Exception as e:
            logger.error(f"Error processing attachments: {str(e)}")
            return {
                'success': False,
                'processed': 0,
                'failed': 0,
                'details': [],
                'error': str(e)
            }
    
    def create_task_from_mail(
        self,
        mail_subject: str,
        mail_body_markdown: str,
        item_id: str,
        sender_email: str,
        sender_name: str = ''
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new task from email content
        
        Args:
            mail_subject: Email subject (becomes task title)
            mail_body_markdown: Email body in Markdown
            item_id: UUID of the Item to attach task to
            sender_email: Email address of the sender
            sender_name: Full name of the sender (optional)
            
        Returns:
            Dictionary with task info, or None on failure
        """
        from main.models import Task, Item, User
        
        try:
            # Get the item
            item = Item.objects.get(id=item_id)
            
            # Try to find a user by email, create if not exists
            requester = None
            try:
                requester = User.objects.get(email=sender_email)
            except User.DoesNotExist:
                # Create new user with email as username
                logger.info(f"Creating new user for email {sender_email}")
                
                # Extract first and last name from sender name
                first_name = ''
                last_name = ''
                if sender_name:
                    name_parts = sender_name.strip().split()
                    if len(name_parts) >= 2:
                        first_name = name_parts[0]
                        last_name = ' '.join(name_parts[1:])
                    elif len(name_parts) == 1:
                        first_name = name_parts[0]
                
                requester = User.objects.create(
                    username=sender_email,
                    email=sender_email,
                    first_name=first_name,
                    last_name=last_name,
                    role='user',
                    is_active=True
                )
                logger.info(f"Created new user {requester.id} for email {sender_email} ({first_name} {last_name})")
            
            # Create the task
            task = Task.objects.create(
                title=mail_subject,
                description=mail_body_markdown,
                status='new',
                item=item,
                requester=requester,
                created_by=requester
            )
            
            logger.info(f"Created task {task.id} from email")
            
            return {
                'id': str(task.id),
                'title': task.title,
                'item_id': str(item.id),
                'item_title': item.title
            }
            
        except Item.DoesNotExist:
            logger.error(f"Item {item_id} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to create task: {str(e)}")
            return None
    
    def add_comment_to_task(
        self,
        task_id: str,
        comment_text: str,
        author_user=None,
        author_name: str = '',
        source: str = 'user'
    ) -> bool:
        """
        Add a comment to a task
        
        Args:
            task_id: UUID of the task
            comment_text: Text content of the comment (Markdown supported)
            author_user: User object for the author (optional)
            author_name: Name to display if author_user is None
            source: 'user' or 'agent'
            
        Returns:
            True if comment added successfully, False otherwise
        """
        from main.models import Task, TaskComment
        
        try:
            task = Task.objects.get(id=task_id)
            
            TaskComment.objects.create(
                task=task,
                author=author_user,
                author_name=author_name,
                text=comment_text,
                source=source
            )
            
            logger.info(f"Added {source} comment to task {task_id}")
            return True
            
        except Task.DoesNotExist:
            logger.error(f"Task {task_id} not found when adding comment")
            return False
        except Exception as e:
            logger.error(f"Failed to add comment to task {task_id}: {str(e)}")
            return False
    
    def send_confirmation_email(
        self,
        recipient_email: str,
        mail_subject: str,
        normalized_description: str,
        item_title: str
    ) -> Dict[str, Any]:
        """
        Send confirmation email to the sender
        
        Args:
            recipient_email: Email address of the original sender
            mail_subject: Original email subject
            normalized_description: The normalized task description
            item_title: Title of the Item the task was assigned to
            
        Returns:
            Dictionary with 'success' (bool), 'email_body_html' (str), and 'email_body_markdown' (str)
        """
        try:
            # Convert markdown description to HTML
            description_html = self.convert_markdown_to_html(normalized_description)
            
            # Build email body
            email_body_html = f"""
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #3b82f6, #2563eb); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px; }}
        .section {{ margin: 20px 0; padding: 15px; background: white; border-radius: 5px; border-left: 4px solid #3b82f6; }}
        .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; font-size: 12px; color: #6b7280; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Ihr Anliegen wurde erfolgreich erfasst</h1>
        </div>
        <div class="content">
            <p>Guten Tag,</p>
            
            <p>vielen Dank für Ihre E-Mail mit dem Betreff "<strong>{mail_subject}</strong>". 
            Ihr Anliegen wurde erfolgreich in unserem System erfasst und verarbeitet.</p>
            
            <div class="section">
                <h3>📋 Zugeordnet zu Item:</h3>
                <p><strong>{item_title}</strong></p>
            </div>
            
            <div class="section">
                <h3>📝 Aufbereitete Beschreibung:</h3>
                {description_html}
            </div>
            
            <p>Ihr Anliegen wurde als neue Aufgabe angelegt und wird entsprechend bearbeitet.</p>
            
            <div class="footer">
                <p>Diese E-Mail wurde automatisch von IdeaGraph generiert.</p>
                <p>&copy; IdeaGraph v1.0 | idea@angermeier.net</p>
            </div>
        </div>
    </div>
</body>
</html>
"""
            
            # Build markdown version for comment
            email_body_markdown = f"""# ✅ Ihr Anliegen wurde erfolgreich erfasst

Guten Tag,

vielen Dank für Ihre E-Mail mit dem Betreff "**{mail_subject}**". 
Ihr Anliegen wurde erfolgreich in unserem System erfasst und verarbeitet.

## 📋 Zugeordnet zu Item:
**{item_title}**

## 📝 Aufbereitete Beschreibung:
{normalized_description}

Ihr Anliegen wurde als neue Aufgabe angelegt und wird entsprechend bearbeitet.

---
Diese E-Mail wurde automatisch von IdeaGraph generiert.
© IdeaGraph v1.0 | idea@angermeier.net
"""
            
            # Send email
            result = self.graph_service.send_mail(
                to=[recipient_email],
                subject=f"Re: {mail_subject}",
                body=email_body_html
            )
            
            if result.get('success'):
                logger.info(f"Confirmation email sent to {recipient_email}")
                return {
                    'success': True,
                    'email_body_html': email_body_html,
                    'email_body_markdown': email_body_markdown
                }
            else:
                logger.error(f"Failed to send confirmation email to {recipient_email}")
                return {
                    'success': False,
                    'email_body_html': email_body_html,
                    'email_body_markdown': email_body_markdown
                }
                
        except GraphServiceError as e:
            logger.error(f"Graph service error sending confirmation: {e.message}")
            return {'success': False, 'email_body_html': '', 'email_body_markdown': ''}
        except Exception as e:
            logger.error(f"Unexpected error sending confirmation: {str(e)}")
            return {'success': False, 'email_body_html': '', 'email_body_markdown': ''}
    
    def process_mail(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single email message
        
        Args:
            message: Email message dict from Graph API
            
        Returns:
            Dictionary with processing result
        """
        try:
            # Extract message details
            message_id = message.get('id')
            subject = message.get('subject', '(No Subject)')
            body_data = message.get('body', {})
            body_html = body_data.get('content', '')
            sender = message.get('from', {}).get('emailAddress', {})
            sender_email = sender.get('address', '')
            sender_name = sender.get('name', '')
            
            logger.info(f"Processing mail: {subject} from {sender_name} <{sender_email}>")
            
            # Step 1: Convert HTML to Markdown
            body_markdown = self.convert_html_to_markdown(body_html)
            
            # Step 2: Find matching Item
            mail_content = f"Subject: {subject}\n\n{body_markdown}"
            matched_item = self.find_matching_item(mail_content)
            
            if not matched_item:
                logger.warning(f"No matching item found for mail: {subject}")
                return {
                    'success': False,
                    'message': 'No matching item found',
                    'mail_subject': subject
                }
            
            item_id = matched_item['id']
            item_title = matched_item['metadata'].get('title', 'Unknown')
            
            logger.info(f"Matched to item: {item_title} ({item_id})")
            
            # Step 3: Generate normalized description
            normalized_description = self.generate_normalized_description(
                mail_subject=subject,
                mail_body=body_markdown,
                item_context=matched_item
            )
            
            # Step 4: Create task
            task_info = self.create_task_from_mail(
                mail_subject=subject,
                mail_body_markdown=normalized_description,
                item_id=item_id,
                sender_email=sender_email,
                sender_name=sender_name
            )
            
            if not task_info:
                logger.error("Failed to create task")
                return {
                    'success': False,
                    'message': 'Failed to create task',
                    'mail_subject': subject
                }
            
            # Step 4a: Add comment with original mail content
            # Get the requester user for the comment
            from main.models import User
            try:
                requester = User.objects.get(email=sender_email)
                
                # Create original mail comment with sender as author
                original_mail_comment = f"""**Originale E-Mail von {sender_name}:**

**Betreff:** {subject}

{body_markdown}
"""
                self.add_comment_to_task(
                    task_id=task_info['id'],
                    comment_text=original_mail_comment,
                    author_user=requester,
                    author_name='',
                    source='user'
                )
                logger.info(f"Added original mail comment to task {task_info['id']}")
                
            except User.DoesNotExist:
                logger.warning(f"User {sender_email} not found when adding original mail comment")
            except Exception as e:
                logger.error(f"Error adding original mail comment: {str(e)}")
            
            # Step 5: Process attachments if present
            has_attachments = message.get('hasAttachments', False)
            attachments_result = {'processed': 0, 'failed': 0}
            
            if has_attachments:
                logger.info(f"Message has attachments, processing...")
                
                # Get the created task object
                from main.models import Task
                try:
                    task = Task.objects.get(id=task_info['id'])
                    
                    # Get requester user for file uploads
                    from main.models import User
                    requester = User.objects.get(email=sender_email)
                    
                    # Process attachments
                    attachments_result = self.process_attachments(
                        message_id=message_id,
                        task=task,
                        user=requester
                    )
                    
                    logger.info(f"Processed {attachments_result.get('processed', 0)} attachments, "
                              f"{attachments_result.get('failed', 0)} failed")
                    
                except Task.DoesNotExist:
                    logger.error(f"Task {task_info['id']} not found for attachment processing")
                except User.DoesNotExist:
                    logger.error(f"User {sender_email} not found for attachment processing")
                except Exception as e:
                    logger.error(f"Error during attachment processing: {str(e)}")
            
            # Step 6: Send confirmation email
            confirmation_result = self.send_confirmation_email(
                recipient_email=sender_email,
                mail_subject=subject,
                normalized_description=normalized_description,
                item_title=item_title
            )
            
            confirmation_sent = confirmation_result.get('success', False)
            
            # Step 6a: Add comment with confirmation email content (if sent)
            if confirmation_sent and confirmation_result.get('email_body_markdown'):
                try:
                    self.add_comment_to_task(
                        task_id=task_info['id'],
                        comment_text=confirmation_result['email_body_markdown'],
                        author_user=None,
                        author_name='AI Agent Bot',
                        source='agent'
                    )
                    logger.info(f"Added confirmation email comment to task {task_info['id']}")
                except Exception as e:
                    logger.error(f"Error adding confirmation email comment: {str(e)}")
            
            # Step 7: Mark message as read
            try:
                self.graph_service.mark_message_as_read(message_id)
            except GraphServiceError as e:
                logger.warning(f"Failed to mark message as read: {e.message}")
            
            # Step 8: Archive the message
            archived = False
            try:
                self.graph_service.move_message(message_id, destination_folder='archive')
                archived = True
                logger.info(f"Message {message_id} archived successfully")
            except GraphServiceError as e:
                logger.warning(f"Failed to archive message: {e.message}")
            
            return {
                'success': True,
                'message': 'Mail processed successfully',
                'mail_subject': subject,
                'task_id': task_info['id'],
                'item_id': item_id,
                'item_title': item_title,
                'confirmation_sent': confirmation_sent,
                'archived': archived,
                'attachments_processed': attachments_result.get('processed', 0),
                'attachments_failed': attachments_result.get('failed', 0)
            }
            
        except Exception as e:
            logger.error(f"Error processing mail: {str(e)}")
            return {
                'success': False,
                'message': f'Error processing mail: {str(e)}',
                'mail_subject': message.get('subject', '(Unknown)')
            }
    
    def process_mailbox(
        self,
        mailbox: Optional[str] = None,
        folder: str = 'inbox',
        max_messages: int = 10
    ) -> Dict[str, Any]:
        """
        Process all unread messages in a mailbox
        
        Args:
            mailbox: Email address of the mailbox (uses default if not provided)
            folder: Folder to process (default: 'inbox')
            max_messages: Maximum number of messages to process (default: 10)
            
        Returns:
            Dictionary with processing summary
        """
        logger.info(f"Starting mailbox processing for {mailbox or 'default mailbox'}")
        
        try:
            # Retrieve messages
            result = self.graph_service.get_mailbox_messages(
                mailbox=mailbox,
                folder=folder,
                top=max_messages,
                unread_only=True
            )
            
            if not result.get('success'):
                logger.error("Failed to retrieve messages")
                return {
                    'success': False,
                    'message': 'Failed to retrieve messages',
                    'processed': 0,
                    'failed': 0
                }
            
            messages = result.get('messages', [])
            logger.info(f"Found {len(messages)} unread messages")
            
            # Process each message
            processed = 0
            failed = 0
            results = []
            
            for message in messages:
                result = self.process_mail(message)
                results.append(result)
                
                if result.get('success'):
                    processed += 1
                else:
                    failed += 1
            
            logger.info(f"Mailbox processing complete: {processed} processed, {failed} failed")
            
            return {
                'success': True,
                'message': 'Mailbox processing complete',
                'total_messages': len(messages),
                'processed': processed,
                'failed': failed,
                'results': results
            }
            
        except GraphServiceError as e:
            logger.error(f"Graph service error: {e.message}")
            return {
                'success': False,
                'message': f'Graph service error: {e.message}',
                'processed': 0,
                'failed': 0
            }
        except Exception as e:
            logger.error(f"Unexpected error processing mailbox: {str(e)}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'processed': 0,
                'failed': 0
            }

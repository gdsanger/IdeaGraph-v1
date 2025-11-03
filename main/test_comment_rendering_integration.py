"""
Integration test to demonstrate HTML rendering and link auto-conversion in comments.
This test creates a sample comment with various HTML elements and URLs, then verifies
the rendering works as expected.
"""
from django.test import TestCase
from main.models import User, Item, Task, TaskComment
from main.templatetags.comment_extras import render_comment


class CommentRenderingIntegrationTestCase(TestCase):
    """Integration test for comment rendering feature"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(
            username='testuser',
            email='test@example.com',
            role='developer'
        )
        self.user.set_password('testpass123')
        self.user.save()
        
        self.item = Item.objects.create(
            title='Test Item',
            description='Test Description',
            created_by=self.user
        )
        
        self.task = Task.objects.create(
            title='Test Task',
            description='Test task description',
            item=self.item,
            created_by=self.user,
            status='new'
        )
    
    def test_comment_with_html_and_links(self):
        """Test rendering a comment with HTML and links as described in the issue"""
        # Create a comment similar to the one in the original issue
        comment_text = """
<h2>Software-Entwicklung Update</h2>

<p>Lieber <strong>Christian Angermeier</strong>,</p>

<p>wir haben die Anforderungen analysiert und folgende Links sind relevant:</p>

<ul>
    <li>Dokumentation: https://github.com/gdsanger/IdeaGraph-v1</li>
    <li>Issue Tracker: http://172.18.248.192:8080/tasks/95af6493-3bca-4544-98ab-7874868d94e0</li>
</ul>

<p>Bitte kontaktieren Sie uns unter <a href="mailto:ca@angermeier.net">ca@angermeier.net</a></p>

<p>Mit freundlichen Grüßen,<br>
<strong>ISARtec GmbH</strong><br>
Steinheilstraße 4 · 85737 Ismaning</p>
        """
        
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text=comment_text,
            source='user'
        )
        
        # Render the comment
        rendered = render_comment(comment.text)
        
        # Verify HTML elements are preserved
        self.assertIn('<h2>Software-Entwicklung Update</h2>', rendered)
        self.assertIn('<strong>Christian Angermeier</strong>', rendered)
        self.assertIn('<ul>', rendered)
        self.assertIn('<li>', rendered)
        self.assertIn('<br>', rendered)
        
        # Verify URLs are automatically linkified
        self.assertIn('<a href="https://github.com/gdsanger/IdeaGraph-v1"', rendered)
        self.assertIn('<a href="http://172.18.248.192:8080/tasks/95af6493-3bca-4544-98ab-7874868d94e0"', rendered)
        
        # Verify existing mailto link is preserved
        self.assertIn('mailto:ca@angermeier.net', rendered)
        
        print("\n" + "="*80)
        print("INTEGRATION TEST RESULT: Comment Rendering with HTML and Links")
        print("="*80)
        print("\nOriginal comment text:")
        print(comment_text)
        print("\n" + "-"*80)
        print("Rendered HTML output:")
        print(rendered)
        print("="*80 + "\n")
    
    def test_plain_text_with_urls(self):
        """Test that plain text URLs are automatically converted to links"""
        comment_text = """
Hallo Team,

bitte schaut euch folgende Ressourcen an:
- Projektseite: https://example.com/project
- API Docs: https://api.example.com/docs
- Support: support@example.com

Danke!
        """
        
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text=comment_text,
            source='user'
        )
        
        rendered = render_comment(comment.text)
        
        # Verify URLs are linkified
        self.assertIn('<a href="https://example.com/project"', rendered)
        self.assertIn('<a href="https://api.example.com/docs"', rendered)
        
        print("\n" + "="*80)
        print("INTEGRATION TEST RESULT: Plain Text URL Auto-Linking")
        print("="*80)
        print("\nOriginal comment text:")
        print(comment_text)
        print("\n" + "-"*80)
        print("Rendered HTML output:")
        print(rendered)
        print("="*80 + "\n")
    
    def test_mixed_formatting_with_code(self):
        """Test comment with code blocks and formatting"""
        comment_text = """
<h3>Bug Fix Details</h3>

<p>I've fixed the issue in the <code>render_comment</code> function.</p>

<p>Here's the code snippet:</p>

<pre>
def render_comment(text):
    cleaned = bleach.clean(text)
    return bleach.linkify(cleaned)
</pre>

<p>The fix is available at: https://github.com/example/repo/pull/123</p>
        """
        
        comment = TaskComment.objects.create(
            task=self.task,
            author=self.user,
            text=comment_text,
            source='agent'
        )
        
        rendered = render_comment(comment.text)
        
        # Verify code elements are preserved
        self.assertIn('<code>render_comment</code>', rendered)
        self.assertIn('<pre>', rendered)
        
        # Verify URL is linkified
        self.assertIn('<a href="https://github.com/example/repo/pull/123"', rendered)
        
        print("\n" + "="*80)
        print("INTEGRATION TEST RESULT: Mixed Formatting with Code")
        print("="*80)
        print("\nOriginal comment text:")
        print(comment_text)
        print("\n" + "-"*80)
        print("Rendered HTML output:")
        print(rendered)
        print("="*80 + "\n")

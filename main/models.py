import uuid
import random
from django.db import models
import uuid


class Tag(models.Model):
    """Tag model for categorizing and labeling items"""
    
    # Color palette for tag colors
    COLOR_PALETTE = [
        '#ef4444',  # Red
        '#f97316',  # Orange
        '#f59e0b',  # Amber
        '#eab308',  # Yellow
        '#84cc16',  # Lime
        '#22c55e',  # Green
        '#10b981',  # Emerald
        '#14b8a6',  # Teal
        '#06b6d4',  # Cyan
        '#0ea5e9',  # Sky
        '#3b82f6',  # Blue
        '#6366f1',  # Indigo
        '#8b5cf6',  # Violet
        '#a855f7',  # Purple
        '#d946ef',  # Fuchsia
        '#ec4899',  # Pink
        '#f43f5e',  # Rose
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default='#3b82f6')  # Hex color code
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Assign a random color from the palette if no color is set
        if not self.color or self.color == '#3b82f6':
            self.color = random.choice(self.COLOR_PALETTE)
        super().save(*args, **kwargs)
class Section(models.Model):
    """Section model for categorizing items by their fundamental type
    
    Sections classify items into domains such as:
    - Software projects
    - DIY/Home improvement items
    - Problems
    - Visions
    - Action items
    etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name


class Settings(models.Model):
    """
    Settings model to store system configuration and API keys.
    Only accessible to Admin users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # API Keys
    openai_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='OPENAI_API_KEY'
    )
    openai_org_id = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='OPENAI_ORG_ID',
        help_text='OpenAI Organisation ID'
    )
    
    # Graph API Credentials
    client_id = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='CLIENT_ID',
        help_text='GraphAPI Client ID'
    )
    client_secret = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='CLIENT_SECRET',
        help_text='GraphAPI Client Secret'
    )
    tenant_id = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='TENANT_ID',
        help_text='GraphAPI Tenant'
    )
    
    # GitHub Credentials
    github_token = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='GITHUB_TOKEN',
        help_text='GitHub PAT Key'
    )
    
    # ChromaDB Configuration
    chroma_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='CHROMA_API_KEY',
        help_text='ChromaDB Api Key (Cloud)'
    )
    chroma_database = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='CHROMA_DATABASE',
        help_text='ChromaDB Api Key (DATABASE)'
    )
    chroma_tenant = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='CHROMA_TENANT',
        help_text='ChromaDB Api Key (TENANT)'
    )
    
    # KiGate Configuration
    kigate_url = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='KiGateUrl'
    )
    kigate_token = models.CharField(
        max_length=255, 
        blank=True, 
        default='',
        verbose_name='KiGateToken'
    )
    
    # Additional Settings
    max_tags_per_idea = models.IntegerField(
        default=5,
        verbose_name='MAX_TAGS_PER_IDEA',
        help_text='Anzahl der Tags die bei Items durch die KI gesucht werden sollen'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Settings'
        verbose_name_plural = 'Settings'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Settings - {self.id}"

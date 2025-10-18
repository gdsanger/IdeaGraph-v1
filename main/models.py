from django.db import models
import uuid

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

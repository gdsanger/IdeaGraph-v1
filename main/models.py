from django.db import models
import uuid

# Create your models here.

class Section(models.Model):
    """
    Section entity for categorizing items.
    Items are divided into domains or sections to classify them in their basic type.
    Examples: Software project, DIY item, a problem, a vision, action required, etc.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Section'
        verbose_name_plural = 'Sections'
    
    def __str__(self):
        return self.name

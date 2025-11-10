"""
Support Embed Key Service

This service manages long-lived API keys for support embed widgets.
These keys can be embedded in static HTML and work for 1-2 years.
"""

import logging
import secrets
import hashlib
from datetime import timedelta
from typing import Optional, Dict, Any
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger('support_embed_key_service')


class SupportEmbedKeyService:
    """
    Service to manage long-lived embed API keys.
    
    These keys are designed to be embedded in static HTML and provide
    access to support widgets for extended periods (1-2 years).
    """
    
    KEY_LENGTH = 64  # Length of the generated key
    KEY_PREFIX_LENGTH = 8  # How many chars to store as prefix for display
    
    def generate_key(
        self,
        item_id: str,
        name: str,
        created_by_user,
        expires_in_days: int = 730  # Default: 2 years
    ) -> Dict[str, Any]:
        """
        Generate a new embed API key for an item.
        
        Args:
            item_id: UUID of the item
            name: Human-readable name for this key
            created_by_user: User who created the key
            expires_in_days: Number of days until expiry (default: 730 = 2 years)
        
        Returns:
            {
                'success': bool,
                'key': str (the actual key - only returned once!),
                'key_id': str (UUID of the key record),
                'key_prefix': str (first 8 chars for identification),
                'expires_at': datetime,
                'error': str (if failed)
            }
        """
        try:
            from main.models import Item, SupportEmbedKey
            
            # Verify item exists
            try:
                item = Item.objects.get(id=item_id)
            except Item.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Item not found'
                }
            
            # Generate random key
            raw_key = secrets.token_urlsafe(self.KEY_LENGTH)
            
            # Hash the key for storage
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            
            # Get prefix for display
            key_prefix = raw_key[:self.KEY_PREFIX_LENGTH]
            
            # Calculate expiry
            expires_at = timezone.now() + timedelta(days=expires_in_days)
            
            # Create key record
            with transaction.atomic():
                embed_key = SupportEmbedKey.objects.create(
                    item=item,
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    name=name,
                    created_by=created_by_user,
                    expires_at=expires_at
                )
            
            logger.info(f"Generated embed key {embed_key.id} for item {item_id}")
            
            return {
                'success': True,
                'key': raw_key,  # Only returned once!
                'key_id': str(embed_key.id),
                'key_prefix': key_prefix,
                'expires_at': expires_at
            }
        
        except Exception as e:
            logger.error(f"Error generating embed key: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_key(self, raw_key: str) -> Dict[str, Any]:
        """
        Verify an embed API key and return associated item info.
        
        Args:
            raw_key: The raw API key to verify
        
        Returns:
            {
                'valid': bool,
                'item_id': str (if valid),
                'key_id': str (if valid),
                'error': str (if invalid)
            }
        """
        try:
            from main.models import SupportEmbedKey
            
            # Hash the provided key
            key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            
            # Look up the key
            try:
                embed_key = SupportEmbedKey.objects.select_related('item').get(
                    key_hash=key_hash
                )
            except SupportEmbedKey.DoesNotExist:
                logger.warning("Invalid embed key provided")
                return {
                    'valid': False,
                    'error': 'Invalid key'
                }
            
            # Check if key is still valid
            if not embed_key.is_valid():
                if embed_key.revoked_at:
                    logger.warning(f"Revoked embed key {embed_key.id} used")
                    return {
                        'valid': False,
                        'error': 'Key revoked'
                    }
                else:
                    logger.warning(f"Expired embed key {embed_key.id} used")
                    return {
                        'valid': False,
                        'error': 'Key expired'
                    }
            
            # Update usage tracking
            embed_key.usage_count += 1
            embed_key.last_used_at = timezone.now()
            embed_key.save(update_fields=['usage_count', 'last_used_at'])
            
            logger.info(f"Embed key {embed_key.id} verified for item {embed_key.item.id}")
            
            return {
                'valid': True,
                'item_id': str(embed_key.item.id),
                'key_id': str(embed_key.id)
            }
        
        except Exception as e:
            logger.error(f"Error verifying embed key: {str(e)}", exc_info=True)
            return {
                'valid': False,
                'error': 'Verification failed'
            }
    
    def revoke_key(self, key_id: str) -> Dict[str, Any]:
        """
        Revoke an embed API key.
        
        Args:
            key_id: UUID of the key to revoke
        
        Returns:
            {
                'success': bool,
                'error': str (if failed)
            }
        """
        try:
            from main.models import SupportEmbedKey
            
            try:
                embed_key = SupportEmbedKey.objects.get(id=key_id)
            except SupportEmbedKey.DoesNotExist:
                return {
                    'success': False,
                    'error': 'Key not found'
                }
            
            embed_key.revoke()
            logger.info(f"Revoked embed key {key_id}")
            
            return {
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Error revoking embed key: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_keys(self, item_id: str, include_revoked: bool = False) -> Dict[str, Any]:
        """
        List all embed keys for an item.
        
        Args:
            item_id: UUID of the item
            include_revoked: Whether to include revoked keys
        
        Returns:
            {
                'success': bool,
                'keys': list of key info dicts,
                'error': str (if failed)
            }
        """
        try:
            from main.models import SupportEmbedKey
            
            queryset = SupportEmbedKey.objects.filter(item_id=item_id)
            
            if not include_revoked:
                queryset = queryset.filter(revoked_at__isnull=True)
            
            keys = []
            for key in queryset:
                keys.append({
                    'id': str(key.id),
                    'name': key.name,
                    'key_prefix': key.key_prefix,
                    'created_at': key.created_at.isoformat(),
                    'expires_at': key.expires_at.isoformat(),
                    'revoked_at': key.revoked_at.isoformat() if key.revoked_at else None,
                    'last_used_at': key.last_used_at.isoformat() if key.last_used_at else None,
                    'usage_count': key.usage_count,
                    'is_valid': key.is_valid()
                })
            
            return {
                'success': True,
                'keys': keys
            }
        
        except Exception as e:
            logger.error(f"Error listing embed keys: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

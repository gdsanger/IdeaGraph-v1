"""
Support Auth Service

This service handles authentication for embeddable support endpoints
using JWT tokens or HMAC signatures.
"""

import logging
import time
import hmac
import hashlib
from typing import Optional, Dict, Any
import jwt
from django.conf import settings

logger = logging.getLogger('support_auth_service')


class SupportAuthService:
    """
    Service to authenticate embed requests
    
    Supports two authentication methods:
    1. JWT tokens (recommended) - short-lived tokens with aud='embed'
    2. HMAC signatures - timestamp-based signatures with replay protection
    """
    
    JWT_ALGORITHM = 'HS256'
    JWT_AUDIENCE = 'embed'
    JWT_MAX_AGE_SECONDS = 1800  # 30 minutes
    
    HMAC_ALGORITHM = 'sha256'
    HMAC_MAX_AGE_SECONDS = 300  # 5 minutes
    
    def __init__(self):
        """Initialize SupportAuthService"""
        self.jwt_secret = settings.JWT_SECRET
    
    def verify_jwt(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token
        
        Args:
            token: JWT token string
        
        Returns:
            {
                'valid': bool,
                'item_id': str (if valid),
                'error': str (if invalid)
            }
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.JWT_ALGORITHM],
                audience=self.JWT_AUDIENCE
            )
            
            # Extract item_id from payload
            item_id = payload.get('item_id')
            if not item_id:
                return {
                    'valid': False,
                    'error': 'Missing item_id in token'
                }
            
            logger.info(f"JWT token verified for item {item_id}")
            return {
                'valid': True,
                'item_id': item_id,
                'payload': payload
            }
        
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return {
                'valid': False,
                'error': 'Token expired'
            }
        except jwt.InvalidAudienceError:
            logger.warning("JWT token has invalid audience")
            return {
                'valid': False,
                'error': 'Invalid token audience'
            }
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return {
                'valid': False,
                'error': 'Invalid token'
            }
    
    def verify_hmac(
        self,
        item_id: str,
        signature: str,
        timestamp: str,
        secret: str
    ) -> Dict[str, Any]:
        """
        Verify HMAC signature
        
        Args:
            item_id: UUID of the item
            signature: HMAC signature (hex string)
            timestamp: Unix timestamp string
            secret: Shared secret key
        
        Returns:
            {
                'valid': bool,
                'item_id': str (if valid),
                'error': str (if invalid)
            }
        """
        try:
            # Parse timestamp
            ts = int(timestamp)
            current_ts = int(time.time())
            
            # Check if timestamp is too old (replay protection)
            if current_ts - ts > self.HMAC_MAX_AGE_SECONDS:
                logger.warning(f"HMAC timestamp too old: {ts} vs {current_ts}")
                return {
                    'valid': False,
                    'error': 'Signature expired'
                }
            
            # Check if timestamp is in the future (clock skew)
            if ts > current_ts + 60:  # Allow 60 seconds clock skew
                logger.warning(f"HMAC timestamp in future: {ts} vs {current_ts}")
                return {
                    'valid': False,
                    'error': 'Invalid timestamp'
                }
            
            # Compute expected signature
            message = f"{item_id}|{timestamp}"
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures (constant-time comparison)
            if not hmac.compare_digest(signature, expected_signature):
                logger.warning("HMAC signature mismatch")
                return {
                    'valid': False,
                    'error': 'Invalid signature'
                }
            
            logger.info(f"HMAC signature verified for item {item_id}")
            return {
                'valid': True,
                'item_id': item_id
            }
        
        except ValueError as e:
            logger.warning(f"Invalid timestamp format: {str(e)}")
            return {
                'valid': False,
                'error': 'Invalid timestamp'
            }
        except Exception as e:
            logger.error(f"HMAC verification error: {str(e)}", exc_info=True)
            return {
                'valid': False,
                'error': 'Verification failed'
            }
    
    def generate_jwt(self, item_id: str, expires_in: int = JWT_MAX_AGE_SECONDS) -> str:
        """
        Generate JWT token for testing/debugging
        
        Args:
            item_id: UUID of the item
            expires_in: Expiration time in seconds
        
        Returns:
            JWT token string
        """
        payload = {
            'item_id': item_id,
            'aud': self.JWT_AUDIENCE,
            'exp': int(time.time()) + expires_in,
            'iat': int(time.time())
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.JWT_ALGORITHM)
        return token
    
    def generate_hmac(self, item_id: str, secret: str) -> Dict[str, str]:
        """
        Generate HMAC signature for testing/debugging
        
        Args:
            item_id: UUID of the item
            secret: Shared secret key
        
        Returns:
            {
                'signature': str,
                'timestamp': str
            }
        """
        timestamp = str(int(time.time()))
        message = f"{item_id}|{timestamp}"
        signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'signature': signature,
            'timestamp': timestamp
        }

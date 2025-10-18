"""
Authentication utilities for JWT token generation and validation.
"""
import jwt
import datetime
from django.conf import settings


# JWT Configuration
JWT_SECRET = getattr(settings, 'JWT_SECRET', settings.SECRET_KEY)
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24


def generate_jwt_token(user):
    """
    Generate a JWT token for a user.
    
    Args:
        user: User model instance
        
    Returns:
        str: JWT token
    """
    payload = {
        'user_id': str(user.id),
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.datetime.utcnow(),
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_jwt_token(token):
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Decoded payload if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def validate_password(password):
    """
    Validate password against policy requirements.
    
    Args:
        password: Raw password string
        
    Returns:
        tuple: (is_valid, error_message)
    """
    min_length = getattr(settings, 'PASSWORD_MIN_LENGTH', 8)
    require_special = getattr(settings, 'PASSWORD_REQUIRE_SPECIAL', True)
    require_number = getattr(settings, 'PASSWORD_REQUIRE_NUMBER', True)
    
    if len(password) < min_length:
        return False, f'Password must be at least {min_length} characters long'
    
    if require_number and not any(char.isdigit() for char in password):
        return False, 'Password must contain at least one number'
    
    if require_special and not any(char in '!@#$%^&*()_+-=[]{}|;:,.<>?' for char in password):
        return False, 'Password must contain at least one special character'
    
    return True, ''

"""
Throttling classes for Actions API
"""
from rest_framework.throttling import UserRateThrottle


class ActionsAPIRateThrottle(UserRateThrottle):
    """
    Rate throttle for Actions API
    100 requests per hour per user
    """
    scope = 'actions_api'


class ActionsAPIBurstRateThrottle(UserRateThrottle):
    """
    Burst rate throttle for Actions API
    10 requests per minute per user
    """
    scope = 'actions_api_burst'

"""
Test for COOP (Cross-Origin-Opener-Policy) settings fix
"""
from django.test import TestCase
from django.conf import settings


class COOPSettingsTest(TestCase):
    """Test COOP settings configuration"""
    
    def test_coop_disabled_for_development(self):
        """
        Test that SECURE_CROSS_ORIGIN_OPENER_POLICY is set to None
        to avoid COOP header errors in development environments
        """
        self.assertIsNone(
            settings.SECURE_CROSS_ORIGIN_OPENER_POLICY,
            "SECURE_CROSS_ORIGIN_OPENER_POLICY should be None for development"
        )
    
    def test_no_coop_header_in_response(self):
        """
        Test that no COOP header is sent in responses when setting is None
        """
        response = self.client.get('/')
        self.assertNotIn(
            'Cross-Origin-Opener-Policy',
            response.headers,
            "COOP header should not be present when setting is None"
        )

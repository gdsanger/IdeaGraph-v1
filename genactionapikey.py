from main.models import User, ApiKey

user = User.objects.get(username='admin')
api_key = ApiKey.generate_key(
    user=user,
    name='My API Key',
    expires_at=None  # Optional expiration
)

# Save the key value - it won't be shown again
print(f"API Key: {api_key.key}")

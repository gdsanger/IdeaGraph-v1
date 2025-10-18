# User Management System Documentation

## Overview

The IdeaGraph user management system provides comprehensive user authentication and authorization functionality with a modern web interface and RESTful API.

## Features

### 🔐 Security
- **Password Hashing**: All passwords are hashed using bcrypt with salt
- **JWT Authentication**: Secure token-based authentication for API access
- **Role-Based Access Control**: Three role levels (Admin, User, Viewer)
- **Password Policy**: Enforces minimum 8 characters with numbers and special characters
- **Account Status**: Active/Inactive flag for user access control

### 👥 User Roles

| Role | Description | Permissions |
|------|-------------|-------------|
| **Admin** | Full system access | User CRUD, Settings management, Full system access |
| **User** | Standard user | Create/edit ideas, tasks, and own profile |
| **Viewer** | Read-only access | View ideas and tasks only |

### 🎨 User Interface

The UI is built with **Bootstrap 5** (dark theme) and includes:

1. **User List** (`/admin/users/`)
   - Paginated table view
   - Search by username or email
   - Filter by role and status
   - Bulk actions support

2. **Create User** (`/admin/users/create/`)
   - Validated form with client-side and server-side validation
   - Password strength indicator
   - Role selection
   - Active/Inactive toggle

3. **Edit User** (`/admin/users/{id}/edit/`)
   - Update email, role, status
   - Optional password change
   - AI classification field

4. **User Detail** (`/admin/users/{id}/`)
   - Complete user information card
   - Last login timestamp
   - Creation date
   - Role badges

5. **Delete User** (`/admin/users/{id}/delete/`)
   - Confirmation modal
   - Prevents self-deletion

## API Documentation

### Authentication

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "testuser",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid",
    "username": "testuser",
    "email": "test@example.com",
    "role": "user",
    "is_active": true
  }
}
```

#### Logout
```http
POST /api/auth/logout
```

### User Management

All user management endpoints require authentication. Admin role required for most operations.

#### List Users (Admin only)
```http
GET /api/users?page=1&per_page=10
Authorization: Bearer {jwt_token}
```

#### Get User Details
```http
GET /api/users/{user_id}
Authorization: Bearer {jwt_token}
```

**Note**: Regular users can only view their own profile. Admins can view any user.

#### Create User (Admin only)
```http
POST /api/users/create
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "role": "user",
  "is_active": true,
  "ai_classification": "AI-Assistant"
}
```

#### Update User
```http
PUT /api/users/{user_id}/update
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "email": "updated@example.com",
  "role": "admin",
  "is_active": true,
  "password": "NewPass123!"  // optional
}
```

**Note**: Regular users can only update their own email and password.

#### Delete User (Admin only)
```http
DELETE /api/users/{user_id}/delete
Authorization: Bearer {jwt_token}
```

## Database Schema

### User Model

```python
class User(models.Model):
    id = UUIDField(primary_key=True)           # Unique identifier
    username = CharField(unique=True)          # Unique username
    email = EmailField(unique=True)            # Email address
    password_hash = CharField()                # Bcrypt hashed password
    role = CharField(choices=['admin', 'user', 'viewer'])
    is_active = BooleanField(default=True)     # Account status
    created_at = DateTimeField(auto_now_add=True)
    last_login = DateTimeField(null=True)      # Last login timestamp
    ai_classification = CharField(blank=True)  # Optional AI notes
```

## Configuration

### Django Settings (`ideagraph/settings.py`)

```python
# Authentication Configuration
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIRE_SPECIAL = True
PASSWORD_REQUIRE_NUMBER = True
JWT_SECRET = SECRET_KEY  # Use separate secret in production
JWT_EXPIRATION_HOURS = 24
```

### YAML Configuration (`authentication_config.yaml`)

```yaml
authentication:
  provider: internal
  jwt:
    expiration_hours: 24
    algorithm: HS256
  password_policy:
    min_length: 8
    require_special: true
    require_number: true
```

## Installation

1. **Install Dependencies**
   ```bash
   pip install bcrypt>=4.0.0 PyJWT>=2.8.0
   ```

2. **Run Migrations**
   ```bash
   python manage.py migrate
   ```

3. **Create Admin User**
   ```bash
   python manage.py shell
   >>> from main.models import User as AppUser
   >>> admin = AppUser(username='admin', email='admin@example.com', role='admin')
   >>> admin.set_password('AdminPass123!')
   >>> admin.save()
   ```

## Usage Examples

### Creating a User via UI

1. Navigate to `/admin/users/`
2. Click "Create New User"
3. Fill in the form:
   - Username: `john_doe`
   - Email: `john@example.com`
   - Password: `SecurePass123!`
   - Role: `User`
   - Active: ✓
4. Click "Create User"

### Creating a User via API

```bash
# 1. Login to get JWT token
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"AdminPass123!"}' \
  | jq -r '.token')

# 2. Create new user
curl -X POST http://localhost:8000/api/users/create \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "jane_doe",
    "email": "jane@example.com",
    "password": "SecurePass123!",
    "role": "user",
    "is_active": true
  }'
```

### Authenticating as a User

```python
from main.models import User as AppUser

# Find user
user = AppUser.objects.get(username='john_doe')

# Verify password
if user.check_password('SecurePass123!'):
    # Update last login
    user.update_last_login()
    print(f"Welcome {user.username}!")
else:
    print("Invalid password")
```

## Security Best Practices

1. **Password Storage**
   - Never store plain-text passwords
   - Use bcrypt with adequate rounds (default: 12)
   - Enforce password complexity requirements

2. **JWT Tokens**
   - Set reasonable expiration times (24 hours)
   - Use HTTPS in production
   - Store tokens securely on client side

3. **Access Control**
   - Always validate user roles before granting access
   - Use Django's `@staff_member_required` decorator for admin views
   - Implement proper JWT validation in API endpoints

4. **Error Handling**
   - Don't expose stack traces to users
   - Log errors server-side
   - Return generic error messages to clients

## Testing

Run the user management tests:

```bash
# All user tests
python manage.py test main.tests.UserModelTest main.tests.UserAPITest main.tests.UserViewTest

# Specific test
python manage.py test main.tests.UserModelTest.test_password_hashing
```

## Troubleshooting

### Common Issues

1. **"User not found" error**
   - Verify user exists in database
   - Check if user is active
   - Ensure correct username is used

2. **"Invalid credentials" error**
   - Verify password is correct
   - Check if account is active
   - Ensure bcrypt is properly installed

3. **"Admin access required" error**
   - Verify user has admin role
   - Check JWT token is valid
   - Ensure Authorization header is correctly formatted

4. **Password validation fails**
   - Must be at least 8 characters
   - Must include at least one number
   - Must include at least one special character

## Future Enhancements

- [ ] Email verification
- [ ] Password reset via email
- [ ] Two-factor authentication (2FA)
- [ ] OAuth integration (Google, GitHub)
- [ ] User activity logging
- [ ] Session management
- [ ] Account lockout after failed attempts
- [ ] Password history
- [ ] User groups and permissions

## Support

For issues or questions:
- Open an issue on GitHub
- Check the main IdeaGraph documentation
- Review the code comments in `main/models.py`, `main/views.py`, and `main/api_views.py`

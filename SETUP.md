# IdeaGraph Django Application Setup

This document provides quick setup instructions for the IdeaGraph Django/HTMX application.

## Requirements

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/gdsanger/IdeaGraph-v1.git
   cd IdeaGraph-v1
   ```
 
2. **Create and activate a virtual environment:**
   ```bash
   # Linux/Mac
   python -m venv .venv
   source .venv/bin/activate
   
   # Windows
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser (optional):**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

7. **Access the application:**
   Open your browser and navigate to: http://localhost:8000

## Project Structure

```
IdeaGraph-v1/
├── ideagraph/          # Django project settings
│   ├── settings.py     # Main configuration
│   ├── urls.py         # URL routing
│   └── wsgi.py         # WSGI application
├── main/               # Main Django app
│   ├── templates/      # HTML templates
│   │   └── main/
│   │       ├── base.html    # Base template with navbar/footer
│   │       └── home.html    # Homepage
│   ├── views.py        # View functions
│   └── urls.py         # App URL patterns
├── static/             # Static files (CSS, JS, images)
├── manage.py           # Django management script
└── requirements.txt    # Python dependencies
```

## Features

- **Dark Mode Interface**: Bootstrap 5 with custom autumn color scheme
- **Responsive Design**: Mobile-friendly navigation and layouts
- **HTMX Integration**: Ready for dynamic content updates
- **Modern UI**: Animated components with smooth transitions
- **Bootstrap Icons**: Visual elements throughout the interface

## Customization

### Color Scheme

The autumn color palette is defined in `main/templates/main/base.html`:
- Primary: `#d97706` (Burnt orange)
- Secondary: `#92400e` (Dark brown)
- Accent: `#f59e0b` (Golden yellow)
- Light: `#fbbf24` (Light amber)

### Navigation Menu

Edit the navbar in `main/templates/main/base.html` to add or modify menu items.

### Adding New Pages

1. Create a new view in `main/views.py`
2. Add a URL pattern in `main/urls.py`
3. Create a template in `main/templates/main/`

## Development Commands

```bash
# Check for issues
python manage.py check

# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Collect static files (for production)
python manage.py collectstatic

# Run tests
python manage.py test
```

## License

- **Software**: MIT License
- **Methodology & Documentation**: CC BY-NC-SA 4.0

See [LICENSE_OVERVIEW.md](LICENSE_OVERVIEW.md) for details.

## Author

Christian Angermeier  
Email: ca@angermeier.net

---

For more information, see the main [README.md](README.md).

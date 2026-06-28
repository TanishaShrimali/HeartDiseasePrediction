# CardioGuard Deployment

Use this checklist after the app works locally.

## Render Setup

1. Push the project to GitHub.
2. In Render, create a new Web Service from the repository.
3. Use these settings:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn wsgi:app
```

4. Add these environment variables:

```text
FLASK_ENV=production
PYTHON_VERSION=3.11.11
HOST=0.0.0.0
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<choose-a-password>
```

5. Deploy and open the generated Render URL.

## Demo Notes

- Patient accounts can be registered from the app.
- Doctor accounts can be created from the Admin dashboard.
- The configured `ADMIN_PASSWORD` is applied to the configured `ADMIN_USERNAME` at startup.
- SQLite data is fine for a presentation demo, but hosted demo data can reset if the service is rebuilt without persistent storage.
- PDF report download works from the hosted app after a prediction is saved.

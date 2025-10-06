# backend/config/__init__.py
# Это гарантирует, что приложение Celery всегда импортируется
# при запуске Django, чтобы shared_task использовал это приложение.
from .celery import app as celery_app

__all__ = ('celery_app',)
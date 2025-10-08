# backend/reviews/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Пока ViewSet для отзывов не создан, создаем пустой urlpatterns
# TODO: Добавить ViewSet для отзывов и зарегистрировать его здесь

urlpatterns = [
    # Временно пустой список URL
    # Когда будет создан ReviewViewSet, добавить:
    # path('', include(router.urls)),
]
# backend/orders/apps.py
from django.apps import AppConfig

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'
    verbose_name = 'Заказы'


# backend/reviews/apps.py
from django.apps import AppConfig

class ReviewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reviews'
    verbose_name = 'Отзывы'


# backend/promotions/apps.py
from django.apps import AppConfig

class PromotionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'promotions'
    verbose_name = 'Акции'


# backend/wishlist/apps.py
from django.apps import AppConfig

class WishlistConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wishlist'
    verbose_name = 'Избранное'
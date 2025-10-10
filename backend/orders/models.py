from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import timedelta
from products.models import Product


class Cart(models.Model):
    """Корзина покупателя"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Пользователь'
    )
    session_key = models.CharField(
        'Ключ сессии',
        max_length=40,
        null=True,
        blank=True,
        db_index=True
    )
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
    
    def __str__(self):
        if self.user:
            return f"Корзина {self.user.username}"
        return f"Корзина (сессия {self.session_key})"
    
    def get_total(self):
        """Общая сумма корзины"""
        return sum(item.get_total_price() for item in self.items.all())
    
    def get_items_count(self):
        """Общее количество товаров"""
        return sum(item.quantity for item in self.items.all())
    
    def clear(self):
        """Очистить корзину"""
        self.items.all().delete()


class CartItem(models.Model):
    """Товар в корзине"""
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    quantity = models.PositiveIntegerField(
        'Количество',
        default=1,
        validators=[MinValueValidator(1)]
    )
    reserved_until = models.DateTimeField(
        'Зарезервировано до',
        null=True,
        blank=True
    )
    created_at = models.DateTimeField('Добавлен', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Товар в корзине'
        verbose_name_plural = 'Товары в корзине'
        unique_together = ['cart', 'product']
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
    
    def get_total_price(self):
        """Сумма за позицию"""
        if not self.product or not self.product.price:
            return 0
        return self.product.price * self.quantity
    
    def reserve(self, hours=24):
        """Зарезервировать товар"""
        if self.product.stock_status == 'in_stock':
            self.reserved_until = timezone.now() + timedelta(hours=hours)
            self.save(update_fields=['reserved_until'])
    
    def is_reserved(self):
        """Проверка, зарезервирован ли товар"""
        if not self.reserved_until:
            return False
        return timezone.now() < self.reserved_until
    
    def save(self, *args, **kwargs):
        # Автоматическое резервирование при добавлении товара "в наличии"
        if not self.pk and self.product.stock_status == 'in_stock':
            self.reserved_until = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)


class Order(models.Model):
    """Заказ"""
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('made_to_order', 'Под заказ (в производстве)'),
        ('cancelled', 'Отменен'),
    ]
    
    DELIVERY_CHOICES = [
        ('courier_moscow', 'Курьер по Москве'),
        ('cdek_pickup', 'СДЭК до пункта выдачи'),
        ('russian_post', 'Почта России'),
        ('pickup', 'Самовывоз'),
    ]
    
    # Связи
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Пользователь'
    )
    
    # Контактные данные
    name = models.CharField('Имя', max_length=100)
    email = models.EmailField('Email')
    phone = models.CharField('Телефон', max_length=20)
    
    # Доставка
    delivery_method = models.CharField(
        'Способ доставки',
        max_length=20,
        choices=DELIVERY_CHOICES
    )
    delivery_address = models.TextField('Адрес доставки', blank=True)
    delivery_cost = models.DecimalField(
        'Стоимость доставки',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Стоимость
    total_amount = models.DecimalField(
        'Сумма заказа',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    
    # Статус
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Дополнительно
    comment = models.TextField('Комментарий', blank=True)
    track_number = models.CharField('Трек-номер', max_length=100, blank=True)
    
    # Временные метки
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    paid_at = models.DateTimeField('Оплачен', null=True, blank=True)
    shipped_at = models.DateTimeField('Отправлен', null=True, blank=True)
    delivered_at = models.DateTimeField('Доставлен', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"Заказ #{self.id} от {self.created_at.strftime('%d.%m.%Y')}"
    
    def get_final_amount(self):
        """Итоговая сумма с учетом доставки и скидки"""
        total = self.total_amount or 0
        delivery = self.delivery_cost or 0
        discount = self.discount_amount or 0
        return total + delivery - discount
    
    def get_items_total(self):
        """Сумма всех товаров"""
        return sum(item.get_total_price() for item in self.items.all())
    
    def mark_as_paid(self):
        """Отметить как оплаченный"""
        self.status = 'paid'
        self.paid_at = timezone.now()
        self.save(update_fields=['status', 'paid_at'])
    
    def mark_as_shipped(self, track_number=''):
        """Отметить как отправленный"""
        self.status = 'shipped'
        self.shipped_at = timezone.now()
        if track_number:
            self.track_number = track_number
        self.save(update_fields=['status', 'shipped_at', 'track_number'])
    
    def mark_as_delivered(self):
        """Отметить как доставленный"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def cancel(self):
        """Отменить заказ"""
        self.status = 'cancelled'
        self.save(update_fields=['status'])


class OrderItem(models.Model):
    """Товар в заказе"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        verbose_name='Товар'
    )
    quantity = models.PositiveIntegerField(
        'Количество',
        validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        'Цена на момент заказа',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    class Meta:
        verbose_name = 'Товар в заказе'
        verbose_name_plural = 'Товары в заказе'
    
    def __str__(self):
        return f"{self.product.name} x{self.quantity}"
    
    def get_total_price(self):
        """Сумма за позицию"""
        if self.price is None or self.quantity is None:
            return 0
        return self.price * self.quantity


class Payment(models.Model):
    """Платеж (интеграция с ЮKassa)"""
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('waiting_for_capture', 'Ожидает подтверждения'),
        ('succeeded', 'Успешно'),
        ('canceled', 'Отменен'),
        ('refunded', 'Возвращен'),
    ]
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Заказ'
    )
    payment_id = models.CharField(
        'ID платежа (ЮKassa)',
        max_length=100,
        unique=True,
        db_index=True
    )
    idempotency_key = models.CharField(
        'Ключ идемпотентности',
        max_length=100,
        unique=True
    )
    amount = models.DecimalField(
        'Сумма',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField('Валюта', max_length=3, default='RUB')
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    metadata = models.JSONField('Метаданные', default=dict, blank=True)
    
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Платеж {self.payment_id} - {self.get_status_display()}"
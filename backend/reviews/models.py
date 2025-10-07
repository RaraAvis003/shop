from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from products.models import Product


class Review(models.Model):
    """Отзыв на товар"""
    
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Товар'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Пользователь'
    )
    
    # Оценка и текст
    rating = models.IntegerField(
        'Оценка',
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField('Заголовок', max_length=200)
    text = models.TextField('Текст отзыва')
    
    # Достоинства и недостатки
    pros = models.TextField('Достоинства', blank=True)
    cons = models.TextField('Недостатки', blank=True)
    
    # Модерация и статус
    is_approved = models.BooleanField('Одобрен', default=False)
    is_verified_buyer = models.BooleanField('Проверенная покупка', default=False)
    
    # Метрики
    helpful_count = models.IntegerField('Полезно', default=0)
    
    # Временные метки
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        unique_together = ['product', 'user']
        indexes = [
            models.Index(fields=['product', 'is_approved']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['-helpful_count']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.rating}★)"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Обновить средний рейтинг товара при одобрении
        if self.is_approved:
            self.product.update_rating()
    
    def increment_helpful(self):
        """Увеличить счетчик 'Полезно'"""
        self.helpful_count += 1
        self.save(update_fields=['helpful_count'])
    
    def decrement_helpful(self):
        """Уменьшить счетчик 'Полезно'"""
        if self.helpful_count > 0:
            self.helpful_count -= 1
            self.save(update_fields=['helpful_count'])


class ReviewImage(models.Model):
    """Изображение к отзыву"""
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Отзыв'
    )
    image = models.ImageField('Изображение', upload_to='reviews/')
    order = models.IntegerField('Порядок', default=0)
    created_at = models.DateTimeField('Добавлено', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Изображение отзыва'
        verbose_name_plural = 'Изображения отзывов'
        ordering = ['order']
    
    def __str__(self):
        return f"Фото к отзыву #{self.review.id}"


class ReviewHelpful(models.Model):
    """Отметка 'Полезно' для отзыва"""
    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='helpful_marks',
        verbose_name='Отзыв'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    created_at = models.DateTimeField('Отмечено', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Отметка "Полезно"'
        verbose_name_plural = 'Отметки "Полезно"'
        unique_together = ['review', 'user']
    
    def __str__(self):
        return f"{self.user.username} → Отзыв #{self.review.id}"
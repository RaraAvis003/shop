# backend/products/models.py
from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    """Категория товаров с поддержкой древовидной структуры"""
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('URL', max_length=200, unique=True, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская категория'
    )
    icon_name = models.CharField('Имя иконки', max_length=100, blank=True)
    order = models.IntegerField('Порядок сортировки', default=0)
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """Основная модель товара (нож/топор)"""
    
    STOCK_STATUS_CHOICES = [
        ('in_stock', 'В наличии'),
        ('made_to_order', 'Под заказ'),
        ('out_of_stock', 'Нет в наличии'),
    ]
    
    # Основная информация
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('URL', max_length=200, unique=True, blank=True)
    description = models.TextField('Описание', blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Категория'
    )
    price = models.DecimalField(
        'Цена',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # Характеристики
    blade_length = models.IntegerField(
        'Длина клинка (мм)',
        null=True,
        blank=True,
        validators=[MinValueValidator(1)]
    )
    total_length = models.IntegerField(
        'Общая длина (мм)',
        null=True,
        blank=True,
        validators=[MinValueValidator(1)]
    )
    weight = models.IntegerField(
        'Вес (г)',
        null=True,
        blank=True,
        validators=[MinValueValidator(1)]
    )
    blade_thickness = models.DecimalField(
        'Толщина клинка (мм)',
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.1)]
    )
    blade_material = models.CharField('Материал клинка', max_length=100, blank=True)
    handle_material = models.CharField('Материал рукояти', max_length=100, blank=True)
    hardness = models.CharField('Твердость HRC', max_length=20, blank=True)
    
    # Дополнительные характеристики (JSON)
    specifications = models.JSONField(
        'Дополнительные характеристики',
        default=dict,
        blank=True
    )
    
    # Статусы и флаги
    stock_status = models.CharField(
        'Статус наличия',
        max_length=20,
        choices=STOCK_STATUS_CHOICES,
        default='in_stock'
    )
    is_featured = models.BooleanField('Показывать в слайдере', default=False)
    is_new = models.BooleanField('Новинка', default=False)
    
    # Метрики
    views_count = models.IntegerField('Количество просмотров', default=0)
    average_rating = models.DecimalField(
        'Средний рейтинг',
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    
    # Временные метки
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'stock_status']),
            models.Index(fields=['price', 'stock_status']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['is_new']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def increment_views(self):
        """Увеличить счетчик просмотров"""
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def update_rating(self):
        """Обновить средний рейтинг на основе отзывов"""
        from reviews.models import Review
        reviews = Review.objects.filter(product=self, is_approved=True)
        if reviews.exists():
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            self.average_rating = round(avg, 2)
        else:
            self.average_rating = 0
        self.save(update_fields=['average_rating'])


class ProductImage(models.Model):
    """Изображения товара"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Товар'
    )
    image = models.ImageField('Изображение', upload_to='products/')
    order = models.IntegerField('Порядок', default=0)
    is_main = models.BooleanField('Главное фото', default=False)
    
    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.product.name} - Фото {self.order}"
    
    def save(self, *args, **kwargs):
        # Если это главное фото, убрать флаг у других
        if self.is_main:
            ProductImage.objects.filter(
                product=self.product,
                is_main=True
            ).exclude(pk=self.pk).update(is_main=False)
        super().save(*args, **kwargs)
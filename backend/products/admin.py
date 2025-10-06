# backend/products/admin.py - ПОЛНАЯ ВЕРСИЯ
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    max_num = 8
    fields = ['image', 'order', 'is_main', 'image_preview']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Превью'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'order', 'product_count']
    list_filter = ['parent']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Товаров'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'thumbnail',
        'name',
        'category',
        'price',
        'stock_status_badge',
        'is_featured',
        'is_new',
        'views_count',
        'average_rating',
        'created_at'
    ]
    list_filter = ['stock_status', 'category', 'is_featured', 'is_new', 'created_at']
    search_fields = ['name', 'description', 'blade_material', 'handle_material']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['views_count', 'average_rating', 'created_at', 'updated_at']
    inlines = [ProductImageInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'description', 'category', 'price')
        }),
        ('Характеристики', {
            'fields': (
                'blade_length',
                'total_length',
                'weight',
                'blade_thickness',
                'blade_material',
                'handle_material',
                'hardness',
                'specifications'
            )
        }),
        ('Статус', {
            'fields': ('stock_status', 'is_featured', 'is_new')
        }),
        ('Метрики', {
            'fields': ('views_count', 'average_rating', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_featured', 'mark_as_in_stock']
    
    def thumbnail(self, obj):
        main_image = obj.images.filter(is_main=True).first()
        if not main_image:
            main_image = obj.images.first()
        if main_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover;" />',
                main_image.image.url
            )
        return '-'
    thumbnail.short_description = 'Фото'
    
    def stock_status_badge(self, obj):
        colors = {
            'in_stock': '#28a745',
            'made_to_order': '#007bff',
            'out_of_stock': '#6c757d'
        }
        labels = {
            'in_stock': 'В наличии',
            'made_to_order': 'Под заказ',
            'out_of_stock': 'Нет в наличии'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            colors.get(obj.stock_status, '#6c757d'),
            labels.get(obj.stock_status, obj.stock_status)
        )
    stock_status_badge.short_description = 'Наличие'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} товаров добавлено в слайдер')
    mark_as_featured.short_description = 'Добавить в слайдер на главной'
    
    def mark_as_in_stock(self, request, queryset):
        updated = queryset.update(stock_status='in_stock')
        self.message_user(request, f'{updated} товаров отмечено как "В наличии"')
    mark_as_in_stock.short_description = 'Отметить как "В наличии"'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'order', 'is_main', 'image_preview']
    list_filter = ['is_main', 'product']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Превью'
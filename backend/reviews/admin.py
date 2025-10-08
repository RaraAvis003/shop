# backend/reviews/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Review, ReviewImage, ReviewHelpful


class ReviewImageInline(admin.TabularInline):
    model = ReviewImage
    extra = 1
    max_num = 5
    fields = ['image', 'order', 'image_preview']
    readonly_fields = ['image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return '-'
    image_preview.short_description = 'Превью'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'product',
        'user',
        'rating',
        'title',
        'is_approved',
        'is_verified_buyer',
        'helpful_count',
        'created_at'
    ]
    list_filter = ['is_approved', 'is_verified_buyer', 'rating', 'created_at']
    search_fields = ['title', 'text', 'user__username', 'product__name']
    readonly_fields = ['created_at', 'updated_at', 'helpful_count']
    inlines = [ReviewImageInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('product', 'user', 'rating', 'title', 'text')
        }),
        ('Оценка', {
            'fields': ('pros', 'cons')
        }),
        ('Статус', {
            'fields': ('is_approved', 'is_verified_buyer')
        }),
        ('Метрики', {
            'fields': ('helpful_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_reviews', 'mark_as_verified']
    
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'Одобрено отзывов: {updated}')
    approve_reviews.short_description = 'Одобрить выбранные отзывы'
    
    def mark_as_verified(self, request, queryset):
        updated = queryset.update(is_verified_buyer=True)
        self.message_user(request, f'Отмечено как проверенные покупки: {updated}')
    mark_as_verified.short_description = 'Отметить как проверенные покупки'


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ['review', 'user', 'created_at']
    list_filter = ['created_at']
    search_fields = ['review__title', 'user__username']
    readonly_fields = ['created_at']
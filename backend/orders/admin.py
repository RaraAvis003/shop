# backend/orders/admin.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Cart, CartItem, Order, OrderItem, Payment


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'total_price', 'reserved_until']
    can_delete = False
    
    def total_price(self, obj):
        # ИСПРАВЛЕНО: Проверка на существование объекта
        if obj.pk:
            return f"₽ {obj.get_total_price()}"
        return "—"
    total_price.short_description = 'Сумма'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_key', 'items_count', 'total', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'user__email', 'session_key']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CartItemInline]
    
    def items_count(self, obj):
        return obj.get_items_count()
    items_count.short_description = 'Товаров'
    
    def total(self, obj):
        return f"₽ {obj.get_total()}"
    total.short_description = 'Сумма'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1  # ИЗМЕНЕНО: Добавлена возможность добавлять товары
    readonly_fields = ['total_price']
    fields = ['product', 'quantity', 'price', 'total_price']
    
    def total_price(self, obj):
        # ИСПРАВЛЕНО: Проверка на существование объекта и заполненность полей
        if obj.pk and obj.price is not None and obj.quantity is not None:
            return f"₽ {obj.get_total_price()}"
        return "—"
    total_price.short_description = 'Сумма'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'name',
        'email',
        'phone',
        'status_badge',
        'final_amount_display',
        'created_at'
    ]
    list_filter = ['status', 'delivery_method', 'created_at']
    search_fields = ['id', 'name', 'email', 'phone', 'track_number']
    readonly_fields = [
        'created_at',
        'updated_at',
        'paid_at',
        'shipped_at',
        'delivered_at',
        'final_amount_display'
    ]
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Информация о заказе', {
            'fields': ('user', 'status', 'created_at', 'updated_at')
        }),
        ('Контактные данные', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Доставка', {
            'fields': (
                'delivery_method',
                'delivery_address',
                'delivery_cost',
                'track_number'
            )
        }),
        ('Стоимость', {
            'fields': (
                'total_amount',
                'discount_amount',
                'promo_code',
                'final_amount_display'
            )
        }),
        ('Дополнительно', {
            'fields': ('comment',)
        }),
        ('Временные метки', {
            'fields': ('paid_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_paid', 'mark_as_processing', 'mark_as_shipped']
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'paid': '#28a745',
            'processing': '#17a2b8',
            'shipped': '#007bff',
            'delivered': '#28a745',
            'made_to_order': '#6f42c1',
            'cancelled': '#dc3545',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
    
    def final_amount_display(self, obj):
        return f"₽ {obj.get_final_amount()}"
    final_amount_display.short_description = 'Итого к оплате'
    
    def mark_as_paid(self, request, queryset):
        for order in queryset:
            order.mark_as_paid()
        self.message_user(request, f'Отмечено как оплачено: {queryset.count()} заказов')
    mark_as_paid.short_description = 'Отметить как оплаченные'
    
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status='processing')
        self.message_user(request, f'Переведено в обработку: {updated} заказов')
    mark_as_processing.short_description = 'Перевести в обработку'
    
    def mark_as_shipped(self, request, queryset):
        for order in queryset:
            order.mark_as_shipped()
        self.message_user(request, f'Отмечено как отправлено: {queryset.count()} заказов')
    mark_as_shipped.short_description = 'Отметить как отправленные'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id',
        'order_link',
        'amount',
        'status_badge',
        'created_at'
    ]
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['payment_id', 'order__id', 'order__email']
    readonly_fields = [
        'payment_id',
        'idempotency_key',
        'metadata',
        'created_at',
        'updated_at'
    ]
    
    def order_link(self, obj):
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">Заказ #{}</a>', url, obj.order.id)
    order_link.short_description = 'Заказ'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'waiting_for_capture': '#17a2b8',
            'succeeded': '#28a745',
            'canceled': '#6c757d',
            'refunded': '#dc3545',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'
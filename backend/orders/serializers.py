from rest_framework import serializers
from django.utils import timezone
from .models import Cart, CartItem, Order, OrderItem, Payment
from products.serializers import ProductListSerializer


class CartItemSerializer(serializers.ModelSerializer):
    """Сериализатор товара в корзине"""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    total_price = serializers.SerializerMethodField()
    is_reserved = serializers.SerializerMethodField()
    time_left = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = [
            'id',
            'product',
            'product_id',
            'quantity',
            'total_price',
            'is_reserved',
            'reserved_until',
            'time_left',
            'created_at'
        ]
        read_only_fields = ['reserved_until', 'created_at']
    
    def get_total_price(self, obj):
        return float(obj.get_total_price())
    
    def get_is_reserved(self, obj):
        return obj.is_reserved()
    
    def get_time_left(self, obj):
        """Оставшееся время резервирования в секундах"""
        if obj.reserved_until and obj.is_reserved():
            delta = obj.reserved_until - timezone.now()
            return int(delta.total_seconds())
        return 0


class CartSerializer(serializers.ModelSerializer):
    """Сериализатор корзины"""
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'items_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total(self, obj):
        return float(obj.get_total())
    
    def get_items_count(self, obj):
        return obj.get_items_count()


class AddToCartSerializer(serializers.Serializer):
    """Сериализатор для добавления товара в корзину"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    
    def validate_product_id(self, value):
        from products.models import Product
        try:
            Product.objects.get(id=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError("Товар не найден")
        return value


class UpdateCartItemSerializer(serializers.Serializer):
    """Сериализатор для обновления количества товара"""
    quantity = serializers.IntegerField(min_value=1)


class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор товара в заказе"""
    product = ProductListSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'price', 'total_price']
    
    def get_total_price(self, obj):
        return float(obj.get_total_price())


class OrderSerializer(serializers.ModelSerializer):
    """Сериализатор заказа"""
    items = OrderItemSerializer(many=True, read_only=True)
    final_amount = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    delivery_method_display = serializers.CharField(
        source='get_delivery_method_display',
        read_only=True
    )
    
    class Meta:
        model = Order
        fields = [
            'id',
            'name',
            'email',
            'phone',
            'delivery_method',
            'delivery_method_display',
            'delivery_address',
            'delivery_cost',
            'total_amount',
            'discount_amount',
            'final_amount',
            'promo_code',
            'status',
            'status_display',
            'comment',
            'track_number',
            'items',
            'created_at',
            'updated_at',
            'paid_at',
            'shipped_at',
            'delivered_at'
        ]
        read_only_fields = [
            'created_at',
            'updated_at',
            'paid_at',
            'shipped_at',
            'delivered_at'
        ]
    
    def get_final_amount(self, obj):
        return float(obj.get_final_amount())


class CreateOrderSerializer(serializers.Serializer):
    """Сериализатор для создания заказа"""
    # Контактные данные
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    
    # Доставка
    delivery_method = serializers.ChoiceField(choices=Order.DELIVERY_CHOICES)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True)
    
    # Промокод
    promo_code = serializers.CharField(required=False, allow_blank=True)
    
    def validate_phone(self, value):
        """Валидация российского номера телефона"""
        import re
        # Простая валидация (можно усложнить)
        phone_regex = re.compile(r'^\+?7?\d{10}$')
        cleaned = re.sub(r'[^\d+]', '', value)
        if not phone_regex.match(cleaned):
            raise serializers.ValidationError(
                "Введите корректный номер телефона"
            )
        return value
    
    def validate(self, data):
        """Проверка, что адрес указан для доставки"""
        if data['delivery_method'] != 'pickup' and not data.get('delivery_address'):
            raise serializers.ValidationError({
                'delivery_address': 'Укажите адрес доставки'
            })
        return data


class PaymentSerializer(serializers.ModelSerializer):
    """Сериализатор платежа"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'payment_id',
            'amount',
            'currency',
            'status',
            'status_display',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
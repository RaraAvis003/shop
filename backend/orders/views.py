from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Cart, CartItem, Order, OrderItem
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
    OrderSerializer,
    CreateOrderSerializer
)
from products.models import Product


class CartViewSet(viewsets.ViewSet):
    """ViewSet для работы с корзиной"""
    permission_classes = [AllowAny]
    
    def get_cart(self, request):
        """Получить или создать корзину для пользователя/сессии"""
        if request.user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            cart, created = Cart.objects.get_or_create(session_key=session_key)
        return cart
    
    def list(self, request):
        """Получить корзину"""
        cart = self.get_cart(request)
        serializer = CartSerializer(cart)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def add_item(self, request):
        """Добавить товар в корзину"""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart = self.get_cart(request)
        product = get_object_or_404(Product, id=serializer.validated_data['product_id'])
        quantity = serializer.validated_data['quantity']
        
        # Проверка наличия товара
        if product.stock_status == 'out_of_stock':
            return Response(
                {'error': 'Товар отсутствует в наличии'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Добавить или обновить товар в корзине
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return Response(
            CartItemSerializer(cart_item).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['patch'], url_path='items/(?P<item_id>[^/.]+)')
    def update_item(self, request, item_id=None):
        """Обновить количество товара"""
        cart = self.get_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart_item.quantity = serializer.validated_data['quantity']
        cart_item.save()
        
        return Response(CartItemSerializer(cart_item).data)
    
    @action(detail=False, methods=['delete'], url_path='items/(?P<item_id>[^/.]+)')
    def remove_item(self, request, item_id=None):
        """Удалить товар из корзины"""
        cart = self.get_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Очистить корзину"""
        cart = self.get_cart(request)
        cart.clear()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def apply_promo(self, request):
        """Применить промокод (заглушка, будет реализовано позже)"""
        promo_code = request.data.get('promo_code', '').strip()
        
        if not promo_code:
            return Response(
                {'error': 'Промокод не указан'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # TODO: Реализовать проверку промокода через модель Promotion
        # Пока заглушка
        return Response({
            'message': 'Промокод применен',
            'discount': 0
        })


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с заказами"""
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]  # Для гостевых заказов
    
    def get_queryset(self):
        """Получить заказы текущего пользователя или по email для гостей"""
        if self.request.user.is_authenticated:
            return Order.objects.filter(user=self.request.user)
        
        # Для гостей - фильтр по email (требуется передать в query params)
        email = self.request.query_params.get('email')
        if email:
            return Order.objects.filter(email=email, user__isnull=True)
        
        return Order.objects.none()
    
    @transaction.atomic
    def create(self, request):
        """Создать заказ из корзины"""
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Получить корзину
        if request.user.is_authenticated:
            cart = get_object_or_404(Cart, user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                return Response(
                    {'error': 'Корзина пуста'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            cart = get_object_or_404(Cart, session_key=session_key)
        
        # Проверить, что корзина не пуста
        if not cart.items.exists():
            return Response(
                {'error': 'Корзина пуста'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Рассчитать стоимость доставки
        delivery_costs = {
            'courier_moscow': 500,
            'cdek_pickup': 350,
            'russian_post': 400,
            'pickup': 0,
        }
        delivery_cost = delivery_costs.get(
            serializer.validated_data['delivery_method'],
            0
        )
        
        # Создать заказ
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            name=serializer.validated_data['name'],
            email=serializer.validated_data['email'],
            phone=serializer.validated_data['phone'],
            delivery_method=serializer.validated_data['delivery_method'],
            delivery_address=serializer.validated_data.get('delivery_address', ''),
            delivery_cost=delivery_cost,
            comment=serializer.validated_data.get('comment', ''),
            promo_code=serializer.validated_data.get('promo_code', ''),
            total_amount=cart.get_total(),
            discount_amount=0  # TODO: Рассчитать из промокода
        )
        
        # Создать позиции заказа из корзины
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price  # Цена на момент заказа
            )
        
        # Очистить корзину
        cart.clear()
        
        # Вернуть созданный заказ
        order_serializer = OrderSerializer(order)
        return Response(order_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Отменить заказ"""
        order = self.get_object()
        
        # Проверить, можно ли отменить
        if order.status in ['shipped', 'delivered', 'cancelled']:
            return Response(
                {'error': f'Нельзя отменить заказ со статусом "{order.get_status_display()}"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.cancel()
        
        return Response(OrderSerializer(order).data)
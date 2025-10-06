# backend/products/views.py
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from .models import Category, Product
from .serializers import (
    CategorySerializer,
    ProductListSerializer,
    ProductDetailSerializer
)
from .filters import ProductFilter


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """API для категорий"""
    queryset = Category.objects.filter(parent=None)  # Только корневые категории
    serializer_class = CategorySerializer
    lookup_field = 'slug'


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """API для товаров"""
    queryset = Product.objects.select_related('category').prefetch_related('images')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'blade_material', 'handle_material']
    ordering_fields = ['price', 'created_at', 'views_count', 'average_rating']
    ordering = ['-created_at']
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Увеличить счетчик просмотров при получении детальной информации"""
        instance = self.get_object()
        instance.increment_views()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Товары для слайдера на главной"""
        products = self.queryset.filter(is_featured=True)[:5]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def new(self, request):
        """Новинки"""
        products = self.queryset.filter(is_new=True).order_by('-created_at')[:6]
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def similar(self, request, slug=None):
        """Похожие товары"""
        product = self.get_object()
        
        # Похожие товары из той же категории, в близком ценовом диапазоне
        price_min = product.price * 0.7
        price_max = product.price * 1.3
        
        similar_products = Product.objects.filter(
            category=product.category,
            price__gte=price_min,
            price__lte=price_max
        ).exclude(id=product.id).order_by('?')[:6]
        
        serializer = self.get_serializer(similar_products, many=True)
        return Response(serializer.data)
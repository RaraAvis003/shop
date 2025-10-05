from rest_framework import serializers
from .models import Category, Product, ProductImage


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категорий"""
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'icon_name', 'order', 'children']
    
    def get_children(self, obj):
        if obj.children.exists():
            return CategorySerializer(obj.children.all(), many=True).data
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    """Сериализатор для изображений товара"""
    
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'order', 'is_main']


class ProductListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка товаров (упрощенный)"""
    category = CategorySerializer(read_only=True)
    main_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'category',
            'price',
            'stock_status',
            'is_featured',
            'is_new',
            'average_rating',
            'main_image'
        ]
    
    def get_main_image(self, obj):
        main_image = obj.images.filter(is_main=True).first()
        if not main_image:
            main_image = obj.images.first()
        if main_image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(main_image.image.url)
            return main_image.image.url
        return None


class ProductDetailSerializer(serializers.ModelSerializer):
    """Детальный сериализатор для товара"""
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'category',
            'price',
            'blade_length',
            'total_length',
            'weight',
            'blade_thickness',
            'blade_material',
            'handle_material',
            'hardness',
            'specifications',
            'stock_status',
            'is_featured',
            'is_new',
            'views_count',
            'average_rating',
            'images',
            'created_at',
            'updated_at'
        ]
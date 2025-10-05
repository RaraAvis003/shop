import django_filters
from .models import Product


class ProductFilter(django_filters.FilterSet):
    """Фильтры для каталога товаров"""
    
    # Фильтр по цене
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    
    # Фильтры по характеристикам
    blade_length_min = django_filters.NumberFilter(field_name='blade_length', lookup_expr='gte')
    blade_length_max = django_filters.NumberFilter(field_name='blade_length', lookup_expr='lte')
    
    total_length_min = django_filters.NumberFilter(field_name='total_length', lookup_expr='gte')
    total_length_max = django_filters.NumberFilter(field_name='total_length', lookup_expr='lte')
    
    weight_min = django_filters.NumberFilter(field_name='weight', lookup_expr='gte')
    weight_max = django_filters.NumberFilter(field_name='weight', lookup_expr='lte')
    
    # Фильтры по материалам (множественный выбор)
    blade_material = django_filters.CharFilter(field_name='blade_material', lookup_expr='icontains')
    handle_material = django_filters.CharFilter(field_name='handle_material', lookup_expr='icontains')
    
    # Фильтр по категории (с учетом подкатегорий)
    category = django_filters.CharFilter(method='filter_by_category')
    
    # Фильтр по статусу
    stock_status = django_filters.ChoiceFilter(choices=Product.STOCK_STATUS_CHOICES)
    
    class Meta:
        model = Product
        fields = [
            'category',
            'stock_status',
            'is_featured',
            'is_new',
            'blade_material',
            'handle_material'
        ]
    
    def filter_by_category(self, queryset, name, value):
        """Фильтр по категории с учетом подкатегорий"""
        from .models import Category
        
        try:
            category = Category.objects.get(slug=value)
            # Получаем ID категории и всех её подкатегорий
            category_ids = [category.id]
            
            def get_children_ids(cat):
                for child in cat.children.all():
                    category_ids.append(child.id)
                    get_children_ids(child)
            
            get_children_ids(category)
            return queryset.filter(category_id__in=category_ids)
        except Category.DoesNotExist:
            return queryset.none()
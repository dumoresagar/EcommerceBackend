from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from .models import Category, Brand, Product
from .serializers import (
    CategorySerializer, CategoryTreeSerializer, BrandSerializer,
    ProductListSerializer, ProductDetailSerializer
)
from django.db.models import Count, Q, Min, Max  # Add Min, Max here

class CategoryTreeView(generics.ListAPIView):
    """Get hierarchical category tree"""
    serializer_class = CategoryTreeSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        return Category.objects.filter(parent__isnull=True, is_active=True).order_by('sort_order', 'name')

class CategoryListView(generics.ListAPIView):
    """Get flat list of all categories"""
    queryset = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]

class CategoryDetailView(generics.RetrieveAPIView):
    """Get category details by slug"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

class BrandListView(generics.ListAPIView):
    queryset = Brand.objects.filter(is_active=True).order_by('name')
    serializer_class = BrandSerializer
    permission_classes = [AllowAny]

class ProductListView(generics.ListAPIView):
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'brand', 'featured']
    search_fields = ['name', 'description', 'short_description']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True)
        
        # Category filtering with subcategories
        category_slug = self.request.query_params.get('category_slug', None)
        if category_slug:
            try:
                category = Category.objects.get(slug=category_slug, is_active=True)
                # Include products from current category and all subcategories
                all_categories = [category.id] + [cat.id for cat in category.get_all_children()]
                queryset = queryset.filter(category_id__in=all_categories)
            except Category.DoesNotExist:
                pass
        
        # Brand filtering
        brand_slug = self.request.query_params.get('brand_slug', None)
        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)
        
        # Price range filtering
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Stock availability
        in_stock = self.request.query_params.get('in_stock', None)
        if in_stock == 'true':
            queryset = queryset.filter(stock_quantity__gt=0)
        
        return queryset.select_related('category', 'brand').prefetch_related('images')

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

class FeaturedProductsView(generics.ListAPIView):
    queryset = Product.objects.filter(is_active=True, featured=True).select_related('category', 'brand').prefetch_related('images')
    serializer_class = ProductListSerializer
    permission_classes = [AllowAny]

@api_view(['GET'])
@permission_classes([AllowAny])
def product_filters(request):
    """Get filter options for products"""
    try:
        # Categories with product count
        categories = Category.objects.filter(is_active=True).annotate(
            product_count=Count('products', filter=Q(products__is_active=True))
        ).filter(product_count__gt=0).order_by('name')
        
        # Brands with product count
        brands = Brand.objects.filter(is_active=True).annotate(
            product_count=Count('products', filter=Q(products__is_active=True))
        ).filter(product_count__gt=0).order_by('name')
        
        # Price range
        price_range = Product.objects.filter(is_active=True).aggregate(
            min_price=Min('price'),
            max_price=Max('price')
        )
        
        # Handle case where no products exist
        if price_range['min_price'] is None:
            price_range = {'min_price': 0, 'max_price': 0}
        
        return Response({
            'categories': CategorySerializer(categories, many=True).data,
            'brands': BrandSerializer(brands, many=True).data,
            'price_range': price_range
        })
        
    except Exception as e:
        print(f"Error in product_filters: {e}")
        return Response({
            'categories': [],
            'brands': [],
            'price_range': {'min_price': 0, 'max_price': 0},
            'error': str(e)
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def category_products(request, category_slug):
    """Get products for a specific category"""
    try:
        category = Category.objects.get(slug=category_slug, is_active=True)
    except Category.DoesNotExist:
        return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Get products from current category and all subcategories
    all_categories = [category.id] + [cat.id for cat in category.get_all_children()]
    products = Product.objects.filter(
        category_id__in=all_categories,
        is_active=True
    ).select_related('category', 'brand').prefetch_related('images')
    
    # Apply additional filters
    brand_slug = request.query_params.get('brand_slug', None)
    if brand_slug:
        products = products.filter(brand__slug=brand_slug)
    
    min_price = request.query_params.get('min_price', None)
    max_price = request.query_params.get('max_price', None)
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Ordering
    ordering = request.query_params.get('ordering', '-created_at')
    products = products.order_by(ordering)
    
    # Pagination
    from rest_framework.pagination import PageNumberPagination
    paginator = PageNumberPagination()
    paginator.page_size = 20
    result_page = paginator.paginate_queryset(products, request)
    
    serializer = ProductListSerializer(result_page, many=True)
    return paginator.get_paginated_response({
        'category': CategorySerializer(category).data,
        'products': serializer.data
    })

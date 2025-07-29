from rest_framework import serializers
from .models import Category, Brand, Product, ProductImage, ProductAttribute

class CategoryTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    products_count = serializers.ReadOnlyField(source='get_products_count')
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'products_count', 'children']
    
    def get_children(self, obj):
        if obj.children.exists():
            return CategoryTreeSerializer(obj.children.filter(is_active=True), many=True).data
        return []

class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.ReadOnlyField(source='get_products_count')
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'parent', 'parent_name', 'products_count']

class BrandSerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo', 'description', 'products_count']
    
    def get_products_count(self, obj):
        return obj.products.filter(is_active=True).count()

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary']

class ProductAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductAttribute
        fields = ['id', 'name', 'value']

class ProductListSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    current_price = serializers.ReadOnlyField()
    average_rating = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'short_description', 'price', 'discount_price',
            'current_price', 'discount_percentage', 'category', 'brand', 'images',
            'average_rating', 'stock_quantity', 'featured'
        ]

class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    attributes = ProductAttributeSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    average_rating = serializers.ReadOnlyField()
    current_price = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = Product
        fields = '__all__'

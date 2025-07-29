from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.CategoryListView.as_view(), name='categories'),
    path('categories/tree/', views.CategoryTreeView.as_view(), name='category-tree'),
    path('categories/<slug:slug>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('brands/', views.BrandListView.as_view(), name='brands'),
    path('products/', views.ProductListView.as_view(), name='products'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('featured/', views.FeaturedProductsView.as_view(), name='featured-products'),
    path('filters/', views.product_filters, name='product-filters'),
    path('category/<slug:category_slug>/products/', views.category_products, name='category-products'),
]

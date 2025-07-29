from django.urls import path
from . import views

urlpatterns = [
    path('product/<int:product_id>/', views.ProductReviewsView.as_view(), name='product-reviews'),
    path('create/', views.CreateReviewView.as_view(), name='create-review'),
]

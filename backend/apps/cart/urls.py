from django.urls import path
from . import views

urlpatterns = [
    path('', views.CartView.as_view(), name='cart'),
    path('add/', views.add_to_cart, name='add-to-cart'),
    path('update/<int:item_id>/', views.update_cart_item, name='update-cart-item'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove-from-cart'),
]

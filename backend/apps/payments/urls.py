from django.urls import path
from . import views

urlpatterns = [
    path('', views.PaymentListView.as_view(), name='payment-list'),
    path('create-order/', views.create_razorpay_order, name='create-razorpay-order'),
    path('verify/', views.verify_payment, name='verify-payment'),
    path('webhook/', views.razorpay_webhook, name='razorpay-webhook'),
    path('<int:payment_id>/status/', views.payment_status, name='payment-status'),
]

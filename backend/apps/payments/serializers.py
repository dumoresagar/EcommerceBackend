from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('user', 'razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature')

class RazorpayOrderSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()

class PaymentVerificationSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()

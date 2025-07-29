import razorpay
import hmac
import hashlib
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import Payment
from .serializers import PaymentSerializer, RazorpayOrderSerializer, PaymentVerificationSerializer
from apps.orders.models import Order

# Initialize Razorpay client
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class PaymentListView(generics.ListAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).order_by('-created_at')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_razorpay_order(request):
    """Create a Razorpay Order"""
    serializer = RazorpayOrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        order_id = serializer.validated_data['order_id']
        order = Order.objects.get(id=order_id, user=request.user)
        
        # Check if payment already exists
        existing_payment = Payment.objects.filter(order=order).first()
        if existing_payment and existing_payment.status == 'captured':
            return Response(
                {'error': 'Payment already completed for this order'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or update payment record
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                'user': request.user,
                'amount': order.total_amount,
                'payment_method': 'card',
                'status': 'pending'
            }
        )
        
        # Create Razorpay Order
        razorpay_order_data = {
            'amount': payment.amount_in_paise,
            'currency': payment.currency,
            'receipt': f'order_{order.id}',
            'notes': {
                'order_id': order.id,
                'user_id': request.user.id,
                'payment_id': payment.id,
            }
        }
        
        razorpay_order = razorpay_client.order.create(data=razorpay_order_data)
        
        # Update payment with Razorpay Order ID
        payment.razorpay_order_id = razorpay_order['id']
        payment.status = 'processing'
        payment.save()
        
        return Response({
            'razorpay_order': {
                'id': razorpay_order['id'],
                'amount': razorpay_order['amount'],
                'currency': razorpay_order['currency'],
                'status': razorpay_order['status'],
            },
            'payment_id': payment.id,
            'key_id': settings.RAZORPAY_KEY_ID,
            'user_details': {
                'name': f"{request.user.first_name} {request.user.last_name}",
                'email': request.user.email,
                'contact': request.user.phone_number or '',
            }
        })
        
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': f'Order creation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    """Verify Razorpay payment"""
    serializer = PaymentVerificationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        razorpay_order_id = serializer.validated_data['razorpay_order_id']
        razorpay_payment_id = serializer.validated_data['razorpay_payment_id']
        razorpay_signature = serializer.validated_data['razorpay_signature']
        
        # Find our payment record
        payment = Payment.objects.get(
            razorpay_order_id=razorpay_order_id,
            user=request.user
        )
        
        # Verify signature
        generated_signature = hmac.new(
            settings.RAZORPAY_KEY_SECRET.encode(),
            f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        if generated_signature == razorpay_signature:
            # Payment is verified
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = 'captured'
            payment.save()
            
            # Update order status
            payment.order.payment_status = 'completed'
            payment.order.status = 'confirmed'
            payment.order.save()
            
            return Response({
                'payment_status': payment.status,
                'order_status': payment.order.status,
                'message': 'Payment verified successfully'
            })
        else:
            payment.status = 'failed'
            payment.failure_reason = 'Signature verification failed'
            payment.save()
            
            return Response({
                'error': 'Payment verification failed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
@require_POST
def razorpay_webhook(request):
    """Handle Razorpay webhooks"""
    webhook_secret = settings.RAZORPAY_KEY_SECRET
    webhook_signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')
    webhook_body = request.body

    try:
        # Verify webhook signature
        expected_signature = hmac.new(
            webhook_secret.encode(),
            webhook_body,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(webhook_signature, expected_signature):
            return HttpResponse('Invalid signature', status=400)
        
        import json
        event = json.loads(webhook_body)
        
        if event['event'] == 'payment.captured':
            payment_data = event['payload']['payment']['entity']
            handle_payment_captured(payment_data)
        elif event['event'] == 'payment.failed':
            payment_data = event['payload']['payment']['entity']
            handle_payment_failed(payment_data)
            
        return HttpResponse('Success', status=200)
        
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=400)

def handle_payment_captured(payment_data):
    """Handle successful payment capture"""
    try:
        payment = Payment.objects.get(razorpay_order_id=payment_data['order_id'])
        payment.status = 'captured'
        payment.razorpay_payment_id = payment_data['id']
        payment.save()
        
        # Update order status
        payment.order.payment_status = 'completed'
        payment.order.status = 'confirmed'
        payment.order.save()
        
    except Payment.DoesNotExist:
        print(f"Payment not found for order: {payment_data['order_id']}")

def handle_payment_failed(payment_data):
    """Handle failed payment"""
    try:
        payment = Payment.objects.get(razorpay_order_id=payment_data['order_id'])
        payment.status = 'failed'
        payment.failure_reason = payment_data.get('error_description', 'Payment failed')
        payment.save()
        
    except Payment.DoesNotExist:
        print(f"Payment not found for order: {payment_data['order_id']}")

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_status(request, payment_id):
    """Get payment status"""
    try:
        payment = Payment.objects.get(id=payment_id, user=request.user)
        return Response(PaymentSerializer(payment).data)
    except Payment.DoesNotExist:
        return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

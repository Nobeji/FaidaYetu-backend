import json
import re
import uuid
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from accounts.models import Notification, Order
from .models import Payment
from .serializers import InitiatePaymentSerializer, PaymentSerializer
from .services import ClickPesaService
from .sms_service import send_sms

def _make_order_ref(order_id):
    return f'FAIDA{order_id}{uuid.uuid4().hex[:6].upper()}'

def _normalize_phone(phone):
    phone = re.sub(r'[^0-9]', '', phone)
    if phone.startswith('0'):
        phone = '255' + phone[1:]
    elif not phone.startswith('255'):
        phone = '255' + phone
    return phone

class InitiatePaymentView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = InitiatePaymentSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        order_id = ser.validated_data['order_id']
        phone = _normalize_phone(ser.validated_data['phone'])

        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)

        if order.status == 'cancelled':
            return Response({'error': 'Order is cancelled'}, status=400)

        order_ref = _make_order_ref(order_id)
        callback_url = request.build_absolute_uri('/api/payments/webhook/')

        payment = Payment.objects.create(
            order=order,
            amount=order.total,
            phone=phone,
            order_ref=order_ref,
            status='pending',
        )

        svc = ClickPesaService()
        try:
            preview = svc.preview_push(phone, order.total, order_ref)
            if 'error' in preview:
                payment.status = 'failed'
                payment.message = str(preview['error'])
                payment.save()
                return Response({'error': preview['error']}, status=400)

            result = svc.initiate_push(phone, order.total, order_ref, callback_url)
            if 'error' in result:
                payment.status = 'failed'
                payment.message = str(result['error'])
                payment.save()
                return Response({'error': result['error']}, status=400)

            payment.clickpesa_ref = result.get('id', '')
            payment.message = result.get('status', 'PROCESSING')
            payment.save()

            return Response({
                'success': True,
                'payment_id': payment.id,
                'order_ref': order_ref,
                'message': 'Payment push sent to your phone. Check your mobile money.',
            })
        except Exception as e:
            payment.status = 'failed'
            payment.message = str(e)
            payment.save()
            return Response({'error': str(e)}, status=500)

@csrf_exempt
def payment_webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    order_ref = data.get('orderReference') or data.get('externalId')
    status_val = data.get('status', '').lower()
    clickpesa_ref = data.get('reference') or data.get('transactionId', '')

    if not order_ref:
        return JsonResponse({'error': 'Missing orderReference'}, status=400)

    try:
        payment = Payment.objects.get(order_ref=order_ref)
    except Payment.DoesNotExist:
        return JsonResponse({'error': 'Payment not found'}, status=404)

    if status_val in ('completed', 'success'):
        payment.status = 'completed'
        payment.message = data.get('message', 'Payment completed')
        for item in payment.order.items.all():
            product = item.product
            product.stock = max(0, product.stock - item.quantity)
            product.save()
        payment.order.status = 'ready'
        payment.order.save()

        order = payment.order
        supplier = order.supplier
        customer = order.customer
        items_list = ', '.join(f'{item.product.name} {item.quantity}' for item in order.items.all())

        cust_phone = customer.profile.phone
        cust_msg = f'Umefanikiwa kulipa TZS {order.total:,.0f} kwa bidhaa za {items_list} kutoka kwa {supplier.business_name}. Order No {order.id} inatayarishwa. Asante kwa ununuzi wako - FaidaYetu'
        if cust_phone:
            send_sms(cust_phone, cust_msg)
        Notification.objects.create(
            customer=customer,
            title='Malipo yamekamilika',
            message=cust_msg,
        )

        sup_phone = supplier.profile.phone
        sup_msg = f'Malipo yamethibitishwa. Mteja {customer.profile.user.username} amelipa TZS {order.total:,.0f} kwa bidhaa za {items_list}. Order No {order.id} tafadhali tayarisha bidhaa kwa usafirishaji - FaidaYetu'
        if sup_phone:
            send_sms(sup_phone, sup_msg)
        Notification.objects.create(
            supplier=supplier,
            title='Malipo yamekamilika',
            message=sup_msg,
        )
    elif status_val in ('failed', 'cancelled', 'expired'):
        payment.status = 'failed'
        payment.message = data.get('message', 'Payment failed')
    else:
        payment.status = 'pending'

    if clickpesa_ref:
        payment.clickpesa_ref = clickpesa_ref

    payment.save()
    return JsonResponse({'success': True})

class PaymentStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, order_id):
        payments = Payment.objects.filter(order_id=order_id).order_by('-created_at')
        if not payments.exists():
            return Response({'paid': False, 'payments': []})
        ser = PaymentSerializer(payments, many=True)
        latest = payments.first()
        return Response({
            'paid': latest.status == 'completed',
            'status': latest.status,
            'payments': ser.data,
        })

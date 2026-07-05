from django.urls import path
from . import views

urlpatterns = [
    path('api/payments/initiate/', views.InitiatePaymentView.as_view(), name='payment-initiate'),
    path('api/payments/webhook/', views.payment_webhook, name='payment-webhook'),
    path('api/payments/status/<int:order_id>/', views.PaymentStatusView.as_view(), name='payment-status'),
]

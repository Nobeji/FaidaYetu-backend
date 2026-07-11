from django.urls import path
from . import views

urlpatterns = [
    path('api/payments/initiate/', views.InitiatePaymentView.as_view(), name='payment-initiate'),
    path('api/payments/webhook/', views.payment_webhook, name='payment-webhook'),
    path('api/payments/status/<int:order_id>/', views.PaymentStatusView.as_view(), name='payment-status'),
    path('api/payments/verify/<int:order_id>/', views.VerifyPaymentView.as_view(), name='payment-verify'),
    path('api/payments/manual-confirm/<int:order_id>/', views.ManualConfirmPaymentView.as_view(), name='payment-manual-confirm'),
]

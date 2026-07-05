from django.db import models
from accounts.models import Order

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]
    CHANNEL_CHOICES = [
        ('mobile_money', 'Mobile Money'),
        ('card', 'Card'),
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.FloatField()
    phone = models.CharField(max_length=20, blank=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='mobile_money')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    clickpesa_ref = models.CharField(max_length=255, blank=True, null=True)
    order_ref = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Payment #{self.id} - {self.order_ref or self.order.id} - {self.status}'

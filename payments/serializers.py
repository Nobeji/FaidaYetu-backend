from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class InitiatePaymentSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    phone = serializers.CharField(max_length=20)

from accounts.models import DeliveryPerson, Order
from .models import Delivery, DeliveryLog
from rest_framework import serializers, viewsets, permissions, views, status
from rest_framework.response import Response
from rest_framework.decorators import action

class DeliveryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryLog
        fields = '__all__'

class DeliverySerializer(serializers.ModelSerializer):
    logs = DeliveryLogSerializer(many=True, read_only=True)
    class Meta:
        model = Delivery
        fields = '__all__'

class DeliveryListCreateView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        deliveries = Delivery.objects.all().order_by('-created_at')
        delivery_id = request.query_params.get('delivery_person')
        if delivery_id:
            deliveries = deliveries.filter(delivery_person_id=delivery_id)
        return Response(DeliverySerializer(deliveries, many=True).data)

    def post(self, request):
        serializer = DeliverySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)

class DeliveryDetailView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        delivery = Delivery.objects.get(pk=pk)
        return Response(DeliverySerializer(delivery).data)

    def patch(self, request, pk):
        delivery = Delivery.objects.get(pk=pk)
        new_status = request.data.get('status')
        serializer = DeliverySerializer(delivery, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if new_status == 'completed':
                dp = delivery.delivery_person
                dp.status = 'online'
                dp.total_routes += 1
                dp.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class LogLocationView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, delivery_id):
        delivery = Delivery.objects.get(pk=delivery_id)
        log = DeliveryLog.objects.create(
            delivery=delivery,
            lat=request.data.get('lat'),
            lng=request.data.get('lng'),
        )
        return Response(DeliveryLogSerializer(log).data, status=201)

class LatestLocationView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, delivery_id):
        try:
            log = DeliveryLog.objects.filter(delivery_id=delivery_id).latest('timestamp')
            return Response(DeliveryLogSerializer(log).data)
        except DeliveryLog.DoesNotExist:
            return Response({'lat': None, 'lng': None})

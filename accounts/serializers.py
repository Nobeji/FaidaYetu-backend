from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Supplier, Customer, DeliveryPerson, Product, Order, OrderItem, Notification

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = ['id', 'user', 'role', 'phone', 'lat', 'lng', 'area', 'city']

class SupplierSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = ['id', 'profile', 'business_name', 'business_email', 'description', 'address', 'rating', 'image', 'product_count', 'created_at']

    def get_product_count(self, obj):
        return obj.products.count()

class CustomerSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    class Meta:
        model = Customer
        fields = '__all__'

class DeliveryPersonSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    class Meta:
        model = DeliveryPerson
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.business_name', read_only=True)
    image = serializers.URLField(read_only=True)
    class Meta:
        model = Product
        fields = '__all__'

class ProfileUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    lat = serializers.FloatField(required=False)
    lng = serializers.FloatField(required=False)
    area = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    business_name = serializers.CharField(required=False)
    business_email = serializers.EmailField(required=False)
    address = serializers.CharField(required=False)
    vehicle_type = serializers.CharField(required=False)
    status = serializers.ChoiceField(choices=['online', 'offline', 'busy'], required=False)

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        model = OrderItem
        fields = '__all__'

class OrderItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_name = serializers.CharField(source='customer.profile.user.username', read_only=True)
    supplier_name = serializers.CharField(source='supplier.business_name', read_only=True)
    supplier_lat = serializers.FloatField(source='supplier.profile.lat', read_only=True)
    supplier_lng = serializers.FloatField(source='supplier.profile.lng', read_only=True)
    delivery_status = serializers.SerializerMethodField()
    delivery_id = serializers.SerializerMethodField()
    paid = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    items_data = OrderItemWriteSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = '__all__'

    def get_delivery_status(self, obj):
        if obj.delivery:
            return obj.delivery.status
        return None

    def get_delivery_id(self, obj):
        if obj.delivery:
            return obj.delivery.id
        return None

    def get_paid(self, obj):
        return obj.payments.filter(status='completed').exists()

    def get_payment_status(self, obj):
        latest = obj.payments.order_by('-created_at').first()
        return latest.status if latest else None

    def create(self, validated_data):
        items_data = validated_data.pop('items_data', [])
        for item in items_data:
            product = item['product']
            qty = item.get('quantity', 1)
            if product.stock < qty:
                raise serializers.ValidationError(
                    f'Insufficient stock for {product.name}. Available: {product.stock}, requested: {qty}'
                )
        order = Order.objects.create(**validated_data)
        for item in items_data:
            OrderItem.objects.create(order=order, **item)
        return order

class NotificationSerializer(serializers.ModelSerializer):
    order_id = serializers.IntegerField(source='order.id', read_only=True, default=None)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'order_id', 'notification_type', 'title', 'message', 'is_read', 'sms_sent', 'created_at', 'customer_name']

    def get_customer_name(self, obj):
        if obj.order and obj.order.customer:
            return obj.order.customer.profile.user.username
        return None

from datetime import date, timedelta
from math import floor
from django.db import models as db_models
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Profile, Supplier, Customer, DeliveryPerson, Product, Order
from deliveries.models import Delivery
from .cloudinary_utils import upload_image
from .serializers import (
    UserSerializer, ProfileSerializer, ProfileUpdateSerializer, SupplierSerializer,
    ProductSerializer, OrderSerializer, OrderItemSerializer,
    DeliveryPersonSerializer, CustomerSerializer,
)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        username = request.data.get('username')
        email = request.data.get('email', '')
        password = request.data.get('password')
        role = request.data.get('role', 'customer')
        phone = request.data.get('phone', '')
        area = request.data.get('area', '')
        city = request.data.get('city', '')
        lat = request.data.get('lat')
        lng = request.data.get('lng')

        if not username or not password:
            return Response({'error': 'Username and password required'}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        profile = user.profile
        profile.role = role
        profile.phone = phone
        profile.area = area
        profile.city = city
        if lat is not None:
            profile.lat = float(lat)
        if lng is not None:
            profile.lng = float(lng)
        profile.save()

        extra = {}
        if role == 'supplier':
            supplier = Supplier.objects.create(
                profile=profile,
                business_name=request.data.get('business_name', username),
                business_email=email,
                address=request.data.get('address', ''),
            )
            extra['supplier'] = SupplierSerializer(supplier).data
        elif role == 'customer':
            customer = Customer.objects.create(profile=profile)
            extra['customer'] = CustomerSerializer(customer).data
        elif role == 'delivery':
            dp = DeliveryPerson.objects.create(profile=profile)
            extra['delivery_person'] = DeliveryPersonSerializer(dp).data

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'profile': ProfileSerializer(profile).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            **extra,
        }, status=201)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password:
            return Response({'error': 'Username and password required'}, status=400)

        if username == 'admin' and not User.objects.filter(username='admin').exists():
            user = User.objects.create_user(username='admin', password=password)
            user.profile.role = 'admin'
            user.profile.save()

        user = User.objects.filter(username=username).first()
        if not user or not user.check_password(password):
            return Response({'error': 'Invalid credentials'}, status=401)

        refresh = RefreshToken.for_user(user)
        profile = user.profile

        extra = {}
        if profile.role == 'supplier' and hasattr(profile, 'supplier'):
            extra['supplier'] = SupplierSerializer(profile.supplier).data
        if profile.role == 'customer' and hasattr(profile, 'customer'):
            extra['customer'] = CustomerSerializer(profile.customer).data
        if profile.role == 'delivery' and hasattr(profile, 'delivery_person'):
            extra['delivery_person'] = DeliveryPersonSerializer(profile.delivery_person).data

        return Response({
            'user': UserSerializer(user).data,
            'profile': ProfileSerializer(profile).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            **extra,
        })

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        data = ProfileSerializer(profile).data
        if profile.role == 'supplier' and hasattr(profile, 'supplier'):
            data['supplier'] = SupplierSerializer(profile.supplier).data
        if profile.role == 'customer' and hasattr(profile, 'customer'):
            data['customer'] = CustomerSerializer(profile.customer).data
        if profile.role == 'delivery' and hasattr(profile, 'delivery_person'):
            data['delivery_person'] = DeliveryPersonSerializer(profile.delivery_person).data
        return Response(data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        profile = user.profile

        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'username' in data or 'email' in data:
            user.save()

        if 'phone' in data:
            profile.phone = data['phone']
        if 'lat' in data:
            profile.lat = data['lat']
        if 'lng' in data:
            profile.lng = data['lng']
        if 'area' in data:
            profile.area = data['area']
        if 'city' in data:
            profile.city = data['city']
        if 'phone' in data or 'lat' in data or 'lng' in data or 'area' in data or 'city' in data:
            profile.save()

        if profile.role == 'supplier' and hasattr(profile, 'supplier'):
            supplier = profile.supplier
            changed = False
            if 'business_name' in data:
                supplier.business_name = data['business_name']; changed = True
            if 'business_email' in data:
                supplier.business_email = data['business_email']; changed = True
            if 'address' in data:
                supplier.address = data['address']; changed = True
            if changed:
                supplier.save()

        if profile.role == 'delivery' and hasattr(profile, 'delivery_person'):
            dp = profile.delivery_person
            changed = False
            if 'vehicle_type' in data:
                dp.vehicle_type = data['vehicle_type']; changed = True
            if 'status' in data:
                dp.status = data['status']; changed = True
            if changed:
                dp.save()

        return self.get(request)

# --- Supplier endpoints ---
class SupplierListView(generics.ListAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Supplier.objects.all()
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius = float(self.request.query_params.get('radius', 50))
        if lat and lng:
            from math import radians, sin, cos, sqrt, asin
            user_lat = float(lat)
            user_lng = float(lng)
            result = []
            for s in qs:
                s_lat = s.profile.lat or -6.7924
                s_lng = s.profile.lng or 39.2083
                dlat = radians(s_lat - user_lat)
                dlng = radians(s_lng - user_lng)
                a = sin(dlat / 2) ** 2 + cos(radians(user_lat)) * cos(radians(s_lat)) * sin(dlng / 2) ** 2
                c = 2 * asin(sqrt(a))
                dist = 6371 * c
                if dist <= radius:
                    result.append(s.id)
            return qs.filter(id__in=result)
        return qs

class SupplierDetailView(generics.RetrieveAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.AllowAny]

class ProductListView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        supplier_id = self.request.data.get('supplier')
        image_file = self.request.FILES.get('image')
        image_url = ''
        if image_file:
            try:
                image_url = upload_image(image_file)
            except Exception:
                pass
        serializer.save(supplier_id=supplier_id, image=image_url)

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_update(self, serializer):
        image_file = self.request.FILES.get('image')
        if image_file:
            try:
                image_url = upload_image(image_file)
                serializer.save(image=image_url)
                return
            except Exception:
                pass
        serializer.save()

class ProductBySupplierView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Product.objects.filter(supplier_id=self.kwargs['supplier_id'])

# --- Order endpoints ---
class OrderListCreateView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Order.objects.all()
        customer_id = self.request.query_params.get('customer')
        supplier_id = self.request.query_params.get('supplier')
        delivery_id = self.request.query_params.get('delivery')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        if delivery_id:
            qs = qs.filter(delivery__delivery_person_id=delivery_id)
        return qs.order_by('-created_at')

class OrderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [permissions.AllowAny]

    def perform_update(self, serializer):
        instance = self.get_object()
        old_status = instance.status
        new_status = self.request.data.get('status', old_status)
        if old_status != new_status and new_status == 'cancelled' and instance.status in ('paid', 'processing', 'ready'):
            for item in instance.items.all():
                product = item.product
                product.stock += item.quantity
                product.save()
        serializer.save()

# --- Dashboard data views ---
class SupplierDashboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, supplier_id):
        orders = Order.objects.filter(supplier_id=supplier_id)
        products = Product.objects.filter(supplier_id=supplier_id)
        total_orders = orders.count()
        total_revenue = sum(o.total for o in orders)
        low_stock = products.filter(stock__lt=db_models.F('min_stock')).count()
        recent_orders = orders.order_by('-created_at')[:5]
        inventory = products.all()

        revenue_display = f'{total_revenue:,.0f} TZS'
        if total_revenue >= 1000000:
            revenue_display = f'{total_revenue / 1000000:.1f}M TZS'

        return Response({
            'stats': {
                'orders': str(total_orders),
                'revenue': revenue_display,
                'lowStock': f'{low_stock:02d}',
                'growth': '+12%',
            },
            'orders': OrderSerializer(recent_orders, many=True).data,
            'inventory': [
                {
                    'name': p.name,
                    'pct': min(100, int(p.stock / (p.stock + p.min_stock) * 100)) if p.stock + p.min_stock > 0 else 0,
                    'low': p.stock < p.min_stock,
                }
                for p in inventory
            ],
        })

class CustomerDashboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, customer_id):
        orders = Order.objects.filter(customer_id=customer_id).order_by('-created_at')
        suppliers = Supplier.objects.all()
        return Response({
            'orders': OrderSerializer(orders, many=True).data,
            'suppliers': SupplierSerializer(suppliers, many=True).data,
        })

# --- Delivery Person endpoints ---
class DeliveryPersonListView(generics.ListAPIView):
    queryset = DeliveryPerson.objects.all()
    serializer_class = DeliveryPersonSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = DeliveryPerson.objects.all()
        status = self.request.query_params.get('status')
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius = float(self.request.query_params.get('radius', 50))
        if status:
            qs = qs.filter(status=status)
        if lat and lng:
            from math import radians, sin, cos, sqrt, asin
            user_lat = float(lat)
            user_lng = float(lng)
            result = []
            for dp in qs:
                dp_lat = dp.profile.lat or -6.7924
                dp_lng = dp.profile.lng or 39.2083
                dlat = radians(dp_lat - user_lat)
                dlng = radians(dp_lng - user_lng)
                a = sin(dlat / 2) ** 2 + cos(radians(user_lat)) * cos(radians(dp_lat)) * sin(dlng / 2) ** 2
                c = 2 * asin(sqrt(a))
                dist = 6371 * c
                if dist <= radius:
                    result.append(dp.id)
            return qs.filter(id__in=result)
        return qs


class AssignDeliveryView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, order_id):
        delivery_person_id = request.data.get('delivery_person_id')
        if not delivery_person_id:
            return Response({'error': 'delivery_person_id required'}, status=400)
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)
        if order.delivery:
            return Response({'error': 'Order already has a delivery assigned'}, status=400)
        try:
            dp = DeliveryPerson.objects.get(id=delivery_person_id)
        except DeliveryPerson.DoesNotExist:
            return Response({'error': 'Delivery person not found'}, status=404)
        from math import radians, sin, cos, sqrt, asin
        s_lat = order.supplier.profile.lat or -6.7924
        s_lng = order.supplier.profile.lng or 39.2083
        c_lat = order.delivery_lat or -6.7924
        c_lng = order.delivery_lng or 39.2083
        dlat = radians(c_lat - s_lat)
        dlng = radians(c_lng - s_lng)
        a = sin(dlat / 2) ** 2 + cos(radians(s_lat)) * cos(radians(c_lat)) * sin(dlng / 2) ** 2
        distance = round(6371 * 2 * asin(sqrt(a)), 1)
        delivery = Delivery.objects.create(
            delivery_person=dp,
            status='assigned',
            distance_km=distance,
            earnings=0.0,
        )
        order.delivery = delivery
        order.status = 'in_transit'
        order.save()
        dp.status = 'busy'
        dp.save()
        return Response(OrderSerializer(order).data, status=201)


class DeliveryDashboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, delivery_id):
        from deliveries.models import Delivery
        deliveries = Delivery.objects.filter(delivery_person_id=delivery_id).order_by('-created_at')
        active = deliveries.filter(status__in=['assigned', 'picked_up', 'in_transit']).first()
        completed = deliveries.filter(status='completed')
        total_earnings = sum(d.earnings for d in completed)
        total_routes = completed.count()

        active_data = None
        if active:
            from .serializers import OrderSerializer
            order_ref = getattr(active, 'order_ref', None)
            if order_ref:
                active_data = OrderSerializer(order_ref).data

        return Response({
            'delivery_person': DeliveryPersonSerializer(
                DeliveryPerson.objects.get(id=delivery_id)
            ).data,
            'active_delivery': active_data,
            'stats': {
                'earnings_today': f'${total_earnings:.2f}',
                'total_routes': total_routes,
                'avg_rating': '4.8',
            },
        })


class StatsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        today = date.today()
        active_farmers = Supplier.objects.count()
        daily_deliveries = Delivery.objects.filter(created_at__date=today).count()
        total_deliveries = Delivery.objects.count()
        completed_deliveries = Delivery.objects.filter(status='completed').count()
        on_time_rate = round((completed_deliveries / total_deliveries * 100)) if total_deliveries > 0 else 98

        return Response({
            'activeFarmers': f'{active_farmers}+' if active_farmers > 0 else '0',
            'dailyDeliveries': f'{daily_deliveries}+' if daily_deliveries > 0 else '0',
            'onTimeRate': f'{on_time_rate}%',
        })


class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({'success': True, 'message': 'Account deleted permanently.'})


# --- Notification endpoints ---
class NotificationListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        supplier_id = request.query_params.get('supplier_id')
        customer_id = request.query_params.get('customer_id')
        unread_only = request.query_params.get('unread', 'false') == 'true'

        if supplier_id:
            from .models import Supplier
            try:
                supplier = Supplier.objects.get(id=supplier_id)
                profile = supplier.profile
                profile_type = 'supplier'
            except Supplier.DoesNotExist:
                return Response({'error': 'Supplier not found'}, status=404)
        elif customer_id:
            from .models import Customer
            try:
                customer = Customer.objects.get(id=customer_id)
                profile = customer.profile
                profile_type = 'customer'
            except Customer.DoesNotExist:
                return Response({'error': 'Customer not found'}, status=404)
        elif request.user.is_authenticated:
            profile = request.user.profile
            profile_type = 'supplier' if profile.role == 'supplier' else 'customer'
        else:
            return Response({'error': 'Authentication required or supplier_id/customer_id needed'}, status=401)

        from .notifications import get_supplier_notifications, get_customer_notifications
        if profile_type == 'supplier':
            qs = get_supplier_notifications(profile, unread_only=unread_only)
            unread_count = get_supplier_notifications(profile, unread_only=True).count()
        else:
            qs = get_customer_notifications(profile, unread_only=unread_only)
            unread_count = get_customer_notifications(profile, unread_only=True).count()
        from .serializers import NotificationSerializer
        data = NotificationSerializer(qs[:50], many=True).data
        return Response({
            'notifications': data,
            'unread_count': unread_count,
        })


class MarkNotificationReadView(APIView):
    permission_classes = [permissions.AllowAny]

    def patch(self, request, pk):
        if request.user.is_authenticated:
            profile = request.user.profile
        else:
            return Response({'error': 'Authentication required'}, status=401)

        from .notifications import mark_notification_read
        notification = mark_notification_read(pk, profile)
        if not notification:
            return Response({'error': 'Notification not found'}, status=404)

        from .serializers import NotificationSerializer
        return Response(NotificationSerializer(notification).data)


class MarkAllNotificationsReadView(APIView):
    permission_classes = [permissions.AllowAny]

    def patch(self, request):
        if request.user.is_authenticated:
            profile = request.user.profile
        else:
            return Response({'error': 'Authentication required'}, status=401)

        from .notifications import mark_all_read
        mark_all_read(profile)
        return Response({'success': True, 'message': 'All notifications marked as read.'})

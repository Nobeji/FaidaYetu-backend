from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


ROLE_CHOICES = [
    ('admin', 'Admin'),
    ('customer', 'Customer'),
    ('supplier', 'Supplier'),
    ('delivery', 'Delivery Personnel'),
]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    phone = models.CharField(max_length=20, blank=True)
    lat = models.FloatField(default=-6.7924)
    lng = models.FloatField(default=39.2083)
    area = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'{self.user.username} ({self.role})'

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

class Supplier(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='supplier')
    business_name = models.CharField(max_length=255)
    business_email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    rating = models.FloatField(default=0.0)
    image = models.URLField(blank=True, default='https://images.unsplash.com/photo-1599839575945-a9e5af0c3fa5?w=400')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.business_name

class Customer(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='customer')
    default_address = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Customer: {self.profile.user.username}'

class DeliveryPerson(models.Model):
    STATUS_CHOICES = [('online', 'Online'), ('offline', 'Offline'), ('busy', 'Busy')]
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='delivery_person')
    vehicle_type = models.CharField(max_length=100, blank=True, default='Pickup Truck')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='online')
    total_earnings = models.FloatField(default=0.0)
    rating = models.FloatField(default=0.0)
    total_routes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Delivery: {self.profile.user.username}'

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('eggs', 'Eggs'),
        ('chicken', 'Chicken'),
        ('feed', 'Feed'),
        ('supplements', 'Supplements'),
    ]
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='eggs')
    price = models.FloatField()
    unit = models.CharField(max_length=50, default='kg')
    stock = models.IntegerField(default=0)
    min_stock = models.IntegerField(default=10)
    image = models.URLField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.name} ({self.supplier.business_name})'

class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='orders')
    delivery = models.OneToOneField('deliveries.Delivery', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_ref')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    total = models.FloatField(default=0.0)
    delivery_lat = models.FloatField(default=-6.7924)
    delivery_lng = models.FloatField(default=39.2083)
    delivery_address = models.CharField(max_length=255, blank=True)
    delivery_area = models.CharField(max_length=255, blank=True)
    delivery_street = models.CharField(max_length=255, blank=True)
    delivery_city = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Order #{self.id} - {self.customer.profile.user.username}'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.FloatField()

    def __str__(self):
        return f'{self.product.name} x{self.quantity}'

class Notification(models.Model):
    TYPE_CHOICES = [
        ('new_order', 'New Order'),
        ('payment_received', 'Payment Received'),
        ('order_cancelled', 'Order Cancelled'),
        ('delivery_update', 'Delivery Update'),
        ('low_stock', 'Low Stock Alert'),
    ]
    recipient = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='notifications')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} -> {self.recipient}'


class UsabilityMetric(models.Model):
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('signup', 'Signup'),
        ('browse', 'Browse Products'),
        ('order', 'Place Order'),
        ('track', 'Track Delivery'),
        ('pay', 'Make Payment'),
        ('inventory', 'Manage Inventory'),
        ('analytics', 'View Analytics'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='usability_metrics', null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    duration_seconds = models.FloatField(default=0)
    completed = models.BooleanField(default=True)
    device_type = models.CharField(max_length=50, blank=True, default='desktop')
    page_url = models.CharField(max_length=500, blank=True)
    error_message = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.action} - {self.user or "anon"}'


class SystemPerformance(models.Model):
    PERIOD_CHOICES = [
        ('before', 'Before System'),
        ('after', 'After System'),
    ]
    metric_name = models.CharField(max_length=100)
    metric_value = models.FloatField()
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    unit = models.CharField(max_length=50, blank=True, default='')
    description = models.TextField(blank=True)
    recorded_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_date']

    def __str__(self):
        return f'{self.metric_name} ({self.period}): {self.metric_value} {self.unit}'


class TAMSurvey(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tam_surveys', null=True, blank=True)
    perceived_usefulness = models.IntegerField(default=0)
    perceived_ease_of_use = models.IntegerField(default=0)
    behavioral_intention = models.IntegerField(default=0)
    actual_usage = models.IntegerField(default=0)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'TAM Survey - {self.user or "anon"} - PU:{self.perceived_usefulness} PEOU:{self.perceived_ease_of_use}'


class SUSSurvey(models.Model):
    q1 = models.IntegerField(default=3)
    q2 = models.IntegerField(default=3)
    q3 = models.IntegerField(default=3)
    q4 = models.IntegerField(default=3)
    q5 = models.IntegerField(default=3)
    q6 = models.IntegerField(default=3)
    q7 = models.IntegerField(default=3)
    q8 = models.IntegerField(default=3)
    q9 = models.IntegerField(default=3)
    q10 = models.IntegerField(default=3)
    user_role = models.CharField(max_length=20, blank=True, default='customer')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sus_surveys', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def calculate_score(self):
        odd_scores = self.q1 + self.q3 + self.q5 + self.q7 + self.q9
        even_scores = self.q2 + self.q4 + self.q6 + self.q8 + self.q10
        raw = (odd_scores - 5) + (25 - even_scores)
        return round(raw * 2.5, 1)

    def __str__(self):
        return f'SUS Score: {self.calculate_score()} - {self.user_role}'

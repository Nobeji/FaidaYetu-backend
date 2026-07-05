import os, sys, django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from accounts.models import Profile, Supplier, Customer, DeliveryPerson, Product, Order, OrderItem
from deliveries.models import Delivery, DeliveryLog

def seed():
    print('Seeding database...')

    # --- Users ---
    supplier_user, _ = User.objects.get_or_create(username='supplier1', defaults={'email': 'supplier@faidayetu.co.tz'})
    supplier_user.set_password('password123')
    supplier_user.save()
    supplier_user.profile.role = 'supplier'
    supplier_user.profile.phone = '+255 712 345 678'
    supplier_user.profile.lat = -6.7924
    supplier_user.profile.lng = 39.2083
    supplier_user.profile.save()

    supplier, _ = Supplier.objects.get_or_create(
        profile=supplier_user.profile,
        defaults={
            'business_name': 'Premium Poultry Co.',
            'business_email': 'supplier@faidayetu.co.tz',
            'description': 'Leading poultry supplier in Dar es Salaam. Farm-fresh eggs and organic chicken.',
            'address': 'Gate 4, Industrial Zone B, Dar es Salaam',
            'rating': 4.8,
            'image': 'https://images.unsplash.com/photo-1599839575945-a9e5af0c3fa5?w=400',
        }
    )

    supplier2_user, _ = User.objects.get_or_create(username='supplier2', defaults={'email': 'mbezi@faidayetu.co.tz'})
    supplier2_user.set_password('password123')
    supplier2_user.save()
    supplier2_user.profile.role = 'supplier'
    supplier2_user.profile.phone = '+255 713 456 789'
    supplier2_user.profile.lat = -6.8731
    supplier2_user.profile.lng = 39.2578
    supplier2_user.profile.save()

    supplier2, _ = Supplier.objects.get_or_create(
        profile=supplier2_user.profile,
        defaults={
            'business_name': 'Mbezi Fresh Farms',
            'business_email': 'mbezi@faidayetu.co.tz',
            'description': 'Fresh poultry products from Mbezi area.',
            'address': 'Mbezi Beach, Dar es Salaam',
            'rating': 4.9,
            'image': 'https://images.unsplash.com/photo-1486427944544-d2c246c4a3a1?w=400',
        }
    )

    supplier3_user, _ = User.objects.get_or_create(username='supplier3', defaults={'email': 'city@faidayetu.co.tz'})
    supplier3_user.set_password('password123')
    supplier3_user.save()
    supplier3_user.profile.role = 'supplier'
    supplier3_user.profile.phone = '+255 714 567 890'
    supplier3_user.profile.lat = -6.8167
    supplier3_user.profile.lng = 39.2833
    supplier3_user.profile.save()

    supplier3, _ = Supplier.objects.get_or_create(
        profile=supplier3_user.profile,
        defaults={
            'business_name': 'City Chickens Ltd',
            'business_email': 'city@faidayetu.co.tz',
            'description': 'Urban poultry solutions for Dar es Salaam.',
            'address': 'City Center, Dar es Salaam',
            'rating': 4.7,
            'image': 'https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=400',
        }
    )

    # Customer
    customer_user, _ = User.objects.get_or_create(username='customer1', defaults={'email': 'jane@example.com'})
    customer_user.set_password('password123')
    customer_user.save()
    customer_user.profile.role = 'customer'
    customer_user.profile.phone = '+255 715 678 901'
    customer_user.profile.lat = -6.8200
    customer_user.profile.lng = 39.2800
    customer_user.profile.save()
    customer, _ = Customer.objects.get_or_create(profile=customer_user.profile, defaults={'default_address': 'Kariakoo, Dar es Salaam'})

    # Delivery
    delivery_user, _ = User.objects.get_or_create(username='delivery1', defaults={'email': 'john@faidayetu.co.tz'})
    delivery_user.set_password('password123')
    delivery_user.save()
    delivery_user.profile.role = 'delivery'
    delivery_user.profile.phone = '+255 716 789 012'
    delivery_user.profile.lat = -6.7900
    delivery_user.profile.lng = 39.2100
    delivery_user.profile.save()
    delivery_person, _ = DeliveryPerson.objects.get_or_create(
        profile=delivery_user.profile,
        defaults={'vehicle_type': 'Pickup Truck (Toyota Hilux)', 'status': 'online'}
    )

    # Products
    products_data = [
        {'supplier': supplier, 'name': 'Grade A Eggs (Large 30pk)', 'category': 'eggs', 'price': 12000, 'stock': 1240, 'min_stock': 200, 'image': 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400'},
        {'supplier': supplier, 'name': 'Organic Broiler (whole)', 'category': 'chicken', 'price': 18500, 'stock': 84, 'min_stock': 100, 'image': 'https://images.unsplash.com/photo-1587593810167-a84920ea0781?w=400'},
        {'supplier': supplier, 'name': 'Kienyeji Chicken (1kg)', 'category': 'chicken', 'price': 14000, 'stock': 45, 'min_stock': 30, 'image': 'https://images.unsplash.com/photo-1567620832903-9fc6debc209f?w=400'},
        {'supplier': supplier, 'name': 'Poultry Feed (50kg bag)', 'category': 'feed', 'price': 45000, 'stock': 320, 'min_stock': 80, 'image': 'https://images.unsplash.com/photo-1599839575945-a9e5af0c3fa5?w=400'},
        {'supplier': supplier2, 'name': 'Free Range Eggs (12pk)', 'category': 'eggs', 'price': 6500, 'stock': 500, 'min_stock': 50, 'image': 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400'},
        {'supplier': supplier2, 'name': 'Dressed Chicken (2kg)', 'category': 'chicken', 'price': 22000, 'stock': 60, 'min_stock': 20, 'image': 'https://images.unsplash.com/photo-1587593810167-a84920ea0781?w=400'},
        {'supplier': supplier3, 'name': 'Local Brew Ingredients', 'category': 'supplements', 'price': 8500, 'stock': 200, 'min_stock': 40, 'image': 'https://images.unsplash.com/photo-1567620832903-9fc6debc209f?w=400'},
    ]

    for p in products_data:
        Product.objects.get_or_create(
            supplier=p['supplier'],
            name=p['name'],
            defaults={
                'category': p['category'],
                'price': p['price'],
                'stock': p['stock'],
                'min_stock': p['min_stock'],
                'image': p['image'],
                'unit': 'unit',
            }
        )

    # Orders
    product1 = Product.objects.filter(supplier=supplier).first()
    product2 = Product.objects.filter(supplier=supplier2).first()
    product3 = Product.objects.filter(supplier=supplier3).first()

    order_statuses = ['new', 'processing', 'ready', 'in_transit', 'delivered', 'cancelled']
    for i, status in enumerate(order_statuses):
        suppliers_list = [supplier, supplier2, supplier3]
        s = suppliers_list[i % 3]
        p = Product.objects.filter(supplier=s).first()
        if p:
            order_total = p.price * (i + 1)
            order, created = Order.objects.get_or_create(
                customer=customer,
                supplier=s,
                status=status,
                total=order_total,
                delivery_address=customer.default_address,
                delivery_lat=-6.8200 + (i * 0.01),
                delivery_lng=39.2800 + (i * 0.01),
            )
            if created:
                OrderItem.objects.create(order=order, product=p, quantity=i + 1, price=p.price)

    # Deliveries
    completed_order = Order.objects.filter(status='delivered').first()
    if completed_order:
        delivery, created = Delivery.objects.get_or_create(
            delivery_person=delivery_person,
            status='completed',
            defaults={'distance_km': 12.4, 'earnings': 22.0}
        )
        if created:
            completed_order.delivery = delivery
            completed_order.save()
            DeliveryLog.objects.create(delivery=delivery, lat=-6.7924, lng=39.2083)
            DeliveryLog.objects.create(delivery=delivery, lat=-6.8200, lng=39.2800)

    in_transit_order = Order.objects.filter(status='in_transit').first()
    if in_transit_order:
        delivery2, created = Delivery.objects.get_or_create(
            delivery_person=delivery_person,
            status='in_transit',
            defaults={'distance_km': 8.1, 'earnings': 18.5}
        )
        if created:
            in_transit_order.delivery = delivery2
            in_transit_order.save()
            DeliveryLog.objects.create(delivery=delivery2, lat=-6.7900, lng=39.2100)
            DeliveryLog.objects.create(delivery=delivery2, lat=-6.8100, lng=39.2500)

    print('Seed complete!')
    print(f'Users: 5 (supplier1, supplier2, supplier3, customer1, delivery1)')
    print(f'Password for all: password123')

if __name__ == '__main__':
    seed()

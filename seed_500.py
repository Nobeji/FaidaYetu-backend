#!/usr/bin/env python
"""Seed 500 simulated transactions for the FaidaYetu pilot study.
Run from back-end directory: python seed_500.py
"""
import os
import sys
import random
import django
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from accounts.models import Profile, Supplier, Customer, Order, OrderItem
from products.models import Product
from deliveries.models import Delivery, DeliveryLog
from django.utils import timezone

CUSTOMER_NAMES = [
    'Amina Hassan', 'Fatima Omar', 'Halima Juma', 'Rehema Kilonzo', 'Neema Kimaro',
    'Juma Mwangi', 'Ibrahim Salim', 'Omary Festo', 'Hassan Ali', 'Ramadhani Bakari',
    'Asha Mwinyi', 'Zainab Hamisi', 'Mwanaisha Salum', 'Saida Mussa', 'Baraka John',
    'Collins Odhiambo', 'Grace Wanjiku', 'Peter Njoroge', 'Samuel Kipchoge', 'David Mutua',
    'Mary Akinyi', 'Joseph Kamau', 'Rose Nyambura', 'Daniel Mwenda', 'Catherine Achieng',
    'Emmanuel Shirima', 'Victoria Mushi', 'Isack Mlelwa', 'Agnes Mkindwa', 'John Kitalima',
]

SUPPLIER_NAMES = [
    'Kariakoo Poultry Farm', 'Temeke Chicken Hub', 'Ilala Fresh Poultry',
    'Mwananyamala Poultry', 'Buguruni Chicken Center', 'Mikocheni Poultry Farm',
    'Sinza Chicken Hub', 'Msimbazi Poultry', 'Kigogo Fresh Poultry', 'Mabibo Chicken Farm',
]

PRODUCT_NAMES = ['Broiler Chicken', 'Layer Chicken', 'Kienyeji Chicken', 'Chicken Eggs (tray)', 'Minced Chicken', 'Chicken Thighs', 'Chicken Wings', 'Whole Chicken']
PRODUCT_PRICES = [15000, 12000, 18000, 8000, 10000, 9000, 8500, 14000]

SUPPLIER_LAT_RANGE = (-6.85, -6.75)
SUPPLIER_LNG_RANGE = (39.20, 39.32)
CUSTOMER_LAT_RANGE = (-6.88, -6.72)
CUSTOMER_LNG_RANGE = (39.20, 39.35)

def rand_date(start_days=180, end_days=1):
    now = timezone.now()
    delta = random.randint(end_days, start_days)
    return now - timedelta(days=delta, hours=random.randint(0, 23), minutes=random.randint(0, 59))

def create_users_and_data():
    print("Creating users and profiles...")
    suppliers = []
    customers = []

    for i, name in enumerate(SUPPLIER_NAMES):
        uname = f"supplier_{i+1}"
        user, _ = User.objects.get_or_create(username=uname, defaults={'first_name': name.split()[0], 'last_name': ' '.join(name.split()[1:])})
        profile, _ = Profile.objects.get_or_create(user=user, defaults={'role': 'supplier'})
        supplier, _ = Supplier.objects.get_or_create(
            user=user,
            defaults={
                'business_name': name,
                'location': f'Dar es Salaam, Tanzania',
                'latitude': random.uniform(*SUPPLIER_LAT_RANGE),
                'longitude': random.uniform(*SUPPLIER_LNG_RANGE),
            }
        )
        suppliers.append(supplier)

    for i, name in enumerate(CUSTOMER_NAMES):
        uname = f"customer_{i+1}"
        user, _ = User.objects.get_or_create(username=uname, defaults={'first_name': name.split()[0], 'last_name': ' '.join(name.split()[1:])})
        profile, _ = Profile.objects.get_or_create(user=user, defaults={'role': 'customer'})
        customer, _ = Customer.objects.get_or_create(
            user=user,
            defaults={
                'phone': f'+2557{random.randint(10000000, 99999999)}',
                'location': f'Dar es Salaam, Tanzania',
                'latitude': random.uniform(*CUSTOMER_LAT_RANGE),
                'longitude': random.uniform(*CUSTOMER_LNG_RANGE),
            }
        )
        customers.append(customer)

    print(f"  {len(suppliers)} suppliers, {len(customers)} customers")
    return suppliers, customers

def create_products():
    print("Creating products...")
    products = []
    for name, price in zip(PRODUCT_NAMES, PRODUCT_PRICES):
        product, _ = Product.objects.get_or_create(
            name=name,
            defaults={
                'description': f'Fresh {name.lower()} from local farms',
                'price': price,
                'unit': 'kg' if 'egg' not in name.lower() else 'tray',
                'stock': random.randint(50, 200),
            }
        )
        products.append(product)
    print(f"  {len(products)} products")
    return products

def create_transactions(suppliers, customers, products):
    print("Creating 500 transactions...")
    orders_created = 0
    deliveries_created = 0

    for i in range(500):
        customer = random.choice(customers)
        supplier = random.choice(suppliers)
        order_date = rand_date(180, 1)

        status_choices = ['delivered', 'delivered', 'delivered', 'delivered', 'pending', 'in_progress', 'cancelled']
        status = random.choice(status_choices)
        num_items = random.randint(1, 4)
        total = 0

        order = Order.objects.create(
            customer=customer.user,
            supplier=supplier.user,
            status=status,
            created_at=order_date,
        )

        for _ in range(num_items):
            product = random.choice(products)
            qty = random.randint(1, 5)
            price = product.price * qty
            total += price
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=qty,
                unit_price=product.price,
                total_price=price,
            )

        order.total_amount = total
        order.save()
        orders_created += 1

        if status in ('delivered', 'in_progress'):
            Delivery.objects.create(
                order=order,
                delivery_person=supplier.user,
                status='completed' if status == 'delivered' else 'in_transit',
                created_at=order_date + timedelta(hours=random.randint(1, 6)),
            )
            deliveries_created += 1

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/500 transactions created...")

    print(f"  {orders_created} orders, {deliveries_created} deliveries created")

if __name__ == '__main__':
    suppliers, customers = create_users_and_data()
    products = create_products()
    create_transactions(suppliers, customers, products)
    print("Done! 500 transactions seeded.")

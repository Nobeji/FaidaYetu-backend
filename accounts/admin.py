from django.contrib import admin
from .models import Profile, Supplier, Customer, DeliveryPerson, Product, Order, OrderItem

admin.site.register(Profile)
admin.site.register(Supplier)
admin.site.register(Customer)
admin.site.register(DeliveryPerson)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(OrderItem)

from django.urls import path
from . import views

urlpatterns = [
    path('api/deliveries/', views.DeliveryListCreateView.as_view(), name='delivery-list'),
    path('api/deliveries/<int:pk>/', views.DeliveryDetailView.as_view(), name='delivery-detail'),
    path('api/deliveries/<int:delivery_id>/log-location/', views.LogLocationView.as_view(), name='log-location'),
    path('api/deliveries/<int:delivery_id>/latest-location/', views.LatestLocationView.as_view(), name='latest-location'),
]

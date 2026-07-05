from django.urls import path
from . import views, admin_views
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('api/auth/register/', views.RegisterView.as_view(), name='register'),
    path('api/auth/login/', views.LoginView.as_view(), name='login'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/profile/', views.ProfileView.as_view(), name='profile'),

    path('api/suppliers/', views.SupplierListView.as_view(), name='supplier-list'),
    path('api/suppliers/<int:pk>/', views.SupplierDetailView.as_view(), name='supplier-detail'),
    path('api/suppliers/<int:supplier_id>/products/', views.ProductBySupplierView.as_view(), name='supplier-products'),

    path('api/products/', views.ProductListView.as_view(), name='product-list'),
    path('api/products/<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),

    path('api/orders/', views.OrderListCreateView.as_view(), name='order-list'),
    path('api/orders/<int:pk>/', views.OrderDetailView.as_view(), name='order-detail'),
    path('api/orders/<int:order_id>/assign-delivery/', views.AssignDeliveryView.as_view(), name='assign-delivery'),

    path('api/delivery-persons/', views.DeliveryPersonListView.as_view(), name='delivery-person-list'),

    # Admin endpoints
    path('api/admin/dashboard/', admin_views.AdminDashboardView.as_view(), name='admin-dashboard'),
    path('api/admin/demand-analysis/', admin_views.DemandAnalysisView.as_view(), name='admin-demand'),
    path('api/admin/heat-map/', admin_views.HeatMapDataView.as_view(), name='admin-heatmap'),
    path('api/admin/sales-prediction/', admin_views.SalesPredictionView.as_view(), name='admin-prediction'),
    path('api/admin/performance/', admin_views.PerformanceMetricsView.as_view(), name='admin-performance'),
    path('api/admin/suppliers/', admin_views.AdminListSuppliersView.as_view(), name='admin-suppliers'),
    path('api/admin/customers/', admin_views.AdminListCustomersView.as_view(), name='admin-customers'),
    path('api/admin/rfm-segmentation/', admin_views.RFMSegmentationView.as_view(), name='admin-rfm'),
    path('api/admin/churn-prediction/', admin_views.ChurnPredictionView.as_view(), name='admin-churn'),
    path('api/admin/anomaly-detection/', admin_views.AnomalyDetectionView.as_view(), name='admin-anomaly'),
    path('api/admin/route-optimization/', admin_views.RouteOptimizationView.as_view(), name='admin-route'),
    path('api/admin/inventory-forecast/', admin_views.InventoryForecastView.as_view(), name='admin-inventory'),
    path('api/admin/cohort-analysis/', admin_views.CohortAnalysisView.as_view(), name='admin-cohort'),
    path('api/admin/trend-insights/', admin_views.TrendInsightsView.as_view(), name='admin-trends'),
    path('api/admin/model-evaluation/', admin_views.ModelEvaluationView.as_view(), name='admin-model-eval'),
    path('api/admin/what-if-simulator/', admin_views.WhatIfSimulatorView.as_view(), name='admin-whatif'),
    path('api/admin/network-graph/', admin_views.NetworkGraphView.as_view(), name='admin-network'),
    path('api/admin/<str:model_type>/', admin_views.AdminListView.as_view(), name='admin-list'),

    path('api/dashboard/supplier/<int:supplier_id>/', views.SupplierDashboardView.as_view(), name='supplier-dashboard'),
    path('api/dashboard/customer/<int:customer_id>/', views.CustomerDashboardView.as_view(), name='customer-dashboard'),
    path('api/dashboard/delivery/<int:delivery_id>/', views.DeliveryDashboardView.as_view(), name='delivery-dashboard'),
    path('api/stats/', views.StatsView.as_view(), name='stats'),
]

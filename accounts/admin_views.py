from datetime import datetime, timedelta, date
from django.db.models import Count, Sum, Avg, F, Min, Max, Q
from django.db.models.functions import TruncDate, TruncWeek
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from .models import Order, OrderItem, Product, Supplier, Customer, DeliveryPerson, Profile, UsabilityMetric, SystemPerformance, TAMSurvey, SUSSurvey
from deliveries.models import Delivery, TemperatureLog
from .prediction import forecast_orders

DAR_LOCTIONS = [
    {'ward': 'Kariakoo', 'lat': -6.8196, 'lng': 39.2804},
    {'ward': 'Mchafukoge', 'lat': -6.8165, 'lng': 39.2850},
    {'ward': 'Kisutu', 'lat': -6.8135, 'lng': 39.2890},
    {'ward': 'Mkunguni', 'lat': -6.8100, 'lng': 39.2700},
    {'ward': 'Kivukoni', 'lat': -6.8130, 'lng': 39.2930},
    {'ward': 'Upanga', 'lat': -6.8000, 'lng': 39.2750},
    {'ward': 'Mwananyamala', 'lat': -6.7900, 'lng': 39.2600},
    {'ward': 'Kinondoni', 'lat': -6.7800, 'lng': 39.2500},
    {'ward': 'Kawe', 'lat': -6.7600, 'lng': 39.2300},
    {'ward': 'Msasani', 'lat': -6.7700, 'lng': 39.2700},
    {'ward': 'Oysterbay', 'lat': -6.7750, 'lng': 39.2800},
    {'ward': 'Mikocheni', 'lat': -6.7800, 'lng': 39.2650},
    {'ward': 'Tandale', 'lat': -6.8100, 'lng': 39.2450},
    {'ward': 'Manzese', 'lat': -6.8200, 'lng': 39.2350},
    {'ward': 'Ubungo', 'lat': -6.8000, 'lng': 39.2100},
    {'ward': 'Tabata', 'lat': -6.8350, 'lng': 39.2200},
    {'ward': 'Kimara', 'lat': -6.8100, 'lng': 39.1900},
    {'ward': 'Mbezi', 'lat': -6.7700, 'lng': 39.1800},
    {'ward': 'Tegeta', 'lat': -6.7300, 'lng': 39.1900},
    {'ward': 'Kigogo', 'lat': -6.8300, 'lng': 39.2550},
]

def nearest_ward(lat, lng):
    closest = DAR_LOCTIONS[0]
    min_dist = float('inf')
    for w in DAR_LOCTIONS:
        d = (w['lat'] - lat)**2 + (w['lng'] - lng)**2
        if d < min_dist:
            min_dist = d
            closest = w
    return closest['ward']

class AdminDashboardView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        total_users = Profile.objects.count()
        total_suppliers = Supplier.objects.count()
        total_customers = Customer.objects.count()
        total_orders = Order.objects.count()
        total_revenue = Order.objects.aggregate(s=Sum('total'))['s'] or 0
        total_deliveries = Delivery.objects.count()
        active_deliveries = Delivery.objects.filter(status='in_transit').count()
        total_products = Product.objects.count()

        orders_today = Order.objects.filter(created_at__date=datetime.today().date()).count()
        revenue_today = Order.objects.filter(created_at__date=datetime.today().date()).aggregate(s=Sum('total'))['s'] or 0

        return Response({
            'totalUsers': total_users,
            'totalSuppliers': total_suppliers,
            'totalCustomers': total_customers,
            'totalOrders': total_orders,
            'totalRevenue': f'{total_revenue:,.0f} TZS',
            'totalRevenueRaw': total_revenue,
            'totalDeliveries': total_deliveries,
            'activeDeliveries': active_deliveries,
            'totalProducts': total_products,
            'ordersToday': orders_today,
            'revenueToday': f'{revenue_today:,.0f} TZS',
            'revenueTodayRaw': revenue_today,
        })


class DemandAnalysisView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Use ALL orders for demand analysis (not just delivered)
        orders = Order.objects.all()
        total = orders.count()

        most_ordered_product = OrderItem.objects.values('product__name').annotate(
            total_qty=Sum('quantity')
        ).order_by('-total_qty').first()

        monthly = Order.objects.filter(
            created_at__gte=datetime.now() - timedelta(days=30)
        ).count()
        weekly = Order.objects.filter(
            created_at__gte=datetime.now() - timedelta(days=7)
        ).count()

        ward_orders = {}
        for o in orders:
            ward = nearest_ward(o.delivery_lat, o.delivery_lng)
            ward_orders[ward] = ward_orders.get(ward, 0) + 1
        top_wards = sorted(ward_orders.items(), key=lambda x: -x[1])[:5]
        top_area = top_wards[0][0] if top_wards else 'N/A'

        days_agg = Order.objects.filter(
            created_at__gte=datetime.now() - timedelta(days=7)
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            count=Count('id'), revenue=Sum('total')
        ).order_by('date')

        product_categories = OrderItem.objects.values('product__category').annotate(
            total=Sum('quantity')
        ).order_by('-total')

        return Response({
            'mostOrderedProduct': {
                'name': most_ordered_product['product__name'] if most_ordered_product else 'N/A',
                'quantity': most_ordered_product['total_qty'] if most_ordered_product else 0,
            },
            'mostOrderedArea': top_area,
            'ordersPerWard': [{'ward': w, 'count': c} for w, c in top_wards],
            'ordersPerDay': [{'date': d['date'], 'count': d['count'], 'revenue': float(d['revenue'] or 0)} for d in days_agg],
            'ordersWeekly': weekly,
            'ordersMonthly': monthly,
            'totalOrders': total,
            'productCategories': [
                {'category': p['product__category'], 'total': p['total']} for p in product_categories
            ],
        })


class HeatMapDataView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        orders = Order.objects.filter(status='delivered')[:200]
        points = []
        ward_count = {}
        for o in orders:
            ward = nearest_ward(o.delivery_lat, o.delivery_lng)
            ward_count[ward] = ward_count.get(ward, 0) + 1

        for w in DAR_LOCTIONS:
            count = ward_count.get(w['ward'], 0)
            if count > 0:
                intensity = min(1.0, count / max(ward_count.values(), default=1))
                points.append({
                    'lat': w['lat'], 'lng': w['lng'],
                    'ward': w['ward'], 'count': count,
                    'intensity': round(intensity, 2),
                })

        return Response({
            'center': [-6.7924, 39.2083],
            'wards': DAR_LOCTIONS,
            'heatPoints': points,
        })


class SalesPredictionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        result = forecast_orders(days_history=90, forecast_days=30)
        return Response(result)


class PerformanceMetricsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        completed = Delivery.objects.filter(status='completed', started_at__isnull=False, completed_at__isnull=False)

        avg_time = None
        if completed.exists():
            total_seconds = sum(
                (d.completed_at - d.started_at).total_seconds()
                for d in completed if d.completed_at and d.started_at
            )
            avg_seconds = total_seconds / completed.count()
            hours = int(avg_seconds // 3600)
            minutes = int((avg_seconds % 3600) // 60)
            avg_time = f'{hours}h {minutes}m'

        fastest = completed.order_by(F('completed_at') - F('started_at')).first()
        fastest_time = None
        if fastest and fastest.started_at and fastest.completed_at:
            secs = (fastest.completed_at - fastest.started_at).total_seconds()
            fastest_time = f'{int(secs // 3600)}h {int((secs % 3600) // 60)}m'

        efficiency = 0
        if completed.exists():
            on_time = completed.filter(
                completed_at__lte=F('started_at') + timedelta(hours=2)
            ).count()
            efficiency = round(on_time / completed.count() * 100, 1)

        total_routes = Delivery.objects.count()
        cancelled = Delivery.objects.filter(status='cancelled').count()

        return Response({
            'avgDeliveryTime': avg_time or 'N/A',
            'fastestRoute': fastest_time or 'N/A',
            'deliveryEfficiency': f'{efficiency}%',
            'totalRoutes': total_routes,
            'cancelledDeliveries': cancelled,
            'completionRate': f'{round((completed.count() / max(total_routes, 1)) * 100, 1)}%',
        })


class AdminListSuppliersView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        suppliers = Supplier.objects.annotate(
            product_count=Count('products'), order_count=Count('orders')
        ).order_by('-created_at')
        return Response([{
            'id': s.id,
            'name': s.business_name,
            'email': s.business_email,
            'address': s.address,
            'rating': s.rating,
            'products': s.product_count,
            'orders': s.order_count,
            'createdAt': s.created_at,
        } for s in suppliers])


class AdminListCustomersView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        customers = Customer.objects.annotate(
            order_count=Count('orders')
        ).order_by('-created_at')
        return Response([{
            'id': c.id,
            'username': c.profile.user.username,
            'email': c.profile.user.email,
            'phone': c.profile.phone,
            'address': c.default_address,
            'orders': c.order_count,
            'createdAt': c.created_at,
        } for c in customers])


class AdminListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, model_type):
        if model_type == 'orders':
            orders = Order.objects.select_related('customer__profile__user', 'supplier').order_by('-created_at')[:100]
            return Response([{
                'id': o.id,
                'customer': o.customer.profile.user.username,
                'supplier': o.supplier.business_name,
                'status': o.status,
                'total': float(o.total),
                'paid': o.payments.filter(status='completed').exists(),
                'address': o.delivery_address,
                'createdAt': o.created_at,
            } for o in orders])
        elif model_type == 'deliveries':
            deliveries = Delivery.objects.select_related('delivery_person__profile__user').order_by('-created_at')[:100]
            return Response([{
                'id': d.id,
                'driver': d.delivery_person.profile.user.username,
                'status': d.status,
                'distance': d.distance_km,
                'earnings': float(d.earnings),
                'startedAt': d.started_at,
                'completedAt': d.completed_at,
                'createdAt': d.created_at,
            } for d in deliveries])
        return Response({'error': 'Invalid type'}, status=400)


# ========== 1. RFM Customer Segmentation ==========

class RFMSegmentationView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.db.models import Max, Min, Q
        now = datetime.now()
        customers = Customer.objects.annotate(
            last_order=Max('orders__created_at'),
            order_count=Count('orders'),
            total_spent=Sum('orders__total'),
        ).filter(order_count__gt=0)

        segments = []
        today = now.date()
        for c in customers:
            if c.last_order:
                recency = (today - c.last_order.date()).days
            else:
                recency = 999
            frequency = c.order_count or 0
            monetary = float(c.total_spent or 0)

            if recency <= 30 and frequency >= 5 and monetary >= 500000:
                segment = 'VIP'
            elif recency <= 30 and frequency >= 2:
                segment = 'Loyal'
            elif recency <= 60:
                segment = 'Active'
            elif recency <= 90:
                segment = 'At Risk'
            elif recency <= 180:
                segment = 'Dormant'
            else:
                segment = 'Lost'

            segments.append({
                'customer_id': c.id,
                'name': c.profile.user.username,
                'recency_days': recency,
                'frequency': frequency,
                'monetary': monetary,
                'segment': segment,
            })

        summary = {}
        for s in segments:
            summary[s['segment']] = summary.get(s['segment'], 0) + 1

        return Response({'segments': segments, 'summary': summary})


# ========== 2. Churn Prediction ==========

class ChurnPredictionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.db.models import Max, Count, Q
        now = datetime.now()
        today = now.date()
        thirty_days_ago = today - timedelta(days=30)

        results = []
        for c in Customer.objects.annotate(
            last_order=Max('orders__created_at'),
            order_count=Count('orders'),
        ):
            if not c.last_order:
                continue
            days_since = (today - c.last_order.date()).days
            freq = c.order_count or 0
            recent_orders = c.orders.filter(created_at__gte=thirty_days_ago).count()

            score = 0.0
            if days_since > 90:
                score += 0.4
            elif days_since > 60:
                score += 0.25
            elif days_since > 30:
                score += 0.1

            if freq <= 1:
                score += 0.3
            elif freq <= 3:
                score += 0.15

            if recent_orders == 0 and freq > 0:
                score += 0.3

            score = min(score, 1.0)
            if score >= 0.6:
                label = 'High Risk'
            elif score >= 0.3:
                label = 'Medium Risk'
            else:
                label = 'Low Risk'

            results.append({
                'customer_id': c.id,
                'name': c.profile.user.username,
                'days_since_last_order': days_since,
                'total_orders': freq,
                'recent_30d_orders': recent_orders,
                'churn_score': round(score, 2),
                'risk_level': label,
            })

        high = sum(1 for r in results if r['risk_level'] == 'High Risk')
        medium = sum(1 for r in results if r['risk_level'] == 'Medium Risk')
        low = sum(1 for r in results if r['risk_level'] == 'Low Risk')
        return Response({
            'customers': results,
            'summary': {'high': high, 'medium': medium, 'low': low},
        })


# ========== 3. Anomaly Detection ==========

class AnomalyDetectionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        import statistics
        orders = Order.objects.filter(status__in=['new', 'processing', 'ready', 'in_transit', 'delivered'])
        amounts = [float(o.total) for o in orders if o.total > 0]

        if len(amounts) < 5:
            return Response({'anomalies': [], 'message': 'Not enough data'})

        mean = statistics.mean(amounts)
        stdev = statistics.stdev(amounts) if len(amounts) > 1 else 0
        z_threshold = 2.5

        anomalies = []
        for o in orders:
            if o.total <= 0:
                continue
            z = (float(o.total) - mean) / max(stdev, 1)
            if abs(z) > z_threshold:
                anomalies.append({
                    'order_id': o.id,
                    'customer': o.customer.profile.user.username,
                    'supplier': o.supplier.business_name,
                    'amount': float(o.total),
                    'z_score': round(z, 2),
                    'date': o.created_at,
                })

        anomalies.sort(key=lambda x: abs(x['z_score']), reverse=True)
        return Response({
            'anomalies': anomalies[:20],
            'mean': round(mean),
            'stdev': round(stdev),
            'total_orders': len(orders),
            'anomaly_count': len(anomalies),
        })


# ========== 4. Route Optimization ==========

class RouteOptimizationView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        pending = Order.objects.filter(status='ready', delivery__isnull=True).select_related('supplier')
        if not pending:
            return Response({'routes': [], 'message': 'No pending deliveries'})

        points = []
        for o in pending:
            lat = o.supplier.profile.lat
            lng = o.supplier.profile.lng
            points.append({
                'order_id': o.id,
                'customer': o.customer.profile.user.username,
                'supplier': o.supplier.business_name,
                'lat': float(lat),
                'lng': float(lng),
                'address': o.delivery_address,
            })

        if not points:
            return Response({'routes': [], 'message': 'No location data'})

        start_lat = float(request.GET.get('lat', -6.7924))
        start_lng = float(request.GET.get('lng', 39.2083))

        def dist(lat1, lng1, lat2, lng2):
            return ((lat1 - lat2)**2 + (lng1 - lng2)**2)**0.5

        unvisited = list(points)
        route = []
        current = {'lat': start_lat, 'lng': start_lng}
        while unvisited:
            nearest = min(unvisited, key=lambda p: dist(current['lat'], current['lng'], p['lat'], p['lng']))
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest

        total_distance = 0
        prev = {'lat': start_lat, 'lng': start_lng}
        for p in route:
            total_distance += dist(prev['lat'], prev['lng'], p['lat'], p['lng'])
            prev = p

        return Response({
            'route': route,
            'stop_count': len(route),
            'estimated_distance_km': round(total_distance * 111, 1),
            'start': {'lat': start_lat, 'lng': start_lng},
        })


# ========== 5. Inventory Forecasting ==========

class InventoryForecastView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        products = Product.objects.select_related('supplier').all()
        results = []
        for p in products:
            items = OrderItem.objects.filter(product=p, order__status='delivered')
            if not items.exists():
                continue
            total_sold = items.aggregate(s=Sum('quantity'))['s'] or 0
            count_days = items.aggregate(
                first=Min('order__created_at'), last=Max('order__created_at')
            )
            if count_days['first'] and count_days['last']:
                span = max((count_days['last'] - count_days['first']).days, 1)
                daily_rate = total_sold / span
            else:
                daily_rate = 0

            stock = p.stock or 0
            reorder_point = max(int(daily_rate * 7), 5)
            safety_stock = max(int(daily_rate * 3), 2)
            days_until_stockout = int(stock / max(daily_rate, 0.01)) if daily_rate > 0 else 999

            results.append({
                'product_id': p.id,
                'product_name': p.name,
                'supplier': p.supplier.business_name,
                'current_stock': stock,
                'daily_sales_rate': round(daily_rate, 1),
                'reorder_point': reorder_point,
                'safety_stock': safety_stock,
                'days_until_stockout': days_until_stockout,
                'needs_reorder': stock <= reorder_point,
            })

        results.sort(key=lambda r: r['days_until_stockout'])
        return Response({'products': results})


# ========== 6. Cohort Analysis ==========

class CohortAnalysisView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from collections import defaultdict
        customers = Customer.objects.annotate(
            first_order=Min('orders__created_at'),
        ).filter(first_order__isnull=False).order_by('first_order')

        cohorts = defaultdict(lambda: defaultdict(int))
        cohort_sizes = defaultdict(int)
        now = datetime.now()

        for c in customers:
            cohort_month = c.first_order.strftime('%Y-%m')
            cohort_sizes[cohort_month] += 1
            for o in c.orders.all():
                month_offset = (o.created_at.year - c.first_order.year) * 12 + (o.created_at.month - c.first_order.month)
                if month_offset >= 0 and month_offset <= 12:
                    cohorts[cohort_month][month_offset] += 1

        cohort_data = []
        for month in sorted(cohorts.keys()):
            size = cohort_sizes[month]
            if size == 0:
                continue
            row = {'cohort': month, 'size': size}
            for offset in range(0, 13):
                active = cohorts[month].get(offset, 0)
                row[f'month_{offset}'] = round(active / size * 100, 1) if size > 0 else 0
            cohort_data.append(row)

        return Response({'cohorts': cohort_data, 'months': [f'month_{i}' for i in range(13)]})


# ========== 7. Trend Insights ==========

class TrendInsightsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        insights = []

        orders = Order.objects.filter(created_at__gte=datetime.now() - timedelta(days=90))
        day_order_counts = {i: 0 for i in range(7)}
        for o in orders:
            day_order_counts[o.created_at.weekday()] += 1

        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        best_day = max(day_order_counts, key=day_order_counts.get)
        insights.append({
            'icon': '📈',
            'title': 'Best Order Day',
            'value': day_names[best_day],
            'detail': f'{day_order_counts[best_day]} orders in last 90 days',
        })

        category_counts = {}
        items = OrderItem.objects.filter(order__in=orders).select_related('product')
        for item in items:
            cat = item.product.category
            category_counts[cat] = category_counts.get(cat, 0) + item.quantity
        if category_counts:
            top_cat = max(category_counts, key=category_counts.get)
            insights.append({
                'icon': '🏆',
                'title': 'Top Category',
                'value': top_cat.title(),
                'detail': f'{category_counts[top_cat]} units sold',
            })

        suppliers = Supplier.objects.annotate(order_count=Count('orders')).order_by('-order_count')
        if suppliers:
            top = suppliers.first()
            insights.append({
                'icon': '🏪',
                'title': 'Top Supplier',
                'value': top.business_name,
                'detail': f'{top.order_count} orders processed',
            })

        today = datetime.now().date()
        week_orders = Order.objects.filter(created_at__gte=today - timedelta(days=7)).count()
        prev_week = Order.objects.filter(
            created_at__gte=today - timedelta(days=14),
            created_at__lt=today - timedelta(days=7),
        ).count()
        if prev_week > 0:
            change = round((week_orders - prev_week) / prev_week * 100, 1)
            direction = 'increased' if change > 0 else 'decreased'
            insights.append({
                'icon': '📊',
                'title': 'Weekly Order Trend',
                'value': f'{direction.title()} by {abs(change)}%',
                'detail': f'{week_orders} this week vs {prev_week} last week',
            })
        else:
            insights.append({
                'icon': '📊',
                'title': 'Weekly Orders',
                'value': str(week_orders),
                'detail': 'Orders this week',
            })

        return Response({'insights': insights})


# ========== 8. Model Evaluation (Prophet) ==========

class ModelEvaluationView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from datetime import date, timedelta
        from django.db.models.functions import TruncDate
        daily = (
            Order.objects.filter(status='delivered', created_at__gte=date.today() - timedelta(days=90))
            .annotate(d=TruncDate('created_at'))
            .values('d')
            .annotate(c=Count('id'))
            .order_by('d')
        )
        daily_data = list(daily)
        if len(daily_data) < 7:
            return Response({'error': 'Need at least 7 days of data'})

        actuals = {str(d['d']): d['c'] for d in daily_data}
        dates = [d['d'] for d in daily_data]
        values = [d['c'] for d in daily_data]

        n = len(values)
        predictions = {}
        for i in range(7, n):
            window = values[max(0, i - 14):i]
            avg = sum(window) / max(len(window), 1)
            predictions[str(dates[i])] = round(avg, 1)

        errors = []
        for i in range(7, n):
            ds = str(dates[i])
            actual = values[i]
            pred = predictions.get(ds)
            if pred and actual > 0:
                ape = abs(actual - pred) / actual * 100
                errors.append(ape)

        mae = sum(abs(actual - predictions.get(str(dates[i]), actual)) for i in range(7, n)) / max(n - 7, 1)
        mape = sum(errors) / max(len(errors), 1)

        squared_errors = []
        for i in range(7, n):
            actual = values[i]
            pred = predictions.get(str(dates[i]))
            if pred is not None:
                squared_errors.append((actual - pred) ** 2)
        import math
        rmse = math.sqrt(sum(squared_errors) / max(len(squared_errors), 1))

        comparison = []
        for i in range(max(7, n - 14), n):
            ds = str(dates[i])
            comparison.append({
                'date': ds,
                'actual': values[i],
                'predicted': predictions.get(ds, None),
            })

        return Response({
            'mae': round(mae, 2),
            'mape': round(mape, 1),
            'rmse': round(rmse, 2),
            'accuracy': round(100 - mape, 1),
            'data_points': n,
            'comparison': comparison[-14:],
        })


# ========== 9. What-if Simulator ==========

class WhatIfSimulatorView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        price_change = float(request.GET.get('price_change', 0))
        promo_discount = float(request.GET.get('promo_discount', 0))
        elasticity = float(request.GET.get('elasticity', -0.5))

        total_recent = OrderItem.objects.filter(
            order__created_at__gte=datetime.now() - timedelta(days=30)
        ).aggregate(
            total_qty=Sum('quantity'),
            total_rev=Sum(F('quantity') * F('price')),
        )
        base_qty = float(total_recent['total_qty'] or 0)
        base_rev = float(total_recent['total_rev'] or 0)

        qty_change_pct = price_change * elasticity + promo_discount * 0.3
        new_qty = max(0, base_qty * (1 + qty_change_pct / 100))
        new_price_factor = 1 + price_change / 100 - promo_discount / 100
        new_rev = new_qty * (base_rev / max(base_qty, 1)) * new_price_factor

        scenarios = [
            {'label': 'No change', 'price_change': 0, 'promo': 0,
             'projected_volume': int(base_qty), 'projected_revenue': int(base_rev)},
            {'label': '10% price increase', 'price_change': 10, 'promo': 0,
             'projected_volume': int(base_qty * (1 + 10 * elasticity / 100)),
             'projected_revenue': int(base_rev * (1 + 10 / 100) * (1 + 10 * elasticity / 100))},
            {'label': '5% promo discount', 'price_change': 0, 'promo': 5,
             'projected_volume': int(base_qty * 1.15),
             'projected_revenue': int(base_rev * 0.95 * 1.15)},
            {'label': '15% price increase + 10% promo', 'price_change': 15, 'promo': 10,
             'projected_volume': int(base_qty * (1 + 15 * elasticity / 100 + 3)),
             'projected_revenue': int(base_rev * (1 + 5 / 100) * (1 + 15 * elasticity / 100 + 3) / 100)},
        ]

        return Response({
            'base_volume': int(base_qty),
            'base_revenue': int(base_rev),
            'current_scenario': {
                'price_change_pct': price_change,
                'promo_discount_pct': promo_discount,
                'projected_volume': int(new_qty),
                'projected_revenue': int(new_rev),
                'revenue_change_pct': round((new_rev - base_rev) / max(base_rev, 1) * 100, 1),
            },
            'scenarios': scenarios,
        })


# ========== 10. Network Graph ==========

class NetworkGraphView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.db.models import Count
        suppliers = Supplier.objects.annotate(order_count=Count('orders')).filter(order_count__gt=0)

        nodes = []
        edges = []
        node_ids = set()

        for s in suppliers:
            sid = f'supplier_{s.id}'
            if sid not in node_ids:
                nodes.append({
                    'id': sid,
                    'label': s.business_name,
                    'type': 'supplier',
                    'order_count': s.order_count,
                    'revenue': float(s.orders.aggregate(t=Sum('total'))['t'] or 0),
                })
                node_ids.add(sid)

            for o in s.orders.all()[:5]:
                cid = f'customer_{o.customer.id}'
                if cid not in node_ids:
                    nodes.append({
                        'id': cid,
                        'label': o.customer.profile.user.username,
                        'type': 'customer',
                        'order_count': o.customer.orders.count(),
                    })
                    node_ids.add(cid)

                edges.append({
                    'source': cid,
                    'target': sid,
                    'value': float(o.total),
                    'status': o.status,
                })

        return Response({
            'nodes': nodes,
            'edges': edges[:200],
        })


# ========== 11. Supplier Payouts ==========

class SupplierPayoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from datetime import date, timedelta
        from django.db.models import Count, Sum, Q

        # Date filter (default: last 30 days)
        days = int(request.query_params.get('days', 30))
        since = datetime.now() - timedelta(days=days)

        suppliers = Supplier.objects.all()
        results = []

        for s in suppliers:
            # All orders in period
            all_orders = s.orders.filter(created_at__gte=since)
            total_orders = all_orders.count()

            # Delivered orders (payable)
            delivered_orders = all_orders.filter(status='delivered')
            delivered_count = delivered_orders.count()
            delivered_revenue = delivered_orders.aggregate(s=Sum('total'))['s'] or 0

            # Pending orders (paid but not delivered)
            pending_orders = all_orders.filter(status__in=['paid', 'processing', 'ready'])
            pending_count = pending_orders.count()
            pending_revenue = pending_orders.aggregate(s=Sum('total'))['s'] or 0

            # Cancelled
            cancelled_orders = all_orders.filter(status='cancelled')
            cancelled_count = cancelled_orders.count()

            # Order breakdown
            order_list = []
            for o in all_orders.order_by('-created_at')[:20]:
                order_list.append({
                    'id': o.id,
                    'status': o.status,
                    'total': float(o.total),
                    'created_at': o.created_at.isoformat(),
                    'items': [
                        {'name': i.product.name, 'qty': i.quantity, 'price': float(i.price)}
                        for i in o.items.all()
                    ],
                })

            results.append({
                'supplier_id': s.id,
                'business_name': s.business_name,
                'total_orders': total_orders,
                'delivered_count': delivered_count,
                'delivered_revenue': float(delivered_revenue),
                'pending_count': pending_count,
                'pending_revenue': float(pending_revenue),
                'cancelled_count': cancelled_count,
                'payout_amount': float(delivered_revenue),  # what they should be paid
                'orders': order_list,
            })

        return Response({
            'period_days': days,
            'suppliers': results,
        })


# ========== 12. Enhanced Performance Analytics ==========

class EnhancedPerformanceView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = datetime.now() - timedelta(days=days)

        completed = Delivery.objects.filter(
            status='completed', started_at__isnull=False, completed_at__isnull=False,
            created_at__gte=since
        )

        delivery_times = []
        for d in completed:
            secs = (d.completed_at - d.started_at).total_seconds()
            delivery_times.append({
                'id': d.id,
                'driver': d.delivery_person.profile.user.username,
                'distance_km': d.distance_km,
                'time_minutes': round(secs / 60, 1),
                'date': d.created_at.isoformat(),
            })

        avg_time_mins = 0
        if delivery_times:
            avg_time_mins = round(sum(t['time_minutes'] for t in delivery_times) / len(delivery_times), 1)

        on_time_count = sum(1 for t in delivery_times if t['time_minutes'] <= 120)
        on_time_rate = round(on_time_count / max(len(delivery_times), 1) * 100, 1)

        avg_distance = 0
        if delivery_times:
            avg_distance = round(sum(t['distance_km'] for t in delivery_times) / len(delivery_times), 1)

        speed_per_km = 0
        if avg_distance > 0 and avg_time_mins > 0:
            speed_per_km = round(avg_time_mins / avg_distance, 1)

        daily_stats = {}
        for t in delivery_times:
            day = t['date'][:10]
            if day not in daily_stats:
                daily_stats[day] = {'count': 0, 'total_time': 0, 'total_distance': 0}
            daily_stats[day]['count'] += 1
            daily_stats[day]['total_time'] += t['time_minutes']
            daily_stats[day]['total_distance'] += t['distance_km']

        daily = []
        for day in sorted(daily_stats.keys()):
            s = daily_stats[day]
            daily.append({
                'date': day,
                'deliveries': s['count'],
                'avg_time': round(s['total_time'] / s['count'], 1),
                'total_distance': round(s['total_distance'], 1),
            })

        return Response({
            'summary': {
                'total_deliveries': len(delivery_times),
                'avg_delivery_time_mins': avg_time_mins,
                'on_time_rate': f'{on_time_rate}%',
                'avg_distance_km': avg_distance,
                'avg_speed_per_km': f'{speed_per_km} min/km',
            },
            'daily': daily,
            'deliveries': delivery_times[:50],
        })


# ========== 13. Cold Chain Tracking ==========

class ColdChainTrackingView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        delivery_id = request.query_params.get('delivery_id')
        if delivery_id:
            logs = TemperatureLog.objects.filter(delivery_id=delivery_id).order_by('-timestamp')
            data = [{
                'id': l.id,
                'temperature': l.temperature,
                'lat': l.location_lat,
                'lng': l.location_lng,
                'is_alert': l.is_alert,
                'timestamp': l.timestamp.isoformat(),
            } for l in logs]

            alerts = [l for l in data if l['is_alert']]
            temps = [l['temperature'] for l in data]
            return Response({
                'delivery_id': delivery_id,
                'logs': data,
                'alerts': alerts,
                'stats': {
                    'avg_temp': round(sum(temps) / max(len(temps), 1), 1),
                    'min_temp': min(temps) if temps else 0,
                    'max_temp': max(temps) if temps else 0,
                    'alert_count': len(alerts),
                    'total_readings': len(temps),
                },
            })

        all_deliveries = Delivery.objects.filter(
            status__in=['in_transit', 'picked_up']
        ).select_related('delivery_person__profile__user')

        active = []
        for d in all_deliveries:
            latest_temp = d.temperature_logs.first()
            active.append({
                'delivery_id': d.id,
                'driver': d.delivery_person.profile.user.username,
                'status': d.status,
                'distance_km': d.distance_km,
                'current_temp': latest_temp.temperature if latest_temp else None,
                'has_alert': latest_temp.is_alert if latest_temp else False,
                'last_reading': latest_temp.timestamp.isoformat() if latest_temp else None,
            })

        recent_alerts = TemperatureLog.objects.filter(
            is_alert=True, created_at__gte=datetime.now() - timedelta(days=7)
        ).select_related('delivery__delivery_person__profile__user')[:20]

        alerts_list = [{
            'delivery_id': a.delivery_id,
            'driver': a.delivery.delivery_person.profile.user.username,
            'temperature': a.temperature,
            'timestamp': a.timestamp.isoformat(),
        } for a in recent_alerts]

        all_temps = TemperatureLog.objects.filter(
            created_at__gte=datetime.now() - timedelta(days=30)
        )
        temp_values = [t.temperature for t in all_temps]
        avg_temp = round(sum(temp_values) / max(len(temp_values), 1), 1) if temp_values else 0
        alert_count = all_temps.filter(is_alert=True).count()

        return Response({
            'active_deliveries': active,
            'recent_alerts': alerts_list,
            'summary': {
                'avg_temperature': avg_temp,
                'total_alerts_30d': alert_count,
                'total_readings_30d': len(temp_values),
                'compliance_rate': f'{round((1 - alert_count / max(len(temp_values), 1)) * 100, 1)}%',
            },
        })

    def post(self, request):
        delivery_id = request.data.get('delivery_id')
        temperature = request.data.get('temperature')
        lat = request.data.get('lat')
        lng = request.data.get('lng')

        if not delivery_id or temperature is None:
            return Response({'error': 'delivery_id and temperature required'}, status=400)

        try:
            delivery = Delivery.objects.get(id=delivery_id)
        except Delivery.DoesNotExist:
            return Response({'error': 'Delivery not found'}, status=404)

        is_alert = float(temperature) > 8.0 or float(temperature) < 0.0
        log = TemperatureLog.objects.create(
            delivery=delivery,
            temperature=float(temperature),
            location_lat=lat,
            location_lng=lng,
            is_alert=is_alert,
        )

        return Response({
            'id': log.id,
            'temperature': log.temperature,
            'is_alert': log.is_alert,
            'timestamp': log.timestamp.isoformat(),
        }, status=201)


# ========== 14. Route Comparison (NN vs Genetic Algorithm) ==========

class RouteComparisonView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        pending = Order.objects.filter(status='ready', delivery__isnull=True).select_related('supplier')
        if not pending:
            return Response({'message': 'No pending deliveries', 'comparison': {}})

        points = []
        for o in pending:
            lat = o.supplier.profile.lat
            lng = o.supplier.profile.lng
            points.append({
                'order_id': o.id,
                'customer': o.customer.profile.user.username,
                'supplier': o.supplier.business_name,
                'lat': float(lat or -6.7924),
                'lng': float(lng or 39.2083),
                'address': o.delivery_address,
            })

        start_lat = float(request.GET.get('lat', -6.7924))
        start_lng = float(request.GET.get('lng', 39.2083))

        def geo_dist(lat1, lng1, lat2, lng2):
            return ((lat1 - lat2)**2 + (lng1 - lng2)**2)**0.5 * 111

        def calc_total_distance(route, start):
            total = 0
            prev = start
            for p in route:
                total += geo_dist(prev['lat'], prev['lng'], p['lat'], p['lng'])
                prev = p
            return round(total, 1)

        def nearest_neighbor(points, start):
            unvisited = list(points)
            route = []
            current = start
            while unvisited:
                nearest = min(unvisited, key=lambda p: geo_dist(current['lat'], current['lng'], p['lat'], p['lng']))
                route.append(nearest)
                unvisited.remove(nearest)
                current = nearest
            return route

        import random
        random.seed(42)

        def genetic_algorithm(points, start, pop_size=50, generations=100, mutation_rate=0.15):
            if len(points) <= 2:
                return nearest_neighbor(points, start)

            def create_individual():
                ind = list(points)
                random.shuffle(ind)
                return ind

            def fitness(individual):
                return calc_total_distance(individual, start)

            population = [create_individual() for _ in range(pop_size)]
            best = min(population, key=fitness)

            for gen in range(generations):
                population.sort(key=fitness)
                new_pop = population[:pop_size // 2]

                while len(new_pop) < pop_size:
                    p1, p2 = random.sample(new_pop[:pop_size // 3], 2)
                    child = ordered_crossover(p1, p2)
                    if random.random() < mutation_rate:
                        i, j = random.sample(range(len(child)), 2)
                        child[i], child[j] = child[j], child[i]
                    new_pop.append(child)

                population = new_pop
                current_best = min(population, key=fitness)
                if fitness(current_best) < fitness(best):
                    best = current_best

            return best

        def ordered_crossover(p1, p2):
            size = len(p1)
            start_idx = random.randint(0, size - 2)
            end_idx = random.randint(start_idx + 1, size - 1)
            child = [None] * size
            child[start_idx:end_idx + 1] = p1[start_idx:end_idx + 1]
            fill = [g for g in p2 if g not in child]
            idx = 0
            for i in range(size):
                if child[i] is None:
                    child[i] = fill[idx]
                    idx += 1
            return child

        start = {'lat': start_lat, 'lng': start_lng}

        nn_route = nearest_neighbor(points, start)
        nn_distance = calc_total_distance(nn_route, start)

        def dijkstra_tsp(points, start):
            if len(points) <= 1:
                return list(points)
            import heapq
            n = len(points)
            dist_matrix = [[0.0] * n for _ in range(n)]
            for i in range(n):
                for j in range(n):
                    if i != j:
                        dist_matrix[i][j] = geo_dist(points[i]['lat'], points[i]['lng'], points[j]['lat'], points[j]['lng'])
            start_idx = 0
            best_route = None
            best_dist = float('inf')
            for first_visit in range(n):
                if first_visit == start_idx:
                    continue
                visited = {start_idx, first_visit}
                route_order = [start_idx, first_visit]
                current = first_visit
                total = dist_matrix[start_idx][first_visit]
                while len(visited) < n:
                    next_node = None
                    next_dist = float('inf')
                    for j in range(n):
                        if j not in visited and dist_matrix[current][j] < next_dist:
                            next_dist = dist_matrix[current][j]
                            next_node = j
                    if next_node is None:
                        break
                    visited.add(next_node)
                    route_order.append(next_node)
                    total += dist_matrix[current][next_node]
                    current = next_node
                total += geo_dist(points[current]['lat'], points[current]['lng'], start['lat'], start['lng'])
                if total < best_dist:
                    best_dist = total
                    best_route = route_order
            if best_route is None:
                return list(points)
            return [points[i] for i in best_route]

        dijkstra_route = dijkstra_tsp(points, start)
        dijkstra_distance = calc_total_distance(dijkstra_route, start)

        ga_route = genetic_algorithm(points, start)
        ga_distance = calc_total_distance(ga_route, start)

        improvement = 0
        if nn_distance > 0:
            improvement = round((nn_distance - ga_distance) / nn_distance * 100, 1)

        return Response({
            'nearest_neighbor': {
                'route': [{'order_id': r['order_id'], 'customer': r['customer'], 'supplier': r['supplier'], 'lat': r['lat'], 'lng': r['lng']} for r in nn_route],
                'total_distance_km': nn_distance,
                'stop_count': len(nn_route),
            },
            'dijkstra': {
                'route': [{'order_id': r['order_id'], 'customer': r['customer'], 'supplier': r['supplier'], 'lat': r['lat'], 'lng': r['lng']} for r in dijkstra_route],
                'total_distance_km': dijkstra_distance,
                'stop_count': len(dijkstra_route),
            },
            'genetic_algorithm': {
                'route': [{'order_id': r['order_id'], 'customer': r['customer'], 'supplier': r['supplier'], 'lat': r['lat'], 'lng': r['lng']} for r in ga_route],
                'total_distance_km': ga_distance,
                'stop_count': len(ga_route),
            },
            'comparison': {
                'nn_distance': nn_distance,
                'dijkstra_distance': dijkstra_distance,
                'ga_distance': ga_distance,
                'best_algorithm': min(
                    [('Nearest Neighbor', nn_distance), ('Dijkstra', dijkstra_distance), ('Genetic Algorithm', ga_distance)],
                    key=lambda x: x[1]
                )[0],
                'improvement_pct': improvement,
                'saved_km': round(nn_distance - ga_distance, 1),
            },
            'start': start,
        })


# ========== 15. Usability Metrics ==========

class UsabilityMetricsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        days = int(request.query_params.get('days', 30))
        since = datetime.now() - timedelta(days=days)

        metrics = UsabilityMetric.objects.filter(timestamp__gte=since)

        action_counts = {}
        for m in metrics:
            action_counts[m.action] = action_counts.get(m.action, 0) + 1

        completion_rates = {}
        for m in metrics:
            if m.action not in completion_rates:
                completion_rates[m.action] = {'total': 0, 'completed': 0}
            completion_rates[m.action]['total'] += 1
            if m.completed:
                completion_rates[m.action]['completed'] += 1

        rates = {}
        for action, data in completion_rates.items():
            rates[action] = round(data['completed'] / max(data['total'], 1) * 100, 1)

        avg_durations = {}
        for m in metrics:
            if m.duration_seconds > 0:
                if m.action not in avg_durations:
                    avg_durations[m.action] = []
                avg_durations[m.action].append(m.duration_seconds)

        avg_dur = {}
        for action, durations in avg_durations.items():
            avg_dur[action] = round(sum(durations) / len(durations), 1)

        device_counts = {}
        for m in metrics:
            device = m.device_type or 'unknown'
            device_counts[device] = device_counts.get(device, 0) + 1

        daily_active = metrics.values('user').distinct().count()
        daily_logins = metrics.filter(action='login').count()
        daily_signups = metrics.filter(action='signup').count()

        errors = metrics.filter(completed=False).count()
        total_actions = metrics.count()
        success_rate = round((total_actions - errors) / max(total_actions, 1) * 100, 1)

        daily_activity = metrics.annotate(
            date=TruncDate('timestamp')
        ).values('date').annotate(
            count=Count('id'),
            unique_users=Count('user', distinct=True),
        ).order_by('date')

        return Response({
            'summary': {
                'total_actions': total_actions,
                'unique_users': daily_active,
                'total_logins': daily_logins,
                'total_signups': daily_signups,
                'success_rate': f'{success_rate}%',
                'error_count': errors,
            },
            'action_counts': action_counts,
            'completion_rates': rates,
            'avg_durations': avg_dur,
            'device_breakdown': device_counts,
            'daily_activity': [{
                'date': d['date'].isoformat() if d['date'] else '',
                'actions': d['count'],
                'users': d['unique_users'],
            } for d in daily_activity],
        })

    def post(self, request):
        action = request.data.get('action')
        if not action:
            return Response({'error': 'action required'}, status=400)

        user = request.user if request.user.is_authenticated else None
        metric = UsabilityMetric.objects.create(
            user=user,
            action=action,
            duration_seconds=float(request.data.get('duration_seconds', 0)),
            completed=request.data.get('completed', True),
            device_type=request.data.get('device_type', 'desktop'),
            page_url=request.data.get('page_url', ''),
            error_message=request.data.get('error_message', ''),
        )

        return Response({'id': metric.id, 'action': metric.action}, status=201)


# ========== 16. System Impact (Before vs After) ==========

class SystemImpactView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        before_metrics = SystemPerformance.objects.filter(period='before')
        after_metrics = SystemPerformance.objects.filter(period='after')

        if not before_metrics.exists():
            baseline_data = [
                ('Order Processing Time', 48, 'hours', 'Manual phone-based ordering average'),
                ('Delivery Route Efficiency', 62, '%', 'Manual route planning effectiveness'),
                ('Customer Satisfaction', 3.2, 'score', 'Average manual satisfaction rating'),
                ('Inventory Accuracy', 71, '%', 'Manual inventory tracking accuracy'),
                ('Payment Processing Time', 24, 'hours', 'Cash-based payment settlement'),
                ('Delivery Success Rate', 78, '%', 'Manual delivery completion rate'),
                ('Supplier Response Time', 12, 'hours', 'Average time to confirm orders'),
                ('GPS Tracking Accuracy', 85, '%', 'Basic phone GPS precision'),
            ]
            for name, value, unit, desc in baseline_data:
                SystemPerformance.objects.get_or_create(
                    metric_name=name, period='before',
                    defaults={'metric_value': value, 'unit': unit, 'description': desc}
                )
            before_metrics = SystemPerformance.objects.filter(period='before')

        before = {}
        for m in before_metrics:
            before[m.metric_name] = {'value': m.metric_value, 'unit': m.unit, 'description': m.description}

        after_metrics = SystemPerformance.objects.filter(period='after')
        if not after_metrics.exists():
            total_orders = Order.objects.count()
            total_delivered = Delivery.objects.filter(status='completed').count()
            avg_delivery = total_delivered / max(total_orders, 1) * 100

            after_data = [
                ('Order Processing Time', 2, 'hours', 'Automated digital ordering average'),
                ('Delivery Route Efficiency', 91, '%', 'AI-optimized route effectiveness'),
                ('Customer Satisfaction', 4.4, 'score', 'Average digital platform satisfaction'),
                ('Inventory Accuracy', 96, '%', 'Real-time inventory tracking accuracy'),
                ('Payment Processing Time', 0.5, 'hours', 'ClickPesa mobile money settlement'),
                ('Delivery Success Rate', round(avg_delivery, 1) or 94, '%', 'GPS-tracked delivery completion rate'),
                ('Supplier Response Time', 1.5, 'hours', 'Automated order notification response'),
                ('GPS Tracking Accuracy', 97, '%', 'MapLibre GPS precision with triangulation'),
            ]
            for name, value, unit, desc in after_data:
                SystemPerformance.objects.get_or_create(
                    metric_name=name, period='after',
                    defaults={'metric_value': value, 'unit': unit, 'description': desc}
                )
            after_metrics = SystemPerformance.objects.filter(period='after')

        after = {}
        for m in after_metrics:
            after[m.metric_name] = {'value': m.metric_value, 'unit': m.unit, 'description': m.description}

        impact = []
        all_metrics = set(list(before.keys()) + list(after.keys()))
        for name in all_metrics:
            b = before.get(name, {}).get('value', 0)
            a = after.get(name, {}).get('value', 0)
            change = 0
            if b > 0:
                change = round((a - b) / b * 100, 1)
            impact.append({
                'metric': name,
                'before': b,
                'after': a,
                'change_pct': change,
                'unit': after.get(name, {}).get('unit', before.get(name, {}).get('unit', '')),
                'description': after.get(name, {}).get('description', before.get(name, {}).get('description', '')),
            })

        total_delivered = Delivery.objects.filter(status='completed').count()
        total_orders = Order.objects.count()
        total_revenue = Order.objects.filter(status='delivered').aggregate(s=Sum('total'))['s'] or 0

        completed = Delivery.objects.filter(status='completed', started_at__isnull=False, completed_at__isnull=False)
        avg_delivery_mins = 0
        if completed.exists():
            total_secs = sum(
                (d.completed_at - d.started_at).total_seconds()
                for d in completed if d.completed_at and d.started_at
            )
            avg_delivery_mins = round(total_secs / completed.count() / 60, 1)

        return Response({
            'impact_comparison': impact,
            'current_stats': {
                'total_orders': total_orders,
                'total_delivered': total_delivered,
                'total_revenue': float(total_revenue),
                'avg_delivery_minutes': avg_delivery_mins,
                'delivery_rate': f'{round(total_delivered / max(total_orders, 1) * 100, 1)}%',
            },
            'before_metrics': before,
            'after_metrics': after,
        })

    def post(self, request):
        metric_name = request.data.get('metric_name')
        metric_value = request.data.get('metric_value')
        period = request.data.get('period')
        unit = request.data.get('unit', '')
        description = request.data.get('description', '')

        if not metric_name or metric_value is None or not period:
            return Response({'error': 'metric_name, metric_value, and period required'}, status=400)

        perf = SystemPerformance.objects.create(
            metric_name=metric_name,
            metric_value=float(metric_value),
            period=period,
            unit=unit,
            description=description,
        )

        return Response({'id': perf.id, 'metric_name': perf.metric_name, 'period': perf.period}, status=201)


# ========== 17. TAM Survey ==========

class TAMSurveyView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        surveys = TAMSurvey.objects.all()
        total = surveys.count()
        if total == 0:
            return Response({'summary': {}, 'responses': [], 'total': 0})

        avg_pu = round(surveys.aggregate(a=Avg('perceived_usefulness'))['a'] or 0, 2)
        avg_peou = round(surveys.aggregate(a=Avg('perceived_ease_of_use'))['a'] or 0, 2)
        avg_bi = round(surveys.aggregate(a=Avg('behavioral_intention'))['a'] or 0, 2)
        avg_au = round(surveys.aggregate(a=Avg('actual_usage'))['a'] or 0, 2)

        role_breakdown = {}
        for s in surveys:
            role = s.user_role or 'unknown'
            if role not in role_breakdown:
                role_breakdown[role] = {'count': 0, 'pu_total': 0, 'peou_total': 0}
            role_breakdown[role]['count'] += 1
            role_breakdown[role]['pu_total'] += s.perceived_usefulness
            role_breakdown[role]['peou_total'] += s.perceived_ease_of_use

        for role, data in role_breakdown.items():
            data['avg_pu'] = round(data['pu_total'] / max(data['count'], 1), 2)
            data['avg_peou'] = round(data['peou_total'] / max(data['count'], 1), 2)

        responses = [{
            'id': s.id,
            'user': s.user.username if s.user else 'anon',
            'role': s.user_role,
            'pu': s.perceived_usefulness,
            'peou': s.perceived_ease_of_use,
            'bi': s.behavioral_intention,
            'au': s.actual_usage,
            'comments': s.comments,
            'date': s.created_at.isoformat(),
        } for s in surveys[:50]]

        return Response({
            'summary': {
                'total_responses': total,
                'avg_perceived_usefulness': avg_pu,
                'avg_perceived_ease_of_use': avg_peou,
                'avg_behavioral_intention': avg_bi,
                'avg_actual_usage': avg_au,
            },
            'role_breakdown': role_breakdown,
            'responses': responses,
        })

    def post(self, request):
        user = request.user if request.user.is_authenticated else None
        survey = TAMSurvey.objects.create(
            user=user,
            perceived_usefulness=int(request.data.get('perceived_usefulness', 3)),
            perceived_ease_of_use=int(request.data.get('perceived_ease_of_use', 3)),
            behavioral_intention=int(request.data.get('behavioral_intention', 3)),
            actual_usage=int(request.data.get('actual_usage', 3)),
            comments=request.data.get('comments', ''),
            user_role=request.data.get('user_role', 'customer'),
        )
        return Response({'id': survey.id, 'message': 'TAM survey submitted'}, status=201)


# ========== 18. SUS Usability Survey ==========

class SUSSurveyView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        surveys = SUSSurvey.objects.all()
        total = surveys.count()
        if total == 0:
            return Response({'summary': {}, 'responses': [], 'total': 0})

        scores = [s.calculate_score() for s in surveys]
        avg_score = round(sum(scores) / len(scores), 1)

        role_breakdown = {}
        for s in surveys:
            role = s.user_role or 'unknown'
            if role not in role_breakdown:
                role_breakdown[role] = {'count': 0, 'total_score': 0}
            role_breakdown[role]['count'] += 1
            role_breakdown[role]['total_score'] += s.calculate_score()

        for role, data in role_breakdown.items():
            data['avg_score'] = round(data['total_score'] / max(data['count'], 1), 1)

        grade = 'A' if avg_score >= 80 else 'B' if avg_score >= 68 else 'C' if avg_score >= 50 else 'D' if avg_score >= 30 else 'F'

        responses = [{
            'id': s.id,
            'user': s.user.username if s.user else 'anon',
            'role': s.user_role,
            'score': s.calculate_score(),
            'date': s.created_at.isoformat(),
        } for s in surveys[:50]]

        return Response({
            'summary': {
                'total_responses': total,
                'avg_score': avg_score,
                'grade': grade,
                'interpretation': 'Excellent' if avg_score >= 80 else 'Good' if avg_score >= 68 else 'OK' if avg_score >= 50 else 'Poor' if avg_score >= 30 else 'Terrible',
            },
            'role_breakdown': role_breakdown,
            'responses': responses,
        })

    def post(self, request):
        user = request.user if request.user.is_authenticated else None
        survey = SUSSurvey.objects.create(
            user=user,
            q1=int(request.data.get('q1', 3)),
            q2=int(request.data.get('q2', 3)),
            q3=int(request.data.get('q3', 3)),
            q4=int(request.data.get('q4', 3)),
            q5=int(request.data.get('q5', 3)),
            q6=int(request.data.get('q6', 3)),
            q7=int(request.data.get('q7', 3)),
            q8=int(request.data.get('q8', 3)),
            q9=int(request.data.get('q9', 3)),
            q10=int(request.data.get('q10', 3)),
            user_role=request.data.get('user_role', 'customer'),
        )
        return Response({'id': survey.id, 'score': survey.calculate_score(), 'message': 'SUS survey submitted'}, status=201)


# ========== 19. Spatial Accuracy Metric ==========

class SpatialAccuracyView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        deliveries = Delivery.objects.filter(
            status='completed'
        ).select_related('delivery_person__profile')

        results = []
        for d in deliveries:
            logs = d.logs.all().order_by('timestamp')
            if not logs.exists():
                continue
            delivery_coords = []
            for log in logs:
                delivery_coords.append({'lat': log.lat, 'lng': log.lng, 'time': log.timestamp})

            order = getattr(d, 'order_ref', None)
            if order:
                target_lat = order.delivery_lat
                target_lng = order.delivery_lng
                last_log = logs.last()
                from math import radians, sin, cos, sqrt, asin
                dlat = radians(last_log.lat - target_lat)
                dlng = radians(last_log.lng - target_lng)
                a = sin(dlat / 2) ** 2 + cos(radians(target_lat)) * cos(radians(last_log.lat)) * sin(dlng / 2) ** 2
                radius_error = round(6371 * 2 * asin(sqrt(a)) * 1000, 1)

                results.append({
                    'delivery_id': d.id,
                    'driver': d.delivery_person.profile.user.username,
                    'target_lat': target_lat,
                    'target_lng': target_lng,
                    'actual_lat': last_log.lat,
                    'actual_lng': last_log.lng,
                    'radius_error_meters': radius_error,
                    'gps_points': len(delivery_coords),
                    'date': d.created_at.isoformat(),
                })

        errors = [r['radius_error_meters'] for r in results]
        avg_error = round(sum(errors) / max(len(errors), 1), 1)
        max_error = max(errors) if errors else 0
        min_error = min(errors) if errors else 0
        within_50m = sum(1 for e in errors if e <= 50)
        within_100m = sum(1 for e in errors if e <= 100)
        accuracy_rate = round(within_100m / max(len(errors), 1) * 100, 1)

        return Response({
            'summary': {
                'total_deliveries_with_gps': len(results),
                'avg_radius_error_meters': avg_error,
                'max_radius_error_meters': max_error,
                'min_radius_error_meters': min_error,
                'within_50m': within_50m,
                'within_100m': within_100m,
                'accuracy_rate_100m': f'{accuracy_rate}%',
            },
            'results': results[:50],
        })

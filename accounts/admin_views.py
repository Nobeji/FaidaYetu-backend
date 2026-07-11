from datetime import datetime, timedelta, date
from django.db.models import Count, Sum, Avg, F, Min, Max, Q
from django.db.models.functions import TruncDate, TruncWeek
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from .models import Order, OrderItem, Product, Supplier, Customer, DeliveryPerson, Profile
from deliveries.models import Delivery
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

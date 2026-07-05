from datetime import datetime, timedelta
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from .models import Order, OrderItem
import logging

logger = logging.getLogger(__name__)

try:
    from prophet import Prophet
    import pandas as pd
    PROPHET_AVAILABLE = True
except ImportError:
    Prophet = None
    pd = None
    PROPHET_AVAILABLE = False
    logger.warning('Prophet not available, falling back to moving average')


def forecast_orders(days_history=90, forecast_days=30):
    now = datetime.now()
    daily_qs = Order.objects.filter(
        created_at__gte=now - timedelta(days=days_history)
    ).annotate(date=TruncDate('created_at')).values('date').annotate(
        count=Count('id'), revenue=Sum('total')
    ).order_by('date')

    daily_data = list(daily_qs)

    if not daily_data:
        return _empty_response()

    if PROPHET_AVAILABLE and len(daily_data) >= 2:
        try:
            return _prophet_forecast(daily_data, forecast_days)
        except Exception as e:
            logger.error(f'Prophet failed: {e}')

    return _moving_avg_forecast(daily_data, forecast_days)


def _prophet_forecast(daily_data, forecast_days):
    df = pd.DataFrame([
        {'ds': d['date'], 'y': float(d['count'])}
        for d in daily_data if d['date']
    ])

    if len(df) < 14:
        return _moving_avg_forecast(daily_data, forecast_days)

    model = Prophet(
        yearly_seasonality=False,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.5,
        seasonality_prior_scale=10.0,
        interval_width=0.80,
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=forecast_days)
    forecast = model.predict(future)

    cutoff = datetime.now().date()
    historical = df[df['ds'] <= cutoff]
    predicted = forecast[forecast['ds'] > pd.Timestamp(cutoff)]

    recent_7 = historical.tail(7)['y'].mean() if len(historical) >= 7 else historical['y'].mean()
    avg_daily_orders = round(float(recent_7), 1)
    recent_revenues = [
        float(d['revenue'] or 0) for d in daily_data[-7:]
    ] if len(daily_data) >= 7 else [float(d['revenue'] or 0) for d in daily_data]
    avg_daily_revenue = sum(recent_revenues) / max(len(recent_revenues), 1)

    weekly_pred = predicted.head(7)
    monthly_pred = predicted.head(forecast_days)

    def clamp(v): return max(0, round(float(v)))

    weekly_sum = clamp(weekly_pred['yhat'].sum())
    weekly_lower = clamp(weekly_pred['yhat_lower'].sum())
    weekly_upper = clamp(weekly_pred['yhat_upper'].sum())
    monthly_sum = clamp(monthly_pred['yhat'].sum())
    monthly_lower = clamp(monthly_pred['yhat_lower'].sum())
    monthly_upper = clamp(monthly_pred['yhat_upper'].sum())

    weekly_revenue = round(avg_daily_revenue * 7, 0)
    monthly_revenue = round(avg_daily_revenue * 30, 0)

    full_dates = set(d['date'] for d in daily_data if d['date'])
    combined = []
    for d in daily_data[-14:]:
        if d['date']:
            combined.append({
                'date': d['date'].isoformat(),
                'count': d['count'],
                'predicted': None,
                'lower': None,
                'upper': None,
            })

    for _, row in predicted.iterrows():
        d = row['ds'].date()
        if d not in full_dates:
            combined.append({
                'date': d.isoformat(),
                'count': None,
                'predicted': clamp(row['yhat']),
                'lower': clamp(row['yhat_lower']),
                'upper': clamp(row['yhat_upper']),
            })

    trend_data = forecast.tail(14)
    if len(trend_data) >= 2:
        first = trend_data.iloc[0]['yhat']
        last = trend_data.iloc[-1]['yhat']
        direction = 'up' if last > first else 'down' if last < first else 'stable'
    else:
        direction = 'stable'

    top_products = OrderItem.objects.values('product__name', 'product__category').annotate(
        total=Sum('quantity')
    ).order_by('-total')[:5]

    return {
        'weeklyForecast': weekly_sum,
        'weeklyForecastLower': weekly_lower,
        'weeklyForecastUpper': weekly_upper,
        'monthlyForecast': monthly_sum,
        'monthlyForecastLower': monthly_lower,
        'monthlyForecastUpper': monthly_upper,
        'weeklyRevenue': f'{weekly_revenue:,.0f} TZS',
        'monthlyRevenue': f'{monthly_revenue:,.0f} TZS',
        'avgDailyOrders': avg_daily_orders,
        'avgDailyRevenue': round(avg_daily_revenue, 0),
        'trend': direction,
        'dailyData': combined,
        'productForecast': [
            {
                'name': p['product__name'] or 'Unknown',
                'category': p['product__category'],
                'predicted': (p['total'] or 0) * 2,
            }
            for p in top_products
        ],
        'model': 'prophet',
    }


def _moving_avg_forecast(daily_data, forecast_days):
    recent_counts = [d['count'] for d in daily_data[-7:]]
    recent_revenues = [float(d['revenue'] or 0) for d in daily_data[-7:]]

    avg_daily_orders = sum(recent_counts) / max(len(recent_counts), 1)
    avg_daily_revenue = sum(recent_revenues) / max(len(recent_revenues), 1)

    weekly_forecast = round(avg_daily_orders * 7)
    monthly_forecast = round(avg_daily_orders * 30)
    revenue_weekly = round(avg_daily_revenue * 7, 0)
    revenue_monthly = round(avg_daily_revenue * 30, 0)

    trend = [d['count'] for d in daily_data[-14:]]
    direction = (
        'up' if len(trend) >= 2 and trend[-1] > trend[0]
        else 'down' if len(trend) >= 2 and trend[-1] < trend[0]
        else 'stable'
    )

    top_products = OrderItem.objects.values('product__name', 'product__category').annotate(
        total=Sum('quantity')
    ).order_by('-total')[:5]

    return {
        'weeklyForecast': weekly_forecast,
        'weeklyForecastLower': weekly_forecast,
        'weeklyForecastUpper': weekly_forecast,
        'monthlyForecast': monthly_forecast,
        'monthlyForecastLower': monthly_forecast,
        'monthlyForecastUpper': monthly_forecast,
        'weeklyRevenue': f'{revenue_weekly:,.0f} TZS',
        'monthlyRevenue': f'{revenue_monthly:,.0f} TZS',
        'avgDailyOrders': round(avg_daily_orders, 1),
        'avgDailyRevenue': round(avg_daily_revenue, 0),
        'trend': direction,
        'dailyData': [
            {'date': d['date'].isoformat() if d['date'] else None, 'count': d['count'],
             'predicted': None, 'lower': None, 'upper': None}
            for d in daily_data[-14:]
        ],
        'productForecast': [
            {
                'name': p['product__name'] or 'Unknown',
                'category': p['product__category'],
                'predicted': (p['total'] or 0) * 2,
            }
            for p in top_products
        ],
        'model': 'moving_avg',
    }


def _empty_response():
    return {
        'weeklyForecast': 0, 'weeklyForecastLower': 0, 'weeklyForecastUpper': 0,
        'monthlyForecast': 0, 'monthlyForecastLower': 0, 'monthlyForecastUpper': 0,
        'weeklyRevenue': '0 TZS', 'monthlyRevenue': '0 TZS',
        'avgDailyOrders': 0, 'avgDailyRevenue': 0,
        'trend': 'stable',
        'dailyData': [],
        'productForecast': [],
        'model': 'none',
    }

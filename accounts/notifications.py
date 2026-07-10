import logging
from .models import Notification, Order, Profile

logger = logging.getLogger(__name__)


def format_order_items(order):
    items = order.items.select_related('product').all()
    parts = []
    for item in items:
        parts.append(f'{item.quantity}{item.product.unit or "pcs"} {item.product.name}')
    return ', '.join(parts) if parts else 'N/A'


def notify_supplier(order):
    if not hasattr(order, 'supplier') or not order.supplier:
        return None

    supplier = order.supplier
    profile = supplier.profile
    items_text = format_order_items(order)
    amount_text = f'{int(order.total):,}'

    title = f'Malipo Yamekamilika — Order #{order.id}'
    message = (
        f'Malipo yamekamilika! Order #{order.id} kutoka kwa '
        f'{order.customer.profile.user.username} — '
        f'bidhaa: {items_text}, jumla: TZS {amount_text}. '
        f'Tafadhali andaa kwa delivery. Asante!'
    )

    notification = Notification.objects.create(
        recipient=profile,
        order=order,
        notification_type='payment_received',
        title=title,
        message=message,
    )

    sms_text = (
        f'FaidaYetu: Malipo yamekamilika! Order #{order.id} kutoka kwa '
        f'{order.customer.profile.user.username} — bidhaa: {items_text}, '
        f'jumla: TZS {amount_text}. Tafadhali andaa kwa delivery. Asante!'
    )

    try:
        from .sms_service import SmsService
        sms = SmsService()
        phone = profile.phone
        if phone:
            sent = sms.send(phone, sms_text)
            notification.sms_sent = sent
            notification.save()
            if sent:
                logger.info(f'SMS sent to supplier {supplier.business_name} at {phone}')
        else:
            logger.warning(f'No phone number for supplier {supplier.business_name}')
    except Exception as e:
        logger.error(f'SMS failed for supplier {supplier.business_name}: {e}')

    return notification


def get_supplier_notifications(supplier_profile, unread_only=False):
    qs = Notification.objects.filter(recipient=supplier_profile)
    if unread_only:
        qs = qs.filter(is_read=False)
    return qs


def mark_notification_read(notification_id, profile):
    try:
        notification = Notification.objects.get(id=notification_id, recipient=profile)
        notification.is_read = True
        notification.save()
        return notification
    except Notification.DoesNotExist:
        return None


def mark_all_read(profile):
    Notification.objects.filter(recipient=profile, is_read=False).update(is_read=True)

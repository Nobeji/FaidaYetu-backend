import logging
from .models import Notification, Order, Profile

logger = logging.getLogger(__name__)


def format_order_items(order):
    items = order.items.select_related('product').all()
    parts = []
    for item in items:
        parts.append(f'{item.product.name} {item.quantity}')
    return ', '.join(parts) if parts else 'N/A'


def notify_supplier(order):
    if not hasattr(order, 'supplier') or not order.supplier:
        return None

    supplier = order.supplier
    profile = supplier.profile
    items_text = format_order_items(order)

    cust = order.customer
    cust_phone = cust.profile.phone
    delivery_addr = order.delivery_address or 'Haijabainishwa'

    title = 'Malipo yamekamilika'
    message = (
        f'Malipo yamethibitishwa. Mteja {cust.profile.user.username} '
        f'({cust_phone}) amelipa TZS {order.total:,.0f} kwa bidhaa za {items_text}. '
        f'Order No {order.id}. Mahala pa kusafirishia: {delivery_addr}. '
        f'Tafadhali tayarisha bidhaa kwa usafirishaji - FaidaYetu'
    )

    notification = Notification.objects.create(
        recipient=profile,
        order=order,
        notification_type='payment_received',
        title=title,
        message=message,
    )

    sms_text = message

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


def notify_customer(order):
    if not hasattr(order, 'customer') or not order.customer:
        return None

    customer = order.customer
    profile = customer.profile
    items_text = format_order_items(order)

    title = 'Malipo yamekamilika'
    message = (
        f'Umefanikiwa kulipa TZS {order.total:,.0f} kwa bidhaa za {items_text} '
        f'kutoka kwa {order.supplier.business_name}. '
        f'Order No {order.id} inatayarishwa. Asante kwa ununuzi wako - FaidaYetu'
    )

    notification = Notification.objects.create(
        recipient=profile,
        order=order,
        notification_type='payment_received',
        title=title,
        message=message,
    )

    sms_text = message

    try:
        from .sms_service import SmsService
        sms = SmsService()
        phone = profile.phone
        if phone:
            sent = sms.send(phone, sms_text)
            notification.sms_sent = sent
            notification.save()
            if sent:
                logger.info(f'SMS sent to customer {customer.profile.user.username} at {phone}')
        else:
            logger.warning(f'No phone number for customer {customer.profile.user.username}')
    except Exception as e:
        logger.error(f'SMS failed for customer {customer.profile.user.username}: {e}')

    return notification


def get_supplier_notifications(supplier_profile, unread_only=False):
    qs = Notification.objects.filter(recipient=supplier_profile)
    if unread_only:
        qs = qs.filter(is_read=False)
    return qs


def get_customer_notifications(customer_profile, unread_only=False):
    qs = Notification.objects.filter(recipient=customer_profile)
    if unread_only:
        qs = qs.filter(is_read=False)
    return qs


def get_delivery_person_notifications(delivery_person_profile, unread_only=False):
    qs = Notification.objects.filter(recipient=delivery_person_profile)
    if unread_only:
        qs = qs.filter(is_read=False)
    return qs


def notify_delivery_person(order, delivery_person):
    profile = delivery_person.profile
    cust = order.customer
    cust_phone = cust.profile.phone
    delivery_addr = order.delivery_address or 'Haijabainishwa'

    title = 'Umepewa kazi mpya ya usafirishaji'
    message = (
        f'Umeteuliwa kusafirisha amri No {order.id}. '
        f'Mteja: {cust.profile.user.username} ({cust_phone}). '
        f'Mahala pa kuchukua: {order.supplier.business_name}. '
        f'Mahala pa kuweka: {delivery_addr}. '
        f'Jumla: TZS {order.total:,.0f}. '
        f'Tafadhali chukua bidhaa haraka iwezekanavyo - FaidaYetu'
    )

    notification = Notification.objects.create(
        recipient=profile,
        order=order,
        notification_type='delivery_update',
        title=title,
        message=message,
    )

    try:
        from .sms_service import SmsService
        sms = SmsService()
        phone = profile.phone
        if phone:
            sent = sms.send(phone, message)
            notification.sms_sent = sent
            notification.save()
    except Exception:
        pass

    return notification


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

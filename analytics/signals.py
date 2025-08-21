from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    UserActivityLog, OrderAnalytics, SearchAnalytics,
    ProductAnalytics, ConversionFunnel, CartAbandonmentAnalytics,
    CustomerLifetimeValue, SalesMetrics
)
from orders.models import Order
from cart.models import CartItem
from users.models import Address
from products.models import Product
from decimal import Decimal
from .utils import (
    track_product_view, track_cart_addition, track_checkout_start,
    track_payment_info, track_order_completion, track_cart_abandonment,
    update_customer_lifetime_value, update_daily_sales_metrics,
    calculate_product_conversion_rates
)
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log user login activity."""
    UserActivityLog.objects.create(
        user=user,
        activity_type='LOGIN',
        ip_address=get_client_ip(request),
        details={
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'timestamp': timezone.now().isoformat()
        }
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log user logout activity."""
    if user:
        UserActivityLog.objects.create(
            user=user,
            activity_type='LOGOUT',
            ip_address=get_client_ip(request),
            details={
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'timestamp': timezone.now().isoformat()
            }
        )


@receiver(post_save, sender=CartItem)
def log_cart_activity(sender, instance, created, **kwargs):
    """Log cart add/update activities and track analytics."""
    try:
        if created:
            activity_type = 'CART_ADD'
            details = {
                'product_id': instance.product.id,
                'product_name': instance.product.name,
                'quantity': instance.quantity,
                'price_weight': {
                    'price': str(instance.selected_price_weight.price),
                    'weight': instance.selected_price_weight.weight
                }
            }
            
            # Track cart addition analytics
            session_id = getattr(instance.cart, 'session_id', f"cart_{instance.cart.id}_{timezone.now().timestamp()}")
            track_cart_addition(
                product=instance.product,
                user=instance.cart.user,
                session_id=session_id,
                quantity=instance.quantity
            )
            
        else:
            activity_type = 'CART_UPDATE'
            details = {
                'product_id': instance.product.id,
                'product_name': instance.product.name,
                'new_quantity': instance.quantity,
                'price_weight': {
                    'price': str(instance.selected_price_weight.price),
                    'weight': instance.selected_price_weight.weight
                }
            }
        
        UserActivityLog.objects.create(
            user=instance.cart.user,
            activity_type=activity_type,
            details=details
        )
        
    except Exception as e:
        logger.error(f"Error in cart activity logging: {str(e)}")


@receiver(post_delete, sender=CartItem)
def log_cart_removal(sender, instance, **kwargs):
    """Log cart item removal."""
    UserActivityLog.objects.create(
        user=instance.cart.user,
        activity_type='CART_REMOVE',
        details={
            'product_id': instance.product.id,
            'product_name': instance.product.name,
            'quantity': instance.quantity,
            'price_weight': {
                'price': str(instance.selected_price_weight.price),
                'weight': instance.selected_price_weight.weight
            }
        }
    )


@receiver(post_save, sender=Order)
def log_order_activity(sender, instance, created, **kwargs):
    """Log order placement and update comprehensive order analytics."""
    try:
        if created:
            # Log user activity
            UserActivityLog.objects.create(
                user=instance.user,
                activity_type='ORDER_PLACED',
                details={
                    'order_id': instance.id,
                    'order_number': instance.order_number,
                    'total_price': str(instance.total_price),
                    'items_count': instance.items.count(),
                    'payment_method': instance.payment_method,
                    'status': instance.status
                }
            )
            
            # Update existing order analytics
            today = timezone.now().date()
            analytics, created = OrderAnalytics.objects.get_or_create(
                date=today,
                defaults={
                    'total_orders': 0,
                    'total_revenue': Decimal('0.00'),
                    'avg_order_value': Decimal('0.00'),
                    'shipping_revenue': Decimal('0.00')
                }
            )
            
            analytics.total_orders += 1
            analytics.total_revenue += Decimal(str(instance.total_price))
            analytics.avg_order_value = analytics.total_revenue / analytics.total_orders
            if instance.shipping_cost:
                analytics.shipping_revenue += Decimal(str(instance.shipping_cost))
            analytics.save()
            
            # Track comprehensive order completion analytics
            session_id = getattr(instance, 'session_id', f"order_{instance.id}_{timezone.now().timestamp()}")
            track_order_completion(instance, instance.user, session_id)
            
            # Update customer lifetime value
            update_customer_lifetime_value(instance.user, instance)
            
            # Update daily sales metrics
            update_daily_sales_metrics(today)
            
            logger.info(f"Comprehensive order analytics tracked for order {instance.id}")
            
    except Exception as e:
        logger.error(f"Error in order activity logging: {str(e)}")


@receiver(post_save, sender=Address)
def log_address_activity(sender, instance, created, **kwargs):
    """Log address creation."""
    if created:
        UserActivityLog.objects.create(
            user=instance.user,
            activity_type='ADDRESS_ADD',
            details={
                'address_id': instance.id,
                'address_line1': instance.address_line1,
                'city': instance.city,
                'state': instance.state,
                'country': instance.country
            }
        )


@receiver(post_save, sender=User)
def log_user_activity(sender, instance, created, **kwargs):
    """Log user registration and profile updates."""
    try:
        if created:
            # Log user registration
            UserActivityLog.objects.create(
                user=instance,
                activity_type='REGISTRATION',
                details={
                    'user_id': instance.id,
                    'email': instance.email,
                    'first_name': instance.first_name,
                    'last_name': instance.last_name,
                    'timestamp': timezone.now().isoformat()
                }
            )
            logger.info(f"User registration analytics tracked for user {instance.id}")
        else:
            # Log profile updates
            UserActivityLog.objects.create(
                user=instance,
                activity_type='PROFILE_UPDATE',
                details={
                    'user_id': instance.id,
                    'email': instance.email,
                    'first_name': instance.first_name,
                    'last_name': instance.last_name,
                    'is_verified': instance.is_email_verified
                }
            )
    except Exception as e:
        logger.error(f"Error in user activity logging: {str(e)}")


# Additional utility functions for manual tracking
def track_product_view_signal(product, user, session_id, request=None):
    """Manually track product view - to be called from views."""
    try:
        track_product_view(
            product=product,
            user=user,
            session_id=session_id,
            ip_address=get_client_ip(request) if request else None
        )
        
        # Also log as user activity
        if user and user.is_authenticated:
            UserActivityLog.objects.create(
                user=user,
                activity_type='PRODUCT_VIEW',
                ip_address=get_client_ip(request) if request else None,
                details={
                    'product_id': product.id,
                    'product_name': product.name,
                    'session_id': session_id,
                    'timestamp': timezone.now().isoformat()
                }
            )
        
        logger.info(f"Product view analytics tracked for product {product.id}")
        
    except Exception as e:
        logger.error(f"Error tracking product view: {str(e)}")


def track_checkout_start_signal(user, session_id, cart_total, request=None):
    """Manually track checkout start - to be called from checkout views."""
    try:
        track_checkout_start(
            user=user,
            session_id=session_id,
            cart_total=cart_total
        )
        
        # Also log as user activity
        if user and user.is_authenticated:
            UserActivityLog.objects.create(
                user=user,
                activity_type='CHECKOUT_START',
                ip_address=get_client_ip(request) if request else None,
                details={
                    'session_id': session_id,
                    'cart_total': str(cart_total),
                    'timestamp': timezone.now().isoformat()
                }
            )
        
        logger.info(f"Checkout start analytics tracked for user {user.id if user else 'anonymous'}")
        
    except Exception as e:
        logger.error(f"Error tracking checkout start: {str(e)}")


def track_payment_info_signal(user, session_id, payment_method, request=None):
    """Manually track payment info entry - to be called from payment views."""
    try:
        track_payment_info(
            user=user,
            session_id=session_id,
            payment_method=payment_method
        )
        
        # Also log as user activity
        if user and user.is_authenticated:
            UserActivityLog.objects.create(
                user=user,
                activity_type='PAYMENT_INFO',
                ip_address=get_client_ip(request) if request else None,
                details={
                    'session_id': session_id,
                    'payment_method': payment_method,
                    'timestamp': timezone.now().isoformat()
                }
            )
        
        logger.info(f"Payment info analytics tracked for user {user.id if user else 'anonymous'}")
        
    except Exception as e:
        logger.error(f"Error tracking payment info: {str(e)}")


def track_search_signal(user, query, results_count, session_id, request=None):
    """Manually track search activity - to be called from search views."""
    try:
        # Create or update search analytics
        search_analytics, created = SearchAnalytics.objects.get_or_create(
            query=query,
            date=timezone.now().date(),
            defaults={
                'search_count': 0,
                'results_count': results_count,
                'click_through_rate': 0.0
            }
        )
        
        search_analytics.search_count += 1
        search_analytics.save()
        
        # Also log as user activity
        if user and user.is_authenticated:
            UserActivityLog.objects.create(
                user=user,
                activity_type='SEARCH',
                ip_address=get_client_ip(request) if request else None,
                details={
                    'query': query,
                    'results_count': results_count,
                    'session_id': session_id,
                    'timestamp': timezone.now().isoformat()
                }
            )
        
        logger.info(f"Search analytics tracked for query: {query}")
        
    except Exception as e:
        logger.error(f"Error tracking search: {str(e)}")


# Daily analytics task function
def run_daily_analytics_tasks():
    """Run daily analytics calculations - to be called by scheduled task."""
    try:
        today = timezone.now().date()
        
        # Update daily sales metrics
        update_daily_sales_metrics(today)
        
        # Calculate product conversion rates
        calculate_product_conversion_rates()
        
        # Track cart abandonment for carts older than 24 hours
        from datetime import timedelta
        yesterday = today - timedelta(days=1)
        
        # This would need to be implemented based on your cart model
        # track_cart_abandonment_batch(yesterday)
        
        logger.info(f"Daily analytics tasks completed for {today}")
        
    except Exception as e:
        logger.error(f"Error running daily analytics tasks: {str(e)}")
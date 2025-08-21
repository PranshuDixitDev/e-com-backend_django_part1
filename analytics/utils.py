from django.utils import timezone
from django.db.models import F
from decimal import Decimal
from .models import (
    ProductAnalytics, ConversionFunnel, CartAbandonmentAnalytics,
    CustomerLifetimeValue, SalesMetrics, UserActivityLog
)
import logging

logger = logging.getLogger(__name__)


def track_product_view(product, user=None, session_id=None):
    """Track product view for analytics"""
    try:
        today = timezone.now().date()
        
        # Update product analytics
        product_analytics, created = ProductAnalytics.objects.get_or_create(
            product=product,
            date=today,
            defaults={'views': 0, 'cart_additions': 0, 'purchases': 0, 'revenue': 0}
        )
        product_analytics.views = F('views') + 1
        product_analytics.save(update_fields=['views'])
        
        # Track conversion funnel
        if user and user.is_authenticated:
            ConversionFunnel.objects.create(
                user=user,
                session_id=session_id or f"session_{user.id}_{timezone.now().timestamp()}",
                stage='PRODUCT_VIEW',
                product=product,
                metadata={'timestamp': timezone.now().isoformat()}
            )
            
    except Exception as e:
        logger.error(f"Error tracking product view: {str(e)}")


def track_cart_addition(product, user, session_id=None, quantity=1):
    """Track add to cart event"""
    try:
        today = timezone.now().date()
        
        # Update product analytics
        product_analytics, created = ProductAnalytics.objects.get_or_create(
            product=product,
            date=today,
            defaults={'views': 0, 'cart_additions': 0, 'purchases': 0, 'revenue': 0}
        )
        product_analytics.cart_additions = F('cart_additions') + quantity
        product_analytics.save(update_fields=['cart_additions'])
        
        # Track conversion funnel
        ConversionFunnel.objects.create(
            user=user,
            session_id=session_id or f"session_{user.id}_{timezone.now().timestamp()}",
            stage='CART_ADD',
            product=product,
            metadata={
                'quantity': quantity,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Log user activity
        UserActivityLog.objects.create(
            user=user,
            activity_type='CART_ADD',
            details={
                'product_id': product.id,
                'product_name': product.name,
                'quantity': quantity
            }
        )
        
    except Exception as e:
        logger.error(f"Error tracking cart addition: {str(e)}")


def track_checkout_start(user, session_id, cart_value, items_count):
    """Track checkout initiation"""
    try:
        ConversionFunnel.objects.create(
            user=user,
            session_id=session_id,
            stage='CHECKOUT_START',
            metadata={
                'cart_value': str(cart_value),
                'items_count': items_count,
                'timestamp': timezone.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error tracking checkout start: {str(e)}")


def track_payment_info(user, session_id, payment_method=None):
    """Track payment information entry"""
    try:
        ConversionFunnel.objects.create(
            user=user,
            session_id=session_id,
            stage='PAYMENT_INFO',
            metadata={
                'payment_method': payment_method,
                'timestamp': timezone.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error tracking payment info: {str(e)}")


def track_order_completion(order, user, session_id):
    """Track order completion and update analytics"""
    try:
        today = timezone.now().date()
        
        # Track conversion funnel completion
        ConversionFunnel.objects.create(
            user=user,
            session_id=session_id,
            stage='ORDER_COMPLETE',
            metadata={
                'order_id': order.id,
                'order_value': str(order.total_price),
                'timestamp': timezone.now().isoformat()
            }
        )
        
        # Update product analytics for each item
        for item in order.items.all():
            product_analytics, created = ProductAnalytics.objects.get_or_create(
                product=item.product,
                date=today,
                defaults={'views': 0, 'cart_additions': 0, 'purchases': 0, 'revenue': 0}
            )
            product_analytics.purchases = F('purchases') + item.quantity
            product_analytics.revenue = F('revenue') + (item.unit_price * item.quantity)
            product_analytics.save(update_fields=['purchases', 'revenue'])
        
        # Update customer lifetime value
        update_customer_lifetime_value(user, order)
        
        # Log user activity
        UserActivityLog.objects.create(
            user=user,
            activity_type='ORDER_PLACED',
            details={
                'order_id': order.id,
                'order_value': str(order.total_price),
                'items_count': order.items.count()
            }
        )
        
    except Exception as e:
        logger.error(f"Error tracking order completion: {str(e)}")


def track_cart_abandonment(user, session_id, cart_value, items_count, stage='cart'):
    """Track cart abandonment"""
    try:
        # Check if there's an existing cart creation time
        cart_created = timezone.now() - timezone.timedelta(hours=1)  # Default assumption
        
        # Try to find the earliest cart addition for this session
        earliest_cart_event = ConversionFunnel.objects.filter(
            user=user,
            session_id=session_id,
            stage='CART_ADD'
        ).order_by('timestamp').first()
        
        if earliest_cart_event:
            cart_created = earliest_cart_event.timestamp
        
        CartAbandonmentAnalytics.objects.create(
            user=user,
            session_id=session_id,
            cart_created=cart_created,
            cart_value=cart_value,
            items_count=items_count,
            abandonment_stage=stage
        )
        
    except Exception as e:
        logger.error(f"Error tracking cart abandonment: {str(e)}")


def update_customer_lifetime_value(user, order):
    """Update customer lifetime value metrics"""
    try:
        clv, created = CustomerLifetimeValue.objects.get_or_create(
            user=user,
            defaults={
                'total_orders': 0,
                'total_spent': Decimal('0.00'),
                'avg_order_value': Decimal('0.00'),
                'customer_segment': 'new'
            }
        )
        
        # Update metrics
        clv.total_orders = F('total_orders') + 1
        clv.total_spent = F('total_spent') + order.total_price
        
        # Set first/last order dates
        if not clv.first_order_date:
            clv.first_order_date = order.created_at
        clv.last_order_date = order.created_at
        
        clv.save()
        
        # Refresh from database to get updated values
        clv.refresh_from_db()
        
        # Calculate average order value
        if clv.total_orders > 0:
            clv.avg_order_value = clv.total_spent / clv.total_orders
        
        # Update customer segment based on spending and order frequency
        if clv.total_spent >= 1000:
            clv.customer_segment = 'vip'
        elif clv.total_orders >= 5:
            clv.customer_segment = 'regular'
        elif clv.total_orders >= 2:
            clv.customer_segment = 'returning'
        else:
            clv.customer_segment = 'new'
        
        # Simple LTV prediction (can be enhanced with ML models)
        clv.predicted_ltv = clv.avg_order_value * 12  # Assume 12 orders per year
        
        clv.save(update_fields=['avg_order_value', 'customer_segment', 'predicted_ltv'])
        
    except Exception as e:
        logger.error(f"Error updating customer lifetime value: {str(e)}")


def update_daily_sales_metrics(date=None):
    """Update daily sales metrics (typically run as a daily task)"""
    try:
        if not date:
            date = timezone.now().date()
        
        # This would typically aggregate data from various sources
        # For now, we'll create a placeholder that can be enhanced
        
        sales_metrics, created = SalesMetrics.objects.get_or_create(
            date=date,
            defaults={
                'total_visitors': 0,
                'unique_visitors': 0,
                'conversion_rate': Decimal('0.0000'),
                'cart_abandonment_rate': Decimal('0.0000'),
                'new_customers': 0,
                'returning_customers': 0,
                'customer_acquisition_cost': Decimal('0.00')
            }
        )
        
        # Calculate metrics based on available data
        # This is a simplified version - in production, you'd aggregate from various sources
        
        # Count unique visitors (simplified - would need session tracking)
        daily_activities = UserActivityLog.objects.filter(
            timestamp__date=date
        ).values('user').distinct().count()
        
        sales_metrics.unique_visitors = daily_activities
        sales_metrics.total_visitors = daily_activities  # Simplified
        
        # Count new vs returning customers
        new_customers = CustomerLifetimeValue.objects.filter(
            first_order_date__date=date
        ).count()
        
        returning_customers = CustomerLifetimeValue.objects.filter(
            last_order_date__date=date
        ).exclude(first_order_date__date=date).count()
        
        sales_metrics.new_customers = new_customers
        sales_metrics.returning_customers = returning_customers
        
        # Calculate cart abandonment rate
        total_carts = ConversionFunnel.objects.filter(
            timestamp__date=date,
            stage='CART_ADD'
        ).values('session_id').distinct().count()
        
        completed_orders = ConversionFunnel.objects.filter(
            timestamp__date=date,
            stage='ORDER_COMPLETE'
        ).values('session_id').distinct().count()
        
        if total_carts > 0:
            # Store as decimal (0.25 for 25%) to fit max_digits=5, decimal_places=4
            abandonment_rate = (total_carts - completed_orders) / total_carts
            sales_metrics.cart_abandonment_rate = Decimal(str(round(abandonment_rate, 4)))
            
            conversion_rate = completed_orders / total_carts
            sales_metrics.conversion_rate = Decimal(str(round(conversion_rate, 4)))
        
        sales_metrics.save()
        
    except Exception as e:
        logger.error(f"Error updating daily sales metrics: {str(e)}")


def calculate_product_conversion_rates():
    """Calculate and update product conversion rates"""
    try:
        today = timezone.now().date()
        
        # Get all product analytics for today
        product_analytics = ProductAnalytics.objects.filter(date=today)
        
        for analytics in product_analytics:
            # Calculate conversion rate (purchases / views) as decimal (0.25 for 25%)
            if analytics.views > 0:
                conversion_rate = analytics.purchases / analytics.views
                analytics.conversion_rate = Decimal(str(round(conversion_rate, 4)))
            
            # Calculate cart to purchase rate as decimal (0.25 for 25%)
            if analytics.cart_additions > 0:
                cart_to_purchase_rate = analytics.purchases / analytics.cart_additions
                analytics.cart_to_purchase_rate = Decimal(str(round(cart_to_purchase_rate, 4)))
            
            analytics.save(update_fields=['conversion_rate', 'cart_to_purchase_rate'])
            
    except Exception as e:
        logger.error(f"Error calculating product conversion rates: {str(e)}")
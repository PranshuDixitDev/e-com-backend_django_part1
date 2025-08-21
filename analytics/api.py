from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from .models import (
    UserActivityLog, OrderAnalytics, SearchAnalytics,
    ProductAnalytics, ConversionFunnel, CartAbandonmentAnalytics,
    CustomerLifetimeValue, SalesMetrics
)
from .serializers import (
    UserActivityLogSerializer, OrderAnalyticsSerializer, SearchAnalyticsSerializer,
    ProductAnalyticsSerializer, ConversionFunnelSerializer, CartAbandonmentAnalyticsSerializer,
    CustomerLifetimeValueSerializer, SalesMetricsSerializer
)
from django.contrib.auth import get_user_model
import logging
import hashlib
import hmac

logger = logging.getLogger(__name__)

User = get_user_model()


class IsInternalServicePermission(permissions.BasePermission):
    """Custom permission for internal service communications."""
    
    def has_permission(self, request, view):
        # Check for internal service token in headers
        internal_token = request.META.get('HTTP_X_INTERNAL_TOKEN')
        if not internal_token:
            return False
        
        # Verify the internal token against configured secret
        expected_token = getattr(settings, 'INTERNAL_SERVICE_TOKEN', None)
        if not expected_token:
            return False
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(internal_token, expected_token)


class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def user_activity(self, request):
        """Get user activity logs for the authenticated user."""
        activities = UserActivityLog.objects.filter(user=request.user).order_by('-timestamp')[:50]
        serializer = UserActivityLogSerializer(activities, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def user_activity_summary(self, request):
        """Get user activity summary for the authenticated user."""
        user = request.user
        
        # Get activity counts by type
        activity_summary = UserActivityLog.objects.filter(user=user).values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Get recent activity (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_activities = UserActivityLog.objects.filter(
            user=user,
            timestamp__gte=thirty_days_ago
        ).count()
        
        return Response({
            'activity_summary': list(activity_summary),
            'recent_activities_count': recent_activities,
            'total_activities': UserActivityLog.objects.filter(user=user).count()
        })
    
    @action(detail=False, methods=['get'])
    def order_analytics(self, request):
        """Get order analytics (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied. Admin access required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get date range from query params
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)
        
        analytics = OrderAnalytics.objects.filter(date__gte=start_date).order_by('-date')
        serializer = OrderAnalyticsSerializer(analytics, many=True)
        
        # Calculate totals
        totals = analytics.aggregate(
            total_orders=Sum('total_orders'),
            total_revenue=Sum('total_revenue'),
            total_shipping=Sum('shipping_revenue')
        )
        
        return Response({
            'analytics': serializer.data,
            'totals': totals,
            'period_days': days
        })
    
    @action(detail=False, methods=['get'])
    def search_analytics(self, request):
        """Get search analytics (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied. Admin access required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get popular search queries
        popular_queries = SearchAnalytics.objects.values('query').annotate(
            search_count=Count('id'),
            avg_results=Avg('results_count')
        ).order_by('-search_count')[:20]
        
        # Get recent searches
        recent_searches = SearchAnalytics.objects.order_by('-timestamp')[:50]
        serializer = SearchAnalyticsSerializer(recent_searches, many=True)
        
        return Response({
            'popular_queries': list(popular_queries),
            'recent_searches': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def log_search(self, request):
        """Log a search query for analytics."""
        query = request.data.get('query')
        results_count = request.data.get('results_count', 0)
        category_id = request.data.get('category_id')
        
        if not query:
            return Response(
                {'error': 'Query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        search_analytics = SearchAnalytics.objects.create(
            query=query,
            user=request.user if request.user.is_authenticated else None,
            results_count=results_count,
            category_id=category_id
        )
        
        serializer = SearchAnalyticsSerializer(search_analytics)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get comprehensive dashboard statistics"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied. Admin access required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get date range from query params
            days = int(request.query_params.get('days', 30))
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # User activity stats
            activity_stats = UserActivityLog.objects.filter(
                timestamp__date__range=[start_date, end_date]
            ).values('activity_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Order analytics stats
            order_stats = OrderAnalytics.objects.filter(
                date__range=[start_date, end_date]
            ).aggregate(
                total_orders=Sum('total_orders'),
                total_revenue=Sum('total_revenue'),
                avg_order_value=Avg('avg_order_value')
            )
            
            # Search analytics stats
            search_stats = SearchAnalytics.objects.filter(
                timestamp__date__range=[start_date, end_date]
            ).values('query').annotate(
                search_count=Count('id')
            ).order_by('-search_count')[:10]
            
            # Recent activity
            recent_activity = UserActivityLog.objects.filter(
                timestamp__date__range=[start_date, end_date]
            ).select_related('user').order_by('-timestamp')[:20]
            
            return Response({
                'status': 'success',
                'data': {
                    'period': {
                        'start_date': start_date,
                        'end_date': end_date,
                        'days': days
                    },
                    'activity_stats': list(activity_stats),
                    'order_stats': order_stats,
                    'top_searches': list(search_stats),
                    'recent_activity': UserActivityLogSerializer(recent_activity, many=True).data
                }
            })
        except Exception as e:
            logger.error(f"Error fetching dashboard stats: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch dashboard statistics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def product_analytics(self, request):
        """Get product performance analytics"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied. Admin access required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            days = int(request.query_params.get('days', 30))
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            analytics = ProductAnalytics.objects.filter(
                date__range=[start_date, end_date]
            ).select_related('product').order_by('-revenue')
            
            return Response({
                'status': 'success',
                'data': ProductAnalyticsSerializer(analytics, many=True).data
            })
        except Exception as e:
            logger.error(f"Error fetching product analytics: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch product analytics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def conversion_funnel(self, request):
        """Get conversion funnel analytics"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied. Admin access required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            days = int(request.query_params.get('days', 30))
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Get funnel stage counts
            funnel_data = ConversionFunnel.objects.filter(
                timestamp__date__range=[start_date, end_date]
            ).values('stage').annotate(
                count=Count('id'),
                unique_users=Count('user', distinct=True)
            ).order_by('stage')
            
            # Calculate conversion rates between stages
            stages = ['PRODUCT_VIEW', 'CART_ADD', 'CHECKOUT_START', 'PAYMENT_INFO', 'ORDER_COMPLETE']
            funnel_stats = []
            
            for i, stage_data in enumerate(funnel_data):
                stage_info = {
                    'stage': stage_data['stage'],
                    'count': stage_data['count'],
                    'unique_users': stage_data['unique_users'],
                    'conversion_rate': 0
                }
                
                if i > 0 and len(funnel_stats) > 0:
                    previous_count = funnel_stats[i-1]['count']
                    if previous_count > 0:
                        stage_info['conversion_rate'] = round(
                            (stage_data['count'] / previous_count) * 100, 2
                        )
                
                funnel_stats.append(stage_info)
            
            return Response({
                'status': 'success',
                'data': {
                    'funnel_stats': funnel_stats,
                    'period': {'start_date': start_date, 'end_date': end_date}
                }
            })
        except Exception as e:
            logger.error(f"Error fetching conversion funnel: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch conversion funnel data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def cart_abandonment(self, request):
        """Get cart abandonment analytics"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied. Admin access required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            days = int(request.query_params.get('days', 30))
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            abandonment_data = CartAbandonmentAnalytics.objects.filter(
                cart_abandoned__date__range=[start_date, end_date]
            ).select_related('user')
            
            # Calculate abandonment stats
            total_abandonments = abandonment_data.count()
            recovered_carts = abandonment_data.filter(recovered=True).count()
            recovery_rate = round((recovered_carts / total_abandonments * 100), 2) if total_abandonments > 0 else 0
            
            # Abandonment by stage
            stage_stats = abandonment_data.values('abandonment_stage').annotate(
                count=Count('id'),
                avg_value=Avg('cart_value')
            ).order_by('-count')
            
            return Response({
                'status': 'success',
                'data': {
                    'summary': {
                        'total_abandonments': total_abandonments,
                        'recovered_carts': recovered_carts,
                        'recovery_rate': recovery_rate,
                        'avg_abandoned_value': abandonment_data.aggregate(
                            avg=Avg('cart_value')
                        )['avg'] or 0
                    },
                    'stage_breakdown': list(stage_stats),
                    'recent_abandonments': CartAbandonmentAnalyticsSerializer(
                        abandonment_data.order_by('-cart_abandoned')[:20], many=True
                    ).data
                }
            })
        except Exception as e:
            logger.error(f"Error fetching cart abandonment data: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch cart abandonment data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def customer_lifetime_value(self, request):
        """Get customer lifetime value analytics"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied. Admin access required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            segment = request.query_params.get('segment', None)
            
            clv_queryset = CustomerLifetimeValue.objects.select_related('user')
            
            if segment:
                clv_queryset = clv_queryset.filter(customer_segment=segment)
            
            # Get top customers by LTV
            top_customers = clv_queryset.order_by('-total_spent')[:50]
            
            # Segment breakdown
            segment_stats = CustomerLifetimeValue.objects.values('customer_segment').annotate(
                count=Count('id'),
                avg_ltv=Avg('total_spent'),
                avg_orders=Avg('total_orders'),
                avg_order_value=Avg('avg_order_value')
            ).order_by('-avg_ltv')
            
            return Response({
                'status': 'success',
                'data': {
                    'top_customers': CustomerLifetimeValueSerializer(top_customers, many=True).data,
                    'segment_breakdown': list(segment_stats),
                    'overall_stats': CustomerLifetimeValue.objects.aggregate(
                        total_customers=Count('id'),
                        avg_ltv=Avg('total_spent'),
                        total_revenue=Sum('total_spent')
                    )
                }
            })
        except Exception as e:
            logger.error(f"Error fetching CLV data: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch customer lifetime value data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def sales_metrics(self, request):
        """Get comprehensive sales metrics"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied. Admin access required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            days = int(request.query_params.get('days', 30))
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            metrics = SalesMetrics.objects.filter(
                date__range=[start_date, end_date]
            ).order_by('-date')
            
            # Calculate trends
            total_metrics = metrics.aggregate(
                total_visitors=Sum('total_visitors'),
                total_unique_visitors=Sum('unique_visitors'),
                avg_conversion_rate=Avg('conversion_rate'),
                avg_abandonment_rate=Avg('cart_abandonment_rate'),
                total_new_customers=Sum('new_customers'),
                total_returning_customers=Sum('returning_customers')
            )
            
            return Response({
                'status': 'success',
                'data': {
                    'daily_metrics': SalesMetricsSerializer(metrics, many=True).data,
                    'summary': total_metrics,
                    'period': {'start_date': start_date, 'end_date': end_date}
                }
            })
        except Exception as e:
            logger.error(f"Error fetching sales metrics: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to fetch sales metrics'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def track_conversion_event(self, request):
        """Track conversion funnel events"""
        try:
            stage = request.data.get('stage')
            session_id = request.data.get('session_id')
            product_id = request.data.get('product_id')
            metadata = request.data.get('metadata', {})
            
            if not stage or not session_id:
                return Response({
                    'status': 'error',
                    'message': 'Stage and session_id are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate stage
            valid_stages = [choice[0] for choice in ConversionFunnel.FUNNEL_STAGES]
            if stage not in valid_stages:
                return Response({
                    'status': 'error',
                    'message': f'Invalid stage. Must be one of: {valid_stages}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Create conversion event
            conversion_event = ConversionFunnel.objects.create(
                user=request.user,
                session_id=session_id,
                stage=stage,
                product_id=product_id,
                metadata=metadata
            )
            
            return Response({
                'status': 'success',
                'message': 'Conversion event tracked successfully',
                'data': ConversionFunnelSerializer(conversion_event).data
            })
        except Exception as e:
            logger.error(f"Error tracking conversion event: {str(e)}")
            return Response({
                'status': 'error',
                'message': 'Failed to track conversion event'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminNotificationView(APIView):
    """Secure endpoint to receive admin notifications about system events."""
    permission_classes = [IsInternalServicePermission]
    
    # Supported event types for validation
    SUPPORTED_EVENT_TYPES = {
        'email_verification': 'EMAIL_VERIFICATION',
        'password_reset': 'PASSWORD_RESET',
        'password_reset_email_sent': 'PASSWORD_RESET_EMAIL_SENT',
        'password_reset_email_failed': 'PASSWORD_RESET_EMAIL_FAILED',
        'account_locked': 'ACCOUNT_LOCKED',
        'suspicious_activity': 'SUSPICIOUS_ACTIVITY'
    }
    
    def post(self, request):
        """Receive and process admin notifications with enhanced security and validation."""
        try:
            data = request.data
            
            # Validate required fields
            required_fields = ['event_type', 'user_id', 'message']
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                logger.warning(f"Admin notification missing required fields: {missing_fields}")
                return Response({
                    'status': 'error',
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            event_type = data.get('event_type')
            user_id = data.get('user_id')
            message = data.get('message')
            
            # Validate event type
            if event_type not in self.SUPPORTED_EVENT_TYPES:
                logger.warning(f"Unsupported event type received: {event_type}")
                return Response({
                    'status': 'error',
                    'message': f'Unsupported event type: {event_type}. Supported types: {", ".join(self.SUPPORTED_EVENT_TYPES.keys())}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate user exists
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                logger.warning(f"User with ID {user_id} not found for admin notification")
                return Response({
                    'status': 'error',
                    'message': f'User with ID {user_id} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            except ValueError:
                logger.warning(f"Invalid user ID format: {user_id}")
                return Response({
                    'status': 'error',
                    'message': 'Invalid user ID format'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Process the notification
            activity_type = self.SUPPORTED_EVENT_TYPES[event_type]
            
            # Log to system logs with structured data
            logger.info(
                f"Admin Notification - {activity_type}: {message}", 
                extra={
                    'event_type': event_type,
                    'user_id': user_id,
                    'username': user.username,
                    'email': user.email
                }
            )
            
            # Create user activity log entry with enhanced details
            UserActivityLog.objects.create(
                user=user,
                activity_type=activity_type,
                details={
                    'notification_type': event_type,
                    'username': user.username,
                    'email': user.email,
                    'message': message,
                    'timestamp': data.get('timestamp', timezone.now().isoformat()),
                    'admin_notified': True,
                    'source': 'internal_notification_system'
                }
            )
            
            return Response({
                'status': 'success',
                'message': 'Admin notification received and processed successfully',
                'event_type': event_type,
                'user_id': user_id
            }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(
                f"Error processing admin notification: {str(e)}", 
                extra={'request_data': request.data},
                exc_info=True
            )
            return Response({
                'status': 'error',
                'message': 'Internal server error while processing notification'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
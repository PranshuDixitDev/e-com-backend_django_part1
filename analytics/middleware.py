import json
import time
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from .models import APIEvent
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class APITrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track API events with comprehensive details including
    user information, IP address, request details, and performance metrics.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        # Store the start time for response time calculation
        request._api_tracking_start_time = time.time()
        
        # Store request size
        request._api_tracking_request_size = len(request.body) if hasattr(request, 'body') else 0
        
        return None
    
    def process_response(self, request, response):
        # Only track API endpoints (you can customize this logic)
        if self._should_track_request(request):
            self._track_api_event(request, response)
        
        return response
    
    def process_exception(self, request, exception):
        # Track failed requests due to exceptions
        if self._should_track_request(request):
            self._track_api_event(request, None, exception=exception)
        
        return None
    
    def _should_track_request(self, request):
        """
        Determine if this request should be tracked.
        Customize this method based on your needs.
        """
        # Skip admin static files and media files
        if request.path.startswith('/admin/jsi18n/') or \
           request.path.startswith('/static/') or \
           request.path.startswith('/media/'):
            return False
        
        # Track API endpoints (customize based on your URL patterns)
        api_patterns = ['/api/', '/admin/', '/auth/']
        return any(request.path.startswith(pattern) for pattern in api_patterns)
    
    def _get_client_ip(self, request):
        """
        Get the client's IP address from the request.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _get_user_agent(self, request):
        """
        Get the user agent from the request.
        """
        return request.META.get('HTTP_USER_AGENT', '')
    
    def _get_referer(self, request):
        """
        Get the referer URL from the request.
        """
        return request.META.get('HTTP_REFERER')
    
    def _get_session_id(self, request):
        """
        Get the session ID from the request.
        """
        if hasattr(request, 'session') and request.session.session_key:
            return request.session.session_key
        return None
    
    def _sanitize_request_data(self, request):
        """
        Sanitize request data by removing sensitive information.
        """
        try:
            # Get request data based on method
            if request.method in ['POST', 'PUT', 'PATCH']:
                if hasattr(request, 'body') and request.body:
                    try:
                        data = json.loads(request.body.decode('utf-8'))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # If it's not JSON, store as string (truncated)
                        data = request.body.decode('utf-8', errors='ignore')[:1000]
                else:
                    data = dict(request.POST)
            elif request.method == 'GET':
                data = dict(request.GET)
            else:
                data = {}
            
            # Remove sensitive fields
            sensitive_fields = [
                'password', 'token', 'secret', 'key', 'authorization',
                'csrf_token', 'csrfmiddlewaretoken', 'api_key'
            ]
            
            if isinstance(data, dict):
                for field in sensitive_fields:
                    if field in data:
                        data[field] = '[REDACTED]'
                    # Also check for case variations
                    for key in list(data.keys()):
                        if any(sensitive in key.lower() for sensitive in sensitive_fields):
                            data[key] = '[REDACTED]'
            
            return data
        except Exception as e:
            logger.warning(f"Error sanitizing request data: {e}")
            return {'error': 'Could not parse request data'}
    
    def _track_api_event(self, request, response=None, exception=None):
        """
        Create an APIEvent record with comprehensive tracking information.
        """
        # Skip API event tracking during tests to prevent transaction management errors
        if getattr(settings, 'TESTING', False):
            return
            
        try:
            # Calculate response time
            response_time = None
            if hasattr(request, '_api_tracking_start_time'):
                response_time = (time.time() - request._api_tracking_start_time) * 1000  # Convert to milliseconds
            
            # Determine status
            if exception:
                status = 'failure'
                error_message = str(exception)
                response_status_code = 500
            elif response:
                status = 'success' if 200 <= response.status_code < 400 else 'failure'
                error_message = None if status == 'success' else f"HTTP {response.status_code}"
                response_status_code = response.status_code
            else:
                status = 'failure'
                error_message = 'Unknown error'
                response_status_code = None
            
            # Get response size
            response_size = None
            if response and hasattr(response, 'content'):
                response_size = len(response.content)
            
            # Create the API event
            api_event = APIEvent.objects.create(
                timestamp=timezone.now(),
                status=status,
                endpoint=request.path,
                response_time=response_time,
                user=request.user if request.user.is_authenticated else None,
                ip_address=self._get_client_ip(request),
                user_agent=self._get_user_agent(request),
                request_method=request.method,
                request_data=self._sanitize_request_data(request),
                response_status_code=response_status_code,
                error_message=error_message,
                session_id=self._get_session_id(request),
                referer=self._get_referer(request),
                request_size=getattr(request, '_api_tracking_request_size', None),
                response_size=response_size
            )
            
            # Log for debugging (optional)
            logger.debug(f"API Event tracked: {api_event}")
            
        except Exception as e:
            # Don't let tracking errors break the application
            logger.error(f"Error tracking API event: {e}")
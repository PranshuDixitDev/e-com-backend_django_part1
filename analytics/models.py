# analytics/models.py
from django.db import models
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

class APIEvent(models.Model):
    STATUS_CHOICES = (
        ('success', 'Success'),
        ('failure', 'Failure'),
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    endpoint = models.CharField(max_length=255, blank=True, null=True)
    response_time = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"{self.status} at {self.timestamp}"

    class Meta:
        verbose_name = "API Event"
        verbose_name_plural = "API Events"
        ordering = ['-timestamp']

class UserSession(models.Model):
    user_id = models.CharField(max_length=255)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Session for {self.user_id} from {self.start_time} to {self.end_time}"

    class Meta:
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"
        ordering = ['-start_time']

class PageView(models.Model):
    user_session = models.ForeignKey(UserSession, on_delete=models.CASCADE)
    page_url = models.URLField()
    timestamp = models.DateTimeField(auto_now_add=True)
    duration = models.FloatField(blank=True, null=True)  # Duration in seconds

    def __str__(self):
        return f"Page view of {self.page_url} at {self.timestamp}"

    class Meta:
        verbose_name = "Page View"
        verbose_name_plural = "Page Views"
        ordering = ['-timestamp']

class ClickEvent(models.Model):
    user_session = models.ForeignKey(UserSession, on_delete=models.CASCADE)
    element_id = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    x_position = models.FloatField(blank=True, null=True)
    y_position = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"Click on {self.element_id} at {self.timestamp}"

    class Meta:
        verbose_name = "Click Event"
        verbose_name_plural = "Click Events"
        ordering = ['-timestamp']

class FormSubmission(models.Model):
    user_session = models.ForeignKey(UserSession, on_delete=models.CASCADE)
    form_id = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    form_data = models.JSONField(blank=True, null=True)  # Store form data as JSON

    def __str__(self):
        return f"Form {self.form_id} submitted at {self.timestamp}"

    class Meta:
        verbose_name = "Form Submission"
        verbose_name_plural = "Form Submissions"
        ordering = ['-timestamp']

class SearchQuery(models.Model):
    user_session = models.ForeignKey(UserSession, on_delete=models.CASCADE)
    query = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    results_count = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"Search query '{self.query}' at {self.timestamp}"

    class Meta:
        verbose_name = "Search Query"
        verbose_name_plural = "Search Queries"
        ordering = ['-timestamp']

class UserFeedback(models.Model):
    user_session = models.ForeignKey(UserSession, on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=255)
    feedback_text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback '{self.feedback_type}' at {self.timestamp}"

    class Meta:
        verbose_name = "User Feedback"
        verbose_name_plural = "User Feedbacks"
        ordering = ['-timestamp']

class UserProfile(models.Model):
    user_id = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.first_name} {self.last_name} ({self.user_id})"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ['-date_joined']

class UserPreference(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    preference_key = models.CharField(max_length=255)
    preference_value = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Preference {self.preference_key} for {self.user_profile}"

    class Meta:
        verbose_name = "User Preference"
        verbose_name_plural = "User Preferences"
        ordering = ['-timestamp']

class UserNotification(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user_profile}: {self.message}"

    class Meta:
        verbose_name = "User Notification"
        verbose_name_plural = "User Notifications"
        ordering = ['-timestamp']

class UserInteraction(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Interaction {self.interaction_type} for {self.user_profile} at {self.timestamp}"

    class Meta:
        verbose_name = "User Interaction"
        verbose_name_plural = "User Interactions"
        ordering = ['-timestamp']

class UserEngagement(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    engagement_type = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    duration = models.FloatField(blank=True, null=True)  # Duration in seconds

    def __str__(self):
        return f"Engagement {self.engagement_type} for {self.user_profile} at {self.timestamp}"

    class Meta:
        verbose_name = "User Engagement"
        verbose_name_plural = "User Engagements"
        ordering = ['-timestamp']

class UserBehavior(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    behavior_type = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Behavior {self.behavior_type} for {self.user_profile} at {self.timestamp}"

    class Meta:
        verbose_name = "User Behavior"
        verbose_name_plural = "User Behaviors"
        ordering = ['-timestamp']

class UserPreferenceChange(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    preference_key = models.CharField(max_length=255)
    old_value = models.TextField()
    new_value = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Preference change {self.preference_key} for {self.user_profile} at {self.timestamp}"

    class Meta:
        verbose_name = "User Preference Change"
        verbose_name_plural = "User Preference Changes"
        ordering = ['-timestamp']

class UserLogin(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    login_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Login for {self.user_profile} at {self.login_time}"

    class Meta:
        verbose_name = "User Login"
        verbose_name_plural = "User Logins"
        ordering = ['-login_time']

class UserLogout(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    logout_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Logout for {self.user_profile} at {self.logout_time}"

    class Meta:
        verbose_name = "User Logout"
        verbose_name_plural = "User Logouts"
        ordering = ['-logout_time']

class UserRegistration(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    registration_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Registration for {self.user_profile} at {self.registration_time}"

    class Meta:
        verbose_name = "User Registration"
        verbose_name_plural = "User Registrations"
        ordering = ['-registration_time']

class UserProfileUpdate(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    update_time = models.DateTimeField(auto_now_add=True)
    updated_fields = models.TextField()  # Store updated fields as JSON or text

    def __str__(self):
        return f"Profile update for {self.user_profile} at {self.update_time}"

    class Meta:
        verbose_name = "User Profile Update"
        verbose_name_plural = "User Profile Updates"
        ordering = ['-update_time']

class UserPasswordReset(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    reset_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    reset_token = models.CharField(max_length=255)

    def __str__(self):
        return f"Password reset for {self.user_profile} at {self.reset_time}"

    class Meta:
        verbose_name = "User Password Reset"
        verbose_name_plural = "User Password Resets"
        ordering = ['-reset_time']

class UserPasswordChange(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    change_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    old_password_hash = models.CharField(max_length=255)
    new_password_hash = models.CharField(max_length=255)

    def __str__(self):
        return f"Password change for {self.user_profile} at {self.change_time}"

    class Meta:
        verbose_name = "User Password Change"
        verbose_name_plural = "User Password Changes"
        ordering = ['-change_time']

class UserAccountDeactivation(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    deactivation_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Account deactivation for {self.user_profile} at {self.deactivation_time}"

    class Meta:
        verbose_name = "User Account Deactivation"
        verbose_name_plural = "User Account Deactivations"
        ordering = ['-deactivation_time']

class UserAccountReactivation(models.Model):
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    reactivation_time = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Account reactivation for {self.user_profile} at {self.reactivation_time}"

    class Meta:
        verbose_name = "User Account Reactivation"
        verbose_name_plural = "User Account Reactivations"
        ordering = ['-reactivation_time']

class UserActivity(models.Model):
    user_id = models.CharField(max_length=255)
    activity_type = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user_id} - {self.activity_type} at {self.timestamp}"

    class Meta:
        verbose_name = "User Activity"
        verbose_name_plural = "User Activities"
        ordering = ['-timestamp']

class ErrorLog(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField()
    endpoint = models.CharField(max_length=255, blank=True, null=True)
    stack_trace = models.TextField(blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Error at {self.timestamp}: {self.error_message}"

    class Meta:
        verbose_name = "Error Log"
        verbose_name_plural = "Error Logs"
        ordering = ['-timestamp']

class OrderAnalytics(models.Model):
    """Track daily order metrics"""
    date = models.DateField(unique=True)
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Order Analytics"
        verbose_name_plural = "Order Analytics"
        ordering = ['-date']

class UserActivityLog(models.Model):
    """Track user activity"""
    ACTIVITY_TYPES = (
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('CART_ADD', 'Add to Cart'),
        ('CART_REMOVE', 'Remove from Cart'),
        ('ORDER_PLACED', 'Order Placed'),
        ('PAYMENT', 'Payment Made'),
        ('PROFILE_UPDATE', 'Profile Updated'),
        ('ADDRESS_ADD', 'Address Added'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    details = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = "User Activity Log"
        verbose_name_plural = "User Activity Logs"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'activity_type', 'timestamp'])
        ]

class SearchAnalytics(models.Model):
    """Track search patterns"""
    query = models.CharField(max_length=255)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    results_count = models.IntegerField()
    category = models.ForeignKey(
        'categories.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Search Analytics"
        verbose_name_plural = "Search Analytics"
        ordering = ['-timestamp']
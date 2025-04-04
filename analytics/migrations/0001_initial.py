# Generated by Django 5.0.6 on 2025-03-29 10:37

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('categories', '0006_alter_category_options_category_slug'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='APIEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('success', 'Success'), ('failure', 'Failure')], max_length=10)),
                ('endpoint', models.CharField(blank=True, max_length=255, null=True)),
                ('response_time', models.FloatField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'API Event',
                'verbose_name_plural': 'API Events',
            },
        ),
        migrations.CreateModel(
            name='OrderAnalytics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('total_orders', models.IntegerField(default=0)),
                ('total_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('avg_order_value', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('shipping_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ],
            options={
                'verbose_name': 'Order Analytics',
                'verbose_name_plural': 'Order Analytics',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='UserActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(max_length=255)),
                ('activity_type', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('details', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'User Activity',
                'verbose_name_plural': 'User Activities',
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(max_length=255)),
                ('first_name', models.CharField(blank=True, max_length=255, null=True)),
                ('last_name', models.CharField(blank=True, max_length=255, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('profile_picture', models.ImageField(blank=True, null=True, upload_to='profile_pictures/')),
            ],
            options={
                'verbose_name': 'User Profile',
                'verbose_name_plural': 'User Profiles',
            },
        ),
        migrations.CreateModel(
            name='UserSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(max_length=255)),
                ('start_time', models.DateTimeField(auto_now_add=True)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'verbose_name': 'User Session',
                'verbose_name_plural': 'User Sessions',
            },
        ),
        migrations.CreateModel(
            name='ErrorLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('error_message', models.TextField()),
                ('endpoint', models.CharField(blank=True, max_length=255, null=True)),
                ('stack_trace', models.TextField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Error Log',
                'verbose_name_plural': 'Error Logs',
            },
        ),
        migrations.CreateModel(
            name='SearchAnalytics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('results_count', models.IntegerField()),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='categories.category')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Search Analytics',
                'verbose_name_plural': 'Search Analytics',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='UserPreferenceChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('preference_key', models.CharField(max_length=255)),
                ('old_value', models.TextField()),
                ('new_value', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Preference Change',
                'verbose_name_plural': 'User Preference Changes',
            },
        ),
        migrations.CreateModel(
            name='UserPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('preference_key', models.CharField(max_length=255)),
                ('preference_value', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Preference',
                'verbose_name_plural': 'User Preferences',
            },
        ),
        migrations.CreateModel(
            name='UserPasswordReset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reset_time', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255, null=True)),
                ('reset_token', models.CharField(max_length=255)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Password Reset',
                'verbose_name_plural': 'User Password Resets',
            },
        ),
        migrations.CreateModel(
            name='UserPasswordChange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('change_time', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255, null=True)),
                ('old_password_hash', models.CharField(max_length=255)),
                ('new_password_hash', models.CharField(max_length=255)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Password Change',
                'verbose_name_plural': 'User Password Changes',
            },
        ),
        migrations.CreateModel(
            name='UserNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('is_read', models.BooleanField(default=False)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Notification',
                'verbose_name_plural': 'User Notifications',
            },
        ),
        migrations.CreateModel(
            name='UserLogout',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('logout_time', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255, null=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Logout',
                'verbose_name_plural': 'User Logouts',
            },
        ),
        migrations.CreateModel(
            name='UserLogin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('login_time', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255, null=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Login',
                'verbose_name_plural': 'User Logins',
            },
        ),
        migrations.CreateModel(
            name='UserInteraction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('interaction_type', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('details', models.TextField(blank=True, null=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Interaction',
                'verbose_name_plural': 'User Interactions',
            },
        ),
        migrations.CreateModel(
            name='UserEngagement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('engagement_type', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('duration', models.FloatField(blank=True, null=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Engagement',
                'verbose_name_plural': 'User Engagements',
            },
        ),
        migrations.CreateModel(
            name='UserBehavior',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('behavior_type', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('details', models.TextField(blank=True, null=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Behavior',
                'verbose_name_plural': 'User Behaviors',
            },
        ),
        migrations.CreateModel(
            name='UserAccountReactivation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reactivation_time', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255, null=True)),
                ('reason', models.TextField(blank=True, null=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Account Reactivation',
                'verbose_name_plural': 'User Account Reactivations',
            },
        ),
        migrations.CreateModel(
            name='UserAccountDeactivation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deactivation_time', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255, null=True)),
                ('reason', models.TextField(blank=True, null=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Account Deactivation',
                'verbose_name_plural': 'User Account Deactivations',
            },
        ),
        migrations.CreateModel(
            name='UserProfileUpdate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('update_time', models.DateTimeField(auto_now_add=True)),
                ('updated_fields', models.TextField()),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Profile Update',
                'verbose_name_plural': 'User Profile Updates',
            },
        ),
        migrations.CreateModel(
            name='UserRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('registration_time', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=255, null=True)),
                ('user_profile', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.userprofile')),
            ],
            options={
                'verbose_name': 'User Registration',
                'verbose_name_plural': 'User Registrations',
            },
        ),
        migrations.CreateModel(
            name='UserFeedback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feedback_type', models.CharField(max_length=255)),
                ('feedback_text', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('user_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.usersession')),
            ],
            options={
                'verbose_name': 'User Feedback',
                'verbose_name_plural': 'User Feedbacks',
            },
        ),
        migrations.CreateModel(
            name='SearchQuery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('results_count', models.IntegerField(blank=True, null=True)),
                ('user_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.usersession')),
            ],
            options={
                'verbose_name': 'Search Query',
                'verbose_name_plural': 'Search Queries',
            },
        ),
        migrations.CreateModel(
            name='PageView',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_url', models.URLField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('duration', models.FloatField(blank=True, null=True)),
                ('user_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.usersession')),
            ],
            options={
                'verbose_name': 'Page View',
                'verbose_name_plural': 'Page Views',
            },
        ),
        migrations.CreateModel(
            name='FormSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('form_id', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('form_data', models.JSONField(blank=True, null=True)),
                ('user_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.usersession')),
            ],
            options={
                'verbose_name': 'Form Submission',
                'verbose_name_plural': 'Form Submissions',
            },
        ),
        migrations.CreateModel(
            name='ClickEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('element_id', models.CharField(max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('x_position', models.FloatField(blank=True, null=True)),
                ('y_position', models.FloatField(blank=True, null=True)),
                ('user_session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analytics.usersession')),
            ],
            options={
                'verbose_name': 'Click Event',
                'verbose_name_plural': 'Click Events',
            },
        ),
        migrations.CreateModel(
            name='UserActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_type', models.CharField(choices=[('LOGIN', 'Login'), ('LOGOUT', 'Logout'), ('CART_ADD', 'Add to Cart'), ('CART_REMOVE', 'Remove from Cart'), ('ORDER_PLACED', 'Order Placed'), ('PAYMENT', 'Payment Made'), ('PROFILE_UPDATE', 'Profile Updated'), ('ADDRESS_ADD', 'Address Added')], max_length=20)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('details', models.JSONField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Activity Log',
                'verbose_name_plural': 'User Activity Logs',
                'ordering': ['-timestamp'],
                'indexes': [models.Index(fields=['user', 'activity_type', 'timestamp'], name='analytics_u_user_id_0a0423_idx')],
            },
        ),
    ]

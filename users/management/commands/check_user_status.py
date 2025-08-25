from django.core.management.base import BaseCommand
from users.models import CustomUser

class Command(BaseCommand):
    help = 'Check and display user status for password reset eligibility'
    
    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='User email to check')
        parser.add_argument('--update', action='store_true', help='Update user to be eligible for password reset')
    
    def handle(self, *args, **options):
        email = options['email']
        
        try:
            user = CustomUser.objects.get(email=email)
            
            self.stdout.write(f"\nUser Status for {email}:")
            self.stdout.write(f"- is_active: {user.is_active}")
            self.stdout.write(f"- is_email_verified: {user.is_email_verified}")
            self.stdout.write(f"- email_sent: {user.email_sent}")
            self.stdout.write(f"- email_failed: {user.email_failed}")
            self.stdout.write(f"- password_reset_attempts: {user.password_reset_attempts}")
            self.stdout.write(f"- password_reset_email_sent: {user.password_reset_email_sent}")
            self.stdout.write(f"- password_reset_email_failed: {user.password_reset_email_failed}")
            
            # Check eligibility
            eligible = (
                user.is_active and 
                user.is_email_verified and 
                user.email_sent and 
                not user.email_failed and 
                user.password_reset_attempts < 5
            )
            
            self.stdout.write(f"\nPassword Reset Eligible: {eligible}")
            
            if not eligible:
                self.stdout.write("\nReasons for ineligibility:")
                if not user.is_active:
                    self.stdout.write("- User is not active")
                if not user.is_email_verified:
                    self.stdout.write("- Email is not verified")
                if not user.email_sent:
                    self.stdout.write("- Email was not sent")
                if user.email_failed:
                    self.stdout.write("- Email sending failed")
                if user.password_reset_attempts >= 5:
                    self.stdout.write("- Too many password reset attempts")
            
            if options['update'] and not eligible:
                self.stdout.write("\nUpdating user to be eligible...")
                user.is_active = True
                user.is_email_verified = True
                user.email_sent = True
                user.email_failed = False
                user.password_reset_attempts = 0
                user.save()
                self.stdout.write(self.style.SUCCESS("User updated successfully!"))
                
        except CustomUser.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with email {email} not found"))
from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.signals import run_daily_analytics_tasks
from analytics.utils import (
    update_daily_sales_metrics, calculate_product_conversion_rates
)
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run daily analytics calculations and updates'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Specific date to run analytics for (YYYY-MM-DD format)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation even if data already exists',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
    
    def handle(self, *args, **options):
        if options['verbose']:
            self.stdout.write('Starting daily analytics calculations...')
        
        try:
            # Determine the date to process
            if options['date']:
                from datetime import datetime
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            else:
                target_date = timezone.now().date()
            
            if options['verbose']:
                self.stdout.write(f'Processing analytics for date: {target_date}')
            
            # Run daily analytics tasks
            run_daily_analytics_tasks()
            
            # Update sales metrics for the specific date
            update_daily_sales_metrics(target_date)
            
            # Calculate product conversion rates
            calculate_product_conversion_rates()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully completed daily analytics for {target_date}'
                )
            )
            
        except Exception as e:
            logger.error(f'Error running daily analytics: {str(e)}')
            self.stdout.write(
                self.style.ERROR(
                    f'Failed to run daily analytics: {str(e)}'
                )
            )
            raise
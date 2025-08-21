from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from analytics.models import (
    UserActivityLog, OrderAnalytics, ProductAnalytics,
    ConversionFunnel, CartAbandonmentAnalytics,
    CustomerLifetimeValue, SalesMetrics, SearchAnalytics
)
from datetime import datetime, timedelta
import json
import csv
import os


class Command(BaseCommand):
    help = 'Generate comprehensive analytics reports'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for report (YYYY-MM-DD format)',
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for report (YYYY-MM-DD format)',
        )
        parser.add_argument(
            '--format',
            choices=['json', 'csv', 'console'],
            default='console',
            help='Output format for the report',
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output file path (for json/csv formats)',
        )
        parser.add_argument(
            '--report-type',
            choices=['summary', 'detailed', 'sales', 'user-behavior', 'products'],
            default='summary',
            help='Type of report to generate',
        )
    
    def handle(self, *args, **options):
        # Determine date range
        if options['start_date']:
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date() - timedelta(days=30)
        
        if options['end_date']:
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
        
        self.stdout.write(f'Generating {options["report_type"]} report from {start_date} to {end_date}')
        
        # Generate report based on type
        if options['report_type'] == 'summary':
            report_data = self.generate_summary_report(start_date, end_date)
        elif options['report_type'] == 'detailed':
            report_data = self.generate_detailed_report(start_date, end_date)
        elif options['report_type'] == 'sales':
            report_data = self.generate_sales_report(start_date, end_date)
        elif options['report_type'] == 'user-behavior':
            report_data = self.generate_user_behavior_report(start_date, end_date)
        elif options['report_type'] == 'products':
            report_data = self.generate_products_report(start_date, end_date)
        
        # Output report
        self.output_report(report_data, options)
    
    def generate_summary_report(self, start_date, end_date):
        """Generate a summary analytics report."""
        # Order analytics
        order_stats = OrderAnalytics.objects.filter(
            date__range=[start_date, end_date]
        ).aggregate(
            total_orders=Sum('total_orders'),
            total_revenue=Sum('total_revenue'),
            avg_order_value=Avg('avg_order_value'),
            total_shipping=Sum('shipping_revenue')
        )
        
        # User activity stats
        user_activity = UserActivityLog.objects.filter(
            timestamp__date__range=[start_date, end_date]
        ).values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Sales metrics
        sales_stats = SalesMetrics.objects.filter(
            date__range=[start_date, end_date]
        ).aggregate(
            total_visitors=Sum('total_visitors'),
            unique_visitors=Sum('unique_visitors'),
            avg_conversion_rate=Avg('conversion_rate'),
            avg_cart_abandonment_rate=Avg('cart_abandonment_rate'),
            total_new_customers=Sum('new_customers'),
            total_returning_customers=Sum('returning_customers'),
            avg_customer_acquisition_cost=Avg('customer_acquisition_cost')
        )
        
        # Cart abandonment rate
        cart_abandonment = CartAbandonmentAnalytics.objects.filter(
            cart_abandoned__date__range=[start_date, end_date]
        ).aggregate(
            total_abandoned=Count('id'),
            avg_cart_value=Avg('cart_value')
        )
        
        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'orders': order_stats,
            'user_activity': list(user_activity),
            'sales': {
                'total_visitors': sales_stats['total_visitors'] or 0,
                'unique_visitors': sales_stats['unique_visitors'] or 0,
                'avg_conversion_rate': float(sales_stats['avg_conversion_rate'] or 0),
                'avg_cart_abandonment_rate': float(sales_stats['avg_cart_abandonment_rate'] or 0),
                'total_new_customers': sales_stats['total_new_customers'] or 0,
                'total_returning_customers': sales_stats['total_returning_customers'] or 0,
                'avg_customer_acquisition_cost': float(sales_stats['avg_customer_acquisition_cost'] or 0),
            },
            'cart_abandonment': cart_abandonment,
            'generated_at': timezone.now().isoformat()
        }
    
    def generate_detailed_report(self, start_date, end_date):
        """Generate a detailed analytics report."""
        summary = self.generate_summary_report(start_date, end_date)
        
        # Add detailed breakdowns
        # Top products
        top_products = ProductAnalytics.objects.filter(
            date__range=[start_date, end_date]
        ).values('product__name').annotate(
            total_views=Sum('views'),
            total_purchases=Sum('purchases'),
            total_revenue=Sum('revenue')
        ).order_by('-total_revenue')[:10]
        
        # Conversion funnel data
        funnel_data = ConversionFunnel.objects.filter(
            timestamp__date__range=[start_date, end_date]
        ).values('stage').annotate(
            count=Count('id')
        )
        
        # Convert to dict for easier processing
        funnel_dict = {item['stage']: item['count'] for item in funnel_data}
        funnel_data = funnel_dict
        
        # Search analytics
        search_stats = SearchAnalytics.objects.filter(
            timestamp__date__range=[start_date, end_date]
        ).aggregate(
            total_searches=Count('id'),
            avg_results=Avg('results_count')
        )
        
        summary.update({
            'top_products': list(top_products),
            'conversion_funnel': funnel_data,
            'search_analytics': search_stats
        })
        
        return summary
    
    def generate_sales_report(self, start_date, end_date):
        """Generate a sales-focused report."""
        # Daily sales breakdown
        daily_sales = SalesMetrics.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date').values(
            'date', 'total_visitors', 'unique_visitors',
            'conversion_rate', 'new_customers', 'returning_customers'
        )
        
        # Customer lifetime value stats
        clv_stats = CustomerLifetimeValue.objects.aggregate(
            avg_clv=Avg('predicted_ltv'),
            total_customers=Count('user'),
            avg_orders=Avg('total_orders'),
            avg_spent=Avg('total_spent')
        )
        
        # Revenue by product category (if available)
        product_revenue = ProductAnalytics.objects.filter(
            date__range=[start_date, end_date]
        ).values('product__category__name').annotate(
            total_revenue=Sum('revenue'),
            total_units=Sum('purchases')
        ).order_by('-total_revenue')
        
        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'daily_sales': list(daily_sales),
            'customer_lifetime_value': clv_stats,
            'revenue_by_category': list(product_revenue),
            'generated_at': timezone.now().isoformat()
        }
    
    def generate_user_behavior_report(self, start_date, end_date):
        """Generate a user behavior report."""
        # Activity breakdown by type
        activity_breakdown = UserActivityLog.objects.filter(
            timestamp__date__range=[start_date, end_date]
        ).values('activity_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # User engagement metrics
        user_engagement = UserActivityLog.objects.filter(
            timestamp__date__range=[start_date, end_date]
        ).values('user').annotate(
            activity_count=Count('id')
        ).aggregate(
            avg_activities_per_user=Avg('activity_count'),
            total_active_users=Count('user')
        )
        
        # Login/logout patterns
        login_stats = UserActivityLog.objects.filter(
            timestamp__date__range=[start_date, end_date],
            activity_type__in=['LOGIN', 'LOGOUT']
        ).values('activity_type').annotate(
            count=Count('id')
        )
        
        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'activity_breakdown': list(activity_breakdown),
            'user_engagement': user_engagement,
            'login_stats': list(login_stats),
            'generated_at': timezone.now().isoformat()
        }
    
    def generate_products_report(self, start_date, end_date):
        """Generate a product performance report."""
        # Product performance metrics
        product_performance = ProductAnalytics.objects.filter(
            date__range=[start_date, end_date]
        ).values(
            'product__name', 'product__id'
        ).annotate(
            total_views=Sum('views'),
            total_purchases=Sum('purchases'),
            total_revenue=Sum('revenue'),
            conversion_rate=Avg('conversion_rate')
        ).order_by('-total_revenue')
        
        # Product category performance
        category_performance = ProductAnalytics.objects.filter(
            date__range=[start_date, end_date]
        ).values(
            'product__category__name'
        ).annotate(
            total_views=Sum('views'),
            total_purchases=Sum('purchases'),
            total_revenue=Sum('revenue')
        ).order_by('-total_revenue')
        
        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'product_performance': list(product_performance),
            'category_performance': list(category_performance),
            'generated_at': timezone.now().isoformat()
        }
    
    def output_report(self, report_data, options):
        """Output the report in the specified format."""
        if options['format'] == 'console':
            self.output_to_console(report_data)
        elif options['format'] == 'json':
            self.output_to_json(report_data, options['output_file'])
        elif options['format'] == 'csv':
            self.output_to_csv(report_data, options['output_file'])
    
    def output_to_console(self, report_data):
        """Output report to console."""
        self.stdout.write('\n' + '='*50)
        self.stdout.write('ANALYTICS REPORT')
        self.stdout.write('='*50)
        
        if 'period' in report_data:
            self.stdout.write(f"Period: {report_data['period']['start']} to {report_data['period']['end']}")
        
        if 'orders' in report_data:
            orders = report_data['orders']
            self.stdout.write('\nORDER STATISTICS:')
            self.stdout.write(f"  Total Orders: {orders.get('total_orders', 0)}")
            self.stdout.write(f"  Total Revenue: ${orders.get('total_revenue', 0)}")
            self.stdout.write(f"  Average Order Value: ${orders.get('avg_order_value', 0)}")
        
        if 'sales' in report_data:
            sales = report_data['sales']
            self.stdout.write('\nSALES STATISTICS:')
            self.stdout.write(f"  Total Visitors: {sales.get('total_visitors', 0)}")
            self.stdout.write(f"  Unique Visitors: {sales.get('unique_visitors', 0)}")
            self.stdout.write(f"  Average Conversion Rate: {sales.get('avg_conversion_rate', 0):.2%}")
            self.stdout.write(f"  New Customers: {sales.get('total_new_customers', 0)}")
            self.stdout.write(f"  Returning Customers: {sales.get('total_returning_customers', 0)}")
        
        if 'user_activity' in report_data:
            self.stdout.write('\nTOP USER ACTIVITIES:')
            for activity in report_data['user_activity'][:5]:
                self.stdout.write(f"  {activity['activity_type']}: {activity['count']}")
        
        self.stdout.write('\n' + '='*50)
    
    def output_to_json(self, report_data, output_file):
        """Output report to JSON file."""
        if not output_file:
            output_file = f"analytics_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        self.stdout.write(f"Report saved to: {output_file}")
    
    def output_to_csv(self, report_data, output_file):
        """Output report to CSV file."""
        if not output_file:
            output_file = f"analytics_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Flatten the report data for CSV output
        flattened_data = []
        
        # Add summary data
        if 'orders' in report_data:
            orders = report_data['orders']
            flattened_data.append({
                'metric': 'Total Orders',
                'value': orders.get('total_orders', 0)
            })
            flattened_data.append({
                'metric': 'Total Revenue',
                'value': orders.get('total_revenue', 0)
            })
        
        # Add user activity data
        if 'user_activity' in report_data:
            for activity in report_data['user_activity']:
                flattened_data.append({
                    'metric': f"Activity: {activity['activity_type']}",
                    'value': activity['count']
                })
        
        if flattened_data:
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['metric', 'value'])
                writer.writeheader()
                writer.writerows(flattened_data)
            
            self.stdout.write(f"Report saved to: {output_file}")
        else:
            self.stdout.write("No data to export to CSV")
# /orders/resources.py

from import_export import resources, fields
from orders.models import Order

class OrderResource(resources.ModelResource):
    user_name = fields.Field(attribute='user__username', column_name='User Name')
    user_email = fields.Field(attribute='user__email', column_name='User Email')
    shipping_address_line1 = fields.Field(column_name='Shipping Address Line 1')
    shipping_city = fields.Field(column_name='Shipping City')
    shipping_state = fields.Field(column_name='Shipping State')
    shipping_postal_code = fields.Field(column_name='Shipping Postal Code')
    shipping_country = fields.Field(column_name='Shipping Country')

    class Meta:
        model = Order
        fields = (
            'order_number', 'created_at', 'total_price', 'payment_status',
            'amount_paid', 'payment_method', 'payment_id', 'payment_date',
            'shipping_cost', 'shipping_name', 'shipping_method', 'shipment_id',
            'tracking_number', 'user_name', 'user_email',
            'shipping_address_line1', 'shipping_city', 'shipping_state',
            'shipping_postal_code', 'shipping_country',
        )
        export_order = (
            'order_number', 'created_at', 'user_name', 'user_email', 
            'total_price', 'amount_paid', 'payment_method', 'payment_id',
            'payment_date', 'payment_status', 'shipping_cost', 'shipping_name', 
            'shipping_method', 'shipment_id', 'tracking_number',
            'shipping_address_line1', 'shipping_city', 'shipping_state', 
            'shipping_postal_code', 'shipping_country',
        )

    def dehydrate_shipping_address_line1(self, order):
        return order.address.address_line1 if order.address else ''

    def dehydrate_shipping_city(self, order):
        return order.address.city if order.address else ''

    def dehydrate_shipping_state(self, order):
        return order.address.state if order.address else ''

    def dehydrate_shipping_postal_code(self, order):
        return order.address.postal_code if order.address else ''

    def dehydrate_shipping_country(self, order):
        return order.address.country if order.address else ''

# /orders/resources.py

from import_export import resources, fields
from orders.models import Order

class OrderResource(resources.ModelResource):
    user_name = fields.Field(attribute='user__username', column_name='User Name')
    user_email = fields.Field(attribute='user__email', column_name='User Email')
    user_phone = fields.Field(attribute='user__phone', column_name='User Phone')
    shipping_address_line1 = fields.Field(column_name='Shipping Address Line 1')
    shipping_address_line2 = fields.Field(column_name='Shipping Address Line 2')
    shipping_city = fields.Field(column_name='Shipping City')
    shipping_state = fields.Field(column_name='Shipping State')
    shipping_postal_code = fields.Field(column_name='Shipping Postal Code')
    shipping_country = fields.Field(column_name='Shipping Country')
    order_items_count = fields.Field(column_name='Total Items')
    order_items_details = fields.Field(column_name='Order Items Details')
    total_weight = fields.Field(column_name='Total Weight (grams)')
    razorpay_order_id = fields.Field(attribute='razorpay_order_id', column_name='Razorpay Order ID')

    class Meta:
        model = Order
        fields = (
            'order_number', 'created_at', 'updated_at', 'status', 'total_price', 
            'payment_status', 'amount_paid', 'payment_method', 'payment_id', 
            'payment_date', 'razorpay_order_id', 'shipping_cost', 'shipping_name', 
            'shipping_method', 'shipment_id', 'tracking_number', 'carrier',
            'estimated_delivery_date', 'user_name', 'user_email', 'user_phone',
            'shipping_address_line1', 'shipping_address_line2', 'shipping_city', 
            'shipping_state', 'shipping_postal_code', 'shipping_country',
            'order_items_count', 'order_items_details', 'total_weight'
        )
        export_order = (
            'order_number', 'created_at', 'updated_at', 'status', 'user_name', 
            'user_email', 'user_phone', 'total_price', 'amount_paid', 
            'payment_method', 'payment_id', 'payment_date', 'payment_status',
            'razorpay_order_id', 'shipping_cost', 'shipping_name', 'shipping_method', 
            'shipment_id', 'tracking_number', 'carrier', 'estimated_delivery_date',
            'shipping_address_line1', 'shipping_address_line2', 'shipping_city', 
            'shipping_state', 'shipping_postal_code', 'shipping_country',
            'order_items_count', 'order_items_details', 'total_weight'
        )

    def dehydrate_shipping_address_line1(self, order):
        return order.address.address_line1 if order.address else ''

    def dehydrate_shipping_address_line2(self, order):
        return order.address.address_line2 if order.address else ''

    def dehydrate_shipping_city(self, order):
        return order.address.city if order.address else ''

    def dehydrate_shipping_state(self, order):
        return order.address.state if order.address else ''

    def dehydrate_shipping_postal_code(self, order):
        return order.address.postal_code if order.address else ''

    def dehydrate_shipping_country(self, order):
        return order.address.country if order.address else ''

    def dehydrate_order_items_count(self, order):
        return order.items.count()

    def dehydrate_order_items_details(self, order):
        items = order.items.all()
        details = []
        for item in items:
            details.append(f"{item.quantity}x {item.product.name} ({item.selected_price_weight.weight}) - ₹{item.unit_price}")
        return "; ".join(details)

    def dehydrate_total_weight(self, order):
        try:
            return order.calculate_total_weight()
        except:
            return 0

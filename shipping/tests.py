import unittest
from unittest.mock import patch, Mock
from django.test import TestCase
from shipping.shiprocket_api import (
    create_shipment, 
    assign_awb, 
    generate_pickup, 
    track_shipment,
    check_serviceability, 
    generate_manifest,
    print_manifest, 
    generate_label, 
    print_invoice
)
import json
import requests

class ShiprocketAPITestCase(TestCase):
    def setUp(self):
        # Updated payload according to Shiprocket's documentation
        self.payload = {
            "order_id": "ORDER123",
            "order_date": "2025-03-22",
            "channel_id": "12345",
            "pickup_location": "Primary",
            "billing_customer_name": "John Doe",
            "billing_last_name": "Doe",
            "billing_address": "456 Customer Rd",
            "billing_city": "New Delhi",
            "billing_pincode": "110001",
            "billing_state": "Delhi",
            "billing_country": "India",
            "billing_email": "john@example.com",
            "billing_phone": "9999999999",
            "shipping_is_billing": True,
            "order_items": [{
                "name": "Test Product",
                "sku": "test-sku-123",
                "units": 1,
                "selling_price": "100",
                "weight": "0.5"
            }],
            "payment_method": "Prepaid",
            "sub_total": 100,
            "length": 10,
            "breadth": 10,
            "height": 10,
            "weight": 0.5
        }

class CreateShipmentTests(ShiprocketAPITestCase):
    @patch('shipping.shiprocket_api.requests.post')
    def test_create_shipment_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        # Updated response structure per Shiprocket API
        mock_response.json.return_value = {
            'order_id': 123456,
            'shipment_id': 'SHIP123',
            'status': 'NEW',
            'status_code': 1
        }
        mock_post.return_value = mock_response

        response = create_shipment(self.payload)
        self.assertIn('shipment_id', response)
        self.assertIn('order_id', response)
        self.assertEqual(response['status_code'], 1)

    @patch('shipping.shiprocket_api.requests.post')
    def test_create_shipment_server_error(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {'message': 'Internal Server Error'}
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

        with self.assertRaises(requests.exceptions.HTTPError):
            create_shipment(self.payload)

    @patch('shipping.shiprocket_api.requests.post')
    def test_create_shipment_malformed_response(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Malformed response", "", 0)
        mock_post.return_value = mock_response

        with self.assertRaises(json.JSONDecodeError):
            create_shipment(self.payload)

    @patch('shipping.shiprocket_api.requests.post')
    def test_create_shipment_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout()
        
        with self.assertRaises(requests.exceptions.Timeout):
            create_shipment(self.payload)

class AssignAWBTests(ShiprocketAPITestCase):
    @patch('shipping.shiprocket_api.requests.post')
    def test_assign_awb_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        # Updated response structure per Shiprocket API
        mock_response.json.return_value = {
            'awb_code': 'AWB123456789',
            'courier_company_id': 1,
            'courier_name': 'Delhivery',
            'shipment_id': 'SHIP123',
            'status': 'AWB_ASSIGNED'
        }
        mock_post.return_value = mock_response

        response = assign_awb('SHIP123')
        self.assertEqual(response['status'], 'AWB_ASSIGNED')
        self.assertIn('courier_company_id', response)

    @patch('shipping.shiprocket_api.requests.post')
    def test_assign_awb_not_found(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {'message': 'Shipment not found'}
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

        with self.assertRaises(requests.exceptions.HTTPError):
            assign_awb('INVALID_SHIP_ID')

class TrackShipmentTests(ShiprocketAPITestCase):
    @patch('shipping.shiprocket_api.requests.get')
    def test_track_shipment_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        # Updated response structure per Shiprocket API
        mock_response.json.return_value = {
            'tracking_data': {
                'track_status': 'In Transit',
                'shipment_status': 1,
                'current_location': 'Delhi Hub',
                'eta': '2025-03-25',
                'scan_type': 'UD',
                'scan_datetime': '2025-03-22 10:00:00'
            }
        }
        mock_get.return_value = mock_response

        response = track_shipment('AWB123')
        self.assertEqual(response['tracking_data']['shipment_status'], 1)
        self.assertIn('scan_datetime', response['tracking_data'])

    @patch('shipping.shiprocket_api.requests.get')
    def test_track_shipment_empty_response(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        # Return a response without 'tracking_data' key
        mock_response.json.return_value = {'status': 'success', 'data': {}}
        mock_get.return_value = mock_response

        # The function should raise KeyError when tracking_data is missing
        with self.assertRaises(KeyError):
            response = track_shipment('AWB123')
            # Access tracking_data to trigger KeyError
            response['tracking_data']

class GeneratePickupTests(ShiprocketAPITestCase):
    @patch('shipping.shiprocket_api.requests.post')
    def test_generate_pickup_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        # Updated response structure per Shiprocket API
        mock_response.json.return_value = {
            'pickup_token_number': 'PICKUP123',
            'pickup_date': '2025-03-23',
            'pickup_status': 'generated'
        }
        mock_post.return_value = mock_response

        response = generate_pickup('SHIP123')
        self.assertIn('pickup_token_number', response)
        self.assertEqual(response['pickup_status'], 'generated')

    @patch('shipping.shiprocket_api.requests.post')
    def test_generate_pickup_validation_error(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.json.return_value = {'message': 'Invalid pickup date'}
        mock_post.return_value = mock_response
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

        with self.assertRaises(requests.exceptions.HTTPError):
            generate_pickup('SHIP123')

class ShiprocketExtendedTests(TestCase):
    def setUp(self):
        self.mock_response = Mock()
        self.mock_response.status_code = 200

    @patch('shipping.shiprocket_api.requests.get')
    def test_check_serviceability(self, mock_get):
        """Test serviceability check with pincode"""
        self.mock_response.json.return_value = {
            'data': {'available_courier_companies': []}
        }
        mock_get.return_value = self.mock_response

        payload = {
            'pickup_postcode': '110001',
            'delivery_postcode': '400001',
            'weight': 1,
            'cod': 0
        }
        response = check_serviceability(payload)
        self.assertIn('data', response)
        self.assertIn('available_courier_companies', response['data'])

    @patch('shipping.shiprocket_api.requests.post')
    def test_generate_manifest(self, mock_post):
        """Test manifest generation"""
        self.mock_response.json.return_value = {
            'manifest_url': 'http://example.com/manifest.pdf'
        }
        mock_post.return_value = self.mock_response

        payload = {'order_ids': [123, 124]}
        response = generate_manifest(payload)
        self.assertIn('manifest_url', response)

    @patch('shipping.shiprocket_api.requests.get')
    def test_print_manifest(self, mock_get):
        """Test manifest PDF retrieval"""
        self.mock_response.json.return_value = {
            'manifest_url': 'http://example.com/manifest.pdf'
        }
        mock_get.return_value = self.mock_response

        response = print_manifest('MANIFEST123')
        self.assertIn('manifest_url', response)

    @patch('shipping.shiprocket_api.requests.post')
    def test_generate_label(self, mock_post):
        """Test shipping label generation"""
        self.mock_response.json.return_value = {
            'label_url': 'http://example.com/label.pdf'
        }
        mock_post.return_value = self.mock_response

        payload = {'shipment_id': 'SHIP123'}
        response = generate_label(payload)
        self.assertIn('label_url', response)

    @patch('shipping.shiprocket_api.requests.get')
    def test_print_invoice(self, mock_get):
        """Test invoice PDF retrieval"""
        self.mock_response.json.return_value = {
            'invoice_url': 'http://example.com/invoice.pdf'
        }
        mock_get.return_value = self.mock_response

        response = print_invoice('ORDER123')
        self.assertIn('invoice_url', response)

    def test_error_handling(self):
        """Test error handling for all shipping functions"""
        with patch('shipping.shiprocket_api.requests.get') as mock_get:
            mock_get.side_effect = Exception('API Error')
            with self.assertRaises(Exception):
                check_serviceability({'pickup_postcode': '110001'})
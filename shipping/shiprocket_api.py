# shipping/shiprocket_api.py

import requests
import logging
from decimal import Decimal
from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

# Base URL for Shiprocket APIs (same for sandbox and production; you can also adjust this based on environment)
SHIPROCKET_BASE_URL = "https://apiv2.shiprocket.in/v1/external"

# Configure logging
logger = logging.getLogger(__name__)

class ShiprocketAPIError(APIException):
    status_code = 503
    default_detail = 'Shiprocket API error'
    default_code = 'shiprocket_error'

def create_shipment(order_payload):
    """
    Create an adhoc shipment in Shiprocket.
    
    Args:
        order_payload (dict): Dictionary containing order details required by Shiprocket.
    
    Returns:
        dict: JSON response from Shiprocket containing shipment details.
    """
    url = f"{SHIPROCKET_BASE_URL}/orders/create/adhoc"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SHIPROCKET_API_TOKEN}"
    }
    response = requests.post(url, json=order_payload, headers=headers)
    response.raise_for_status()  # Raises an exception for HTTP error codes
    return response.json()

def assign_awb(awb_payload):
    """
    Assign an Air Waybill (AWB) to the shipment.
    
    Args:
        awb_payload (dict): Dictionary containing details required for AWB assignment.
    
    Returns:
        dict: JSON response from Shiprocket with AWB details.
    """
    url = f"{SHIPROCKET_BASE_URL}/courier/assign/awb"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SHIPROCKET_API_TOKEN}"
    }
    response = requests.post(url, json=awb_payload, headers=headers)
    response.raise_for_status()
    return response.json()

def generate_pickup(pickup_payload):
    """
    Generate a pickup request for a shipment.
    
    Args:
        pickup_payload (dict): Dictionary containing pickup details.
    
    Returns:
        dict: JSON response confirming pickup generation.
    """
    url = f"{SHIPROCKET_BASE_URL}/courier/generate/pickup"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SHIPROCKET_API_TOKEN}"
    }
    response = requests.post(url, json=pickup_payload, headers=headers)
    response.raise_for_status()
    return response.json()

def track_shipment(awb_code):
    """
    Track a shipment using its AWB code.
    
    Args:
        awb_code (str): The Air Waybill code for the shipment.
    
    Returns:
        dict: JSON response with tracking information.
    """
    url = f"{SHIPROCKET_BASE_URL}/courier/track/awb/{awb_code}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SHIPROCKET_API_TOKEN}"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# ---- Additional Endpoints to Implement ----

def check_serviceability(service_payload):
    """
    Check courier serviceability and get shipping charges.
    
    Args:
        service_payload (dict): Dictionary containing address and order details.
    
    Returns:
        dict: JSON response with serviceable couriers and shipping charges.
    """
    url = f"{SHIPROCKET_BASE_URL}/courier/serviceability/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SHIPROCKET_API_TOKEN}"
    }
    response = requests.get(url, params=service_payload, headers=headers)
    response.raise_for_status()
    return response.json()

def generate_manifest(manifest_payload):
    """
    Generate a manifest for the orders.
    
    Args:
        manifest_payload (dict): Dictionary containing manifest details.
    
    Returns:
        dict: JSON response confirming manifest generation.
    """
    url = f"{SHIPROCKET_BASE_URL}/manifests/generate"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SHIPROCKET_API_TOKEN}"
    }
    response = requests.post(url, json=manifest_payload, headers=headers)
    response.raise_for_status()
    return response.json()

def print_manifest(manifest_id):
    """
    Get the PDF URL for printing the manifest.
    
    Args:
        manifest_id (str): The ID of the generated manifest.
    
    Returns:
        dict: JSON response containing the PDF URL of the manifest.
    """
    url = f"{SHIPROCKET_BASE_URL}/manifests/print"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SHIPROCKET_API_TOKEN}"
    }
    # Some APIs may require the manifest_id as a query parameter or in the body.
    response = requests.get(url, params={"manifest_id": manifest_id}, headers=headers)
    response.raise_for_status()
    return response.json()

def generate_label(label_payload):
    """
    Generate a shipping label for an order.
    
    Args:
        label_payload (dict): Dictionary containing details required for label generation.
    
    Returns:
        dict: JSON response containing label details and PDF URL.
    """
    url = f"{SHIPROCKET_BASE_URL}/courier/generate/label"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SHIPROCKET_API_TOKEN}"
    }
    response = requests.post(url, json=label_payload, headers=headers)
    response.raise_for_status()
    return response.json()

def print_invoice(order_number):
    """
    Retrieve the PDF URL for the order invoice.
    
    Args:
        order_number (str): The order number.
    
    Returns:
        dict: JSON response containing the invoice PDF URL.
    """
    url = f"{SHIPROCKET_BASE_URL}/orders/print/invoice"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SHIPROCKET_API_TOKEN}"
    }
    response = requests.get(url, params={"order_id": order_number}, headers=headers)
    response.raise_for_status()
    return response.json()

def get_shipping_rate(service_payload):
    """
    Get the shipping rate from Shiprocket's serviceability API.
    
    Args:
        service_payload (dict): Should include keys such as 'pickup_postcode', 'delivery_postcode', 'weight', and 'cod'.
    
    Returns:
        Decimal: The shipping charge.
    
    Raises:
        ValueError: If shipping_charge is not found in the response.
    """
    response = check_serviceability(service_payload)
    # Assuming the response structure is like: {"data": {"shipping_charge": <value>, ...}}
    charge = response.get("data", {}).get("shipping_charge")
    if charge is None:
        raise ValueError("Shipping charge not found in response")
    return charge

def check_shipping_availability(pickup_postcode, delivery_postcode, weight, cod=False):
    """
    Check shipping availability and get rates from Shiprocket.
    """
    url = f"{settings.SHIPROCKET_BASE_URL}/courier/serviceability/"
    
    payload = {
        "pickup_postcode": pickup_postcode,
        "delivery_postcode": delivery_postcode,
        "weight": weight,
        "cod": cod,
        "mode": "surface"  # or 'air' based on your requirements
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.SHIPROCKET_API_TOKEN}"
    }
    
    try:
        response = requests.get(url, params=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        available_couriers = data.get('data', {}).get('available_courier_companies', [])
        
        return {
            'available': len(available_couriers) > 0,
            'couriers': available_couriers,
            'estimated_delivery_days': data.get('data', {}).get('estimated_delivery_days'),
            'rate_list': data.get('data', {}).get('rate_list', [])
        }
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Shiprocket API error: {str(e)}")
        raise ShiprocketAPIError(f"Shipping availability check failed: {str(e)}")

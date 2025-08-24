# API Documentation

## Overview
This document describes the endpoints available in the MyEcommerce API and how to interact with them.

## Authentication
This API uses JWT (JSON Web Tokens) for authentication with enhanced support for unverified users. The authentication flow varies based on the user's email verification status:

### Authentication Flow Overview

#### For Verified Users
- Standard JWT tokens (`access` and `refresh`) are provided upon login
- Full access to all protected endpoints
- Standard token refresh mechanism

#### For Unverified Users
- Special verification tokens (`verification_token` and `refresh_token`) are provided upon login
- Limited access - can only use resend verification email endpoint
- Must verify email to gain full access

### Token Usage
To access protected endpoints, include the appropriate JWT token in the `Authorization` header:
```
Authorization: Bearer [token]
```

### Frontend Implementation Guide

#### Handling Login Response
```javascript
const handleLogin = async (credentials) => {
  const response = await fetch('/api/users/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials)
  });
  
  const data = await response.json();
  
  if (data.access && data.refresh) {
    // Verified user - store standard tokens
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);
    localStorage.setItem('user_verified', 'true');
  } else if (data.verification_token && data.refresh_token) {
    // Unverified user - store verification tokens
    localStorage.setItem('verification_token', data.verification_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    localStorage.setItem('user_verified', 'false');
    
    // Store encrypted verification token if available (for resend functionality)
    if (data.encrypted_verification_token) {
      localStorage.setItem('encrypted_verification_token', data.encrypted_verification_token);
    }
    
    // Show verification prompt to user
  }
};
```

#### Making Authenticated Requests
```javascript
const makeAuthenticatedRequest = async (url, options = {}) => {
  const isVerified = localStorage.getItem('user_verified') === 'true';
  const token = isVerified 
    ? localStorage.getItem('access_token')
    : localStorage.getItem('verification_token');
  
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });
};
```

#### Resending Verification Email
```javascript
const resendVerificationEmail = async () => {
  const verificationToken = localStorage.getItem('verification_token');
  
  if (!verificationToken) {
    throw new Error('No verification token available');
  }
  
  const response = await fetch('/api/users/resend-verification-email/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${verificationToken}`,
      'Content-Type': 'application/json'
    }
  });
  
  return response.json();
};
```


### Obtaining Tokens
- **URL**: `/api/token/`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**:
```json
  {
    "username": "user",
    "password": "pass"
  }
`````

### Success Response (Code: 200 OK)
```json
{
  "refresh": "refresh_token",
  "access": "access_token"
}

`````
### Error Response:

```json

{
  "error": "Invalid credentials"
}

`````
### Refreshing Tokens
- **URL**: `/api/token/refresh/`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**:

```json
{
  "refresh": "refresh_token"
}

`````
### Success Response (Code: 200 OK)
```json
{
  "access": "new_access_token"
}

`````

## Endpoints

### Quickstart: End-to-End cURL Flow (Signup → Verify Email → Login → Address → Cart → Validate → Checkout → Logout)

The following cURL sequence demonstrates a complete user journey using this API. Replace placeholder values (wrapped in < >) before running the commands.

- Assumptions:
  - Backend is running locally at http://127.0.0.1:8000
  - jq is optional, used to parse JSON responses in shell. If not available, manually copy values from responses.

1) Register a user

```bash
BASE="http://127.0.0.1:8000"
USERNAME="demo_user01"
PASSWORD="StrongP@ssw0rd!"
EMAIL="demo_user01@example.com"
PHONE="+919000000011"
FIRST="Demo"
LAST="User"
BIRTHDATE="2000-01-01"

curl -s -X POST "$BASE/api/users/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "'"$USERNAME"'",
    "email": "'"$EMAIL"'",
    "password": "'"$PASSWORD"'",
    "first_name": "'"$FIRST"'",
    "last_name": "'"$LAST"'",
    "phone_number": "'"$PHONE"'",
    "birthdate": "'"$BIRTHDATE"'"
  }'
```

Notes:
- A verification email is sent using an encrypted link to the frontend, which should forward the query params uid and token to the backend verification endpoint.

2) Verify email (backend endpoint, using encrypted token forwarded from frontend)

- From the verification link received by email on the frontend, extract the uid and token (query params), then call:
```bash
UID="<paste-uid-from-link>"
TOKEN="<paste-token-from-link>"

curl -G "$BASE/api/users/email-verify/" \
  --data-urlencode "uid=$UID" \
  --data-urlencode "token=$TOKEN"
```

2a) Resend verification email (for unverified users)

- If you need to resend the verification email, use the verification token from login:
```bash
# Only if user is unverified and has verification_token
if [ "$VERIFICATION_TOKEN" != "null" ] && [ "$VERIFICATION_TOKEN" != "" ]; then
    curl -s -X POST "$BASE/api/users/resend-verification-email/" \
      -H "Authorization: Bearer $VERIFICATION_TOKEN" \
      -H "Content-Type: application/json"
fi
```

3) Login to obtain JWT tokens

```bash
LOGIN_PAYLOAD='{ "login": "'"$USERNAME"'", "password": "'"$PASSWORD"'" }'
TOKENS=$(curl -s -X POST "$BASE/api/users/login/" -H "Content-Type: application/json" -d "$LOGIN_PAYLOAD")

# For verified users
ACCESS=$(echo "$TOKENS" | jq -r .access 2>/dev/null)
REFRESH=$(echo "$TOKENS" | jq -r .refresh 2>/dev/null)

# For unverified users
VERIFICATION_TOKEN=$(echo "$TOKENS" | jq -r .verification_token 2>/dev/null)
REFRESH_TOKEN=$(echo "$TOKENS" | jq -r .refresh_token 2>/dev/null)

# Set appropriate auth header based on user status
if [ "$ACCESS" != "null" ] && [ "$ACCESS" != "" ]; then
    AUTH_HEADER="Authorization: Bearer $ACCESS"
else
    AUTH_HEADER="Authorization: Bearer $VERIFICATION_TOKEN"
fi

# If jq is not available, copy values manually from the response JSON
```

4) Create a shipping address (optional if provided during registration)

```bash
curl -s -X POST "$BASE/api/users/addresses/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "address_line1": "123 Main St",
    "address_line2": "",
    "city": "Anytown",
    "state": "Anystate",
    "country": "India",
    "postal_code": "123456"
  }'
```

5) List addresses and capture address_id for checkout

```bash
curl -s -X GET "$BASE/api/users/addresses/" -H "$AUTH_HEADER"
# Identify the id of the desired address from the response, e.g. ADDRESS_ID=42
ADDRESS_ID="<paste-address-id>"
```

6) Find a product and price-weight to add to cart

- Use the Unified Search endpoint to find a product and pick a valid price_weights entry (price + weight):
```bash
curl -s "$BASE/api/search/?q=prodtest"
# Choose product_id and one price_weights pair from the response
PRODUCT_ID="<paste-product-id>"
PRICE="<paste-price-from-price_weights>"   # e.g. 599.99
WEIGHT="<paste-weight-from-price_weights>" # e.g. 200g
```

7) Add item to cart

```bash
curl -s -X POST "$BASE/api/cart/add_to_cart/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": '"$PRODUCT_ID"',
    "quantity": 2,
    "price_weight": { "price": "'"$PRICE"'", "weight": "'"$WEIGHT"'" }
  }'
```

Possible errors:
- 404 with {"error": "Product does not exist or is inactive."}
- 404 with {"error": "Selected price-weight combination does not exist."}
- 400 with {"error": "Insufficient stock available."}

8) Retrieve cart

```bash
curl -s -X GET "$BASE/api/cart/retrieve_cart/" -H "$AUTH_HEADER"
```

9) Validate cart before checkout

```bash
curl -s -X POST "$BASE/api/cart/validate_cart/" -H "$AUTH_HEADER"
# 200 OK => {"status": "Cart is valid"}
# 400 Bad Request => {
#   "error": "Not enough stock for the following items",
#   "details": ["ProductName (200g) (Requested: X, Available: Y)"]
# }
```

10) Checkout

```bash
curl -s -X POST "$BASE/api/orders/checkout/" \
  -H "$AUTH_HEADER" \
  -H "Content-Type: application/json" \
  -d '{
    "address_id": '"$ADDRESS_ID"',
    "payment_data": {"simulate_failure": false}
  }'
```

Success (201 Created) returns order details and triggers invoice generation and a confirmation email.

11) Logout (invalidate refresh token)

```bash
curl -s -X POST "$BASE/api/users/logout/" \
  -H "Content-Type: application/json" \
  -H "$AUTH_HEADER" \
  -d '{ "refresh": "'"$REFRESH"'" }'
```

### Register

- **URL**: `/api/users/register/`
- **Method**: `POST`
- **Auth Required**: No
- **Data Constraints**:
  ```json
  {
    "username": "[unique username required]",
    "password": "[password required]",
    "email": "[valid email address required]",
    "phone_number": "[unique phone number in +919876543210 format required]",
    "first_name": "[required]",
    "last_name": "[required]", 
    "birthdate": "[date in YYYY-MM-DD format required]",
    "addresses": "[optional - array of address objects]"
  }
### Request Body Example (Addresses Not Needed for Registration)

```json
{
  "username": "newuser01",
  "email": "newuser01@example.com",
  "password": "newpassword123",
  "first_name": "New",
  "last_name": "User",
  "phone_number": "+919000000011",
  "birthdate": "2000-01-01"
}


`````
### Request Body Example (With Addresses)

```json
{
  "username": "newuser01",
  "email": "newuser01@example.com",
  "password": "newpassword123",
  "first_name": "New",
  "last_name": "User",
  "phone_number": "+919000000011",
  "birthdate": "2000-01-01",
  "addresses": [
    {
      "address_line1": "123 Main St",
      "city": "Anytown",
      "state": "Anystate",
      "country": "India",
      "postal_code": "123456"
    }
  ]
}

`````
### Success Response (Code: 201 CREATED)


```json

{
  "username": "newuser01",
  "first_name": "New",
  "last_name": "User",
  "email": "newuser01@example.com",
  "phone_number": "+919000000011",
  "addresses": [
    {
      "id": 11,
      "address_line1": "123 Main St",
      "address_line2": "",
      "city": "Anytown",
      "state": "Anystate",
      "country": "India",
      "postal_code": "123456"
    }
  ],
  "birthdate": "2000-01-01"
}

`````
### Error Response(Code: 400 Bad Request):

```json
{
  "error": "A user with this phone number or email already exists."
}
`````

### Error Response(Code: 409 Conflict):

```json
{
  "error": "A user with this username or phone number already exists."
}

`````

### Login

* **URL**: `/api/users/login/`
* **Method**: `POST`
* **Authentication Required**: No
* **Description**: Authenticates users and returns appropriate tokens based on email verification status
* **Data Constraints (Request Body):**

```json
{
  "login": "[username, email, or phone number]",
  "password": "[password]"
}
```

### Success Response for Verified Users (Code: 200 OK)

```json
{
  "refresh": "[refresh token]",
  "access": "[access token]"
}
```

### Success Response for Unverified Users (Code: 403 Forbidden)

```json
{
  "error": "Please verify your email at user@example.com before logging in.",
  "isUserEmailVerified": false,
  "stored_email_address": "user@example.com",
  "verification_token": "[JWT verification token for unverified users]",
  "refresh_token": "[refresh token]",
  "encrypted_verification_token": "[encrypted token for email verification resend - only included when email_sent=true]",
  "action_required": "check_email_for_verification"
}
```

**Note**: The `encrypted_verification_token` field is only included in the response when:
- User account is inactive (email not verified)
- Email verification is pending (`verified=false`)
- Verification email was previously sent (`email_sent=true`)

This encrypted token enables secure email verification resend functionality and follows the system's security protocols.

### Error Response (Code: 400 Bad Request)

```json
{
  "error": "Invalid credentials"
}
```

### Email Verification

- After registration, a verification email is sent with an encrypted link pointing to the frontend.
- The frontend should capture `uid` and `token` from the query string and call the backend verification endpoint.
- **UID Format**: The system generates UIDs by prefixing user IDs with 'u' before base64 encoding (e.g., user ID 4 becomes 'u4' → 'dTQ' after encoding) to ensure readable and unambiguous identifiers.
- **URL (Backend)**: `/api/users/email-verify/` (GET)
- **Query Params**: `uid`, `token`
- Legacy path-based endpoint (also supported): `/api/users/email-verify/<uidb64>/<token>/`
- **Backward Compatibility**: The system supports both new prefixed UIDs and legacy UIDs for seamless migration.
- **Success Response (200 OK)**:
```json
{
  "message": "Email verified successfully!",
  "detail": "Your account has been activated and email verified."
}
```

### Resend Verification Email

- **URL**: `/api/users/resend-verification-email/`
- **Method**: `POST`
- **Auth Required**: Yes (Token-based authentication for unverified users)
- **Description**: Resends verification email for unverified users using token-based authentication
- **Headers**:
```json
{
  "Authorization": "Bearer [verification_token]"
}
```

#### Success Response (200 OK)
```json
{
  "message": "Verification email sent successfully",
  "detail": "Please check your email for the verification link"
}
```

#### Error Responses

**Invalid Token (401 Unauthorized)**
```json
{
  "detail": "Invalid token."
}
```

**User Already Verified (400 Bad Request)**
```json
{
  "error": "Email is already verified"
}
```

**Rate Limited (429 Too Many Requests)**
```json
{
  "error": "Rate limit exceeded. Please try again later."
}
```

**Email Delivery Failed (500 Internal Server Error)**
```json
{
  "error": "Failed to send verification email. Please try again later."
}
```

## Address Management

### List and Create Addresses
- **URL**: `/api/users/addresses/`
- **Method**: `GET` for listing, `POST` for creating
- **Auth Required**: Yes
- **Permissions**: User must be authenticated
- **Data Constraints** (for POST):
  ```json
  {
    "address_line1": "[street address]",
    "address_line2": "[apartment, suite, unit, building, floor, etc.]",
    "city": "[city]",
    "state": "[state/province/region]",
    "country": "[country]",
    "postal_code": "[postal/ZIP code]"
  }

### Success Response for GET  (Code: 200 OK)

```json
[
  {
    "id": 1,
    "address_line1": "123 Main St",
    "address_line2": "",
    "city": "Anytown",
    "state": "Anystate",
    "country": "India",
    "postal_code": "123456"
  }
]

```

### Error Response

```json
{
  "error": "Invalid token or user ID"
}
```

### Success Response for POST  (Code: 201 CREATED)

```json
[
  {
    "id": 1,
    "address_line1": "123 Main St",
    "address_line2": "",
    "city": "Anytown",
    "state": "Anystate",
    "country": "India",
    "postal_code": "123456"
  }
]

```

### Error Response (Code: 400 BAD REQUEST)

```json
{
  "error": "Invalid data provided"
}
```

## Address Detail, Update, and Delete
- **URL**: `/api/users/addresses/{id}/`
- **Method**: `GET` for detail, `PUT`/`PATCH` for update, `DELETE` for delete
- **Auth Required**: Yes
- **Permissions**:  User must be authenticated and own the address
- **Data Constraints** (for GET):

### Success Response for GET  (Code: 200 OK)
```json
{
  "id": 1,
  "address_line1": "123 Main St",
  "address_line2": "",
  "city": "Anytown",
  "state": "Anystate",
  "country": "India",
  "postal_code": "123456"
}
```

### Success Response for PUT/PATCH (Code: 200 OK)
```json
{
  "message": "Address updated successfully."
}
```

### Success Response for DELETE (Code: 204 NO CONTENT)
```json
{}
```

### Error Response (Code: 404 NOT FOUND)

```json
{
  "error": "Address not found."
}

```

## User Profile Retrieval

### List and Create Addresses
- **URL**: `/api/users/user-profile/`
- **Method**: `GET` 
- **Auth Required**: Yes (Bearer Token required)
- **Permissions**: User must be authenticated
- **Description**: This endpoint retrieves the authenticated user's profile information, including a list of associated addresses. Each user profile contains personal information alongside nested details about each registered address.
- **Data Constraints** (for GET):

### Success Response for GET  (Code: 200 OK)
  ```json
  {
    "username": "newuser1",
    "first_name": "UpdatedName",
    "last_name": "UpdatedSurname",
    "email": "newuser1@example.com",
    "phone_number": "+919000000001",
    "addresses": [
      {
        "id": 1,
        "address_line1": "123 Main St",
        "address_line2": null,
        "city": "Anytown",
        "state": "Anystate",
        "country": "India",
        "postal_code": "123456"
      },
      {
        "id": 2,
        "address_line1": "456 New St",
        "address_line2": null,
        "city": "Test",
        "state": "Anystate",
        "country": "India",
        "postal_code": "123456"
      }
    ]
  }

  ```

### Error Response (Code 401 Unauthorized)

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### Error Response (Code 403 Forbidden)
```json
{
  "detail": "You do not have permission to perform this action."
}
```

## Updating User Profile

### List and Create Addresses
- **URL**: `/api/users/user-profile/`
- **Method**: `PUT` 
- **Auth Required**: Yes (Bearer Token required)
- **Permissions**: User must be authenticated
- **Description**:  Allows authenticated users to update their profile information, including one or multiple addresses.
- **Note**: The id in the address data is used to specify which address to update. Omitting id results in a new address creation.
- **Data Constraints** (for GET):

### Request Body
  ```json
  {
  "first_name": "UpdatedName",
  "last_name": "UpdatedSurname",
  "phone_number": "+919000000001",
  "addresses": [
    {
      "id": 2,
      "address_line1": "456 New St",
      "city": "updated",
      "state": "Newsupdatedstate",
      "country": "India",
      "postal_code": "654321"
    }
  ]
}
  ```

### Error Response (Code 400 Bad Request)

```json
{
  "error": "Invalid input data"
}
```

### Error Response (Code 401 Unauthorized)
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### Error Response (Code 403 Forbidden)
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### Category List

* **URL**: `/api/categories/`
* **Method**: `GET`
* **Authentication Required**: No (for listing), Yes (for creating)
* **Description**: Returns all categories ordered by display_order first, then by name
* **Data Constraints (for POST request):**
```json

{
  "category_id": "[unique category id]",
  "name": "[category name]",
  "description": "[category description]",
  "image": "[upload image file]",
  "display_order": "[optional: number 1-8 for ordering]"
}


```

### Success Response(Code: 200 OK for GET, 201 CREATED for POST)
### GET :
```json
[
  {
    "category_id": "001",
    "name": "Electronics",
    "description": "Gadgets and more",
    "tags": ["Smartphone", "Laptop", "Tablet"],
    "image": "url_to_image",
    "display_order": 1,
    "available_display_orders": [2, 3, 4, 5, 6, 7, 8]
  }
]

```

### POST :
```json
{
  "category_id": "002",
  "name": "Books",
  "description": "Read more",
  "tags": ["Fiction", "Non-Fiction"],
  "image": "url_to_newly_uploaded_image",
  "display_order": 2,
  "available_display_orders": [3, 4, 5, 6, 7, 8]
}

```
### Error Response :

```json
{
  "error": "Permissions required"
}
```

### Ordered Category List

* **URL**: `/api/categories/ordered/`
* **Method**: `GET`
* **Authentication Required**: No
* **Description**: Returns only categories with display_order set (1-8), ordered by display_order
* **Note**: Maximum 8 categories can have display_order values

### Success Response (Code: 200 OK)
```json
[
  {
    "category_id": "001",
    "name": "Electronics",
    "description": "Gadgets and more",
    "tags": ["Smartphone", "Laptop", "Tablet"],
    "image": "url_to_image",
    "display_order": 1,
    "available_display_orders": [3, 4, 5, 6, 7, 8]
  },
  {
    "category_id": "002",
    "name": "Books",
    "description": "Read more",
    "tags": ["Fiction", "Non-Fiction"],
    "image": "url_to_image",
    "display_order": 2,
    "available_display_orders": [3, 4, 5, 6, 7, 8]
  }
]
```

### Available Display Orders

* **URL**: `/api/categories/available-orders/`
* **Method**: `GET`
* **Authentication Required**: No
* **Description**: Returns available display order numbers and usage statistics

### Success Response (Code: 200 OK)
```json
{
  "available_orders": [3, 4, 5, 6, 7, 8],
  "total_slots": 8,
  "used_slots": 2
}
```


++

### Category Detail

* **URL**: `/api/categories/{category_id}/`
* **Method**: `GET`, `PUT`, `PATCH`, `DELETE`
* **Authentication Required**: No (for GET), Yes (for PUT, PATCH, DELETE)
* **Data Constraints (for PUT/PATCH request):**
```json

{
  "name": "[new category name]",
  "description": "[new category description]",
  "tags": ["Updated", "Tags"],
  "image": "[new image or keep existing]",
  "display_order": "[optional: number 1-8 for ordering]"
}


```

### Success Response (Code: 200 OK for GET, PUT, PATCH; 204 NO CONTENT for DELETE)
### GET :
```json
{
  "category_id": "001",
  "name": "Electronics",
  "description": "Gadgets and more updated",
  "tags": ["Smartphone", "Laptop", "Tablet"],
  "image": "url_to_updated_image",
  "display_order": 1,
  "available_display_orders": [2, 3, 4, 5, 6, 7, 8]
}


```

### PUT/PATCH:
```json
{
  "category_id": "001",
  "name": "Updated Category Name",
  "description": "Updated description here",
  "tags": ["Updated", "Tags"],
  "image": "url_to_updated_image",
  "display_order": 2,
  "available_display_orders": [3, 4, 5, 6, 7, 8]
}

```
### DELETE:
```json
{}
```
### Error Response :

```json
{
  "error": "Invalid category ID or insufficient permissions"
}
```

### Display Order Validation Errors:

```json
{
  "display_order": ["Display order must be between 1 and 8."]
}
```

```json
{
  "display_order": ["A category with this display order already exists."]
}
```

## Logout

* **URL**: `/api/users/logout/`
* **Method**: `POST`
* **Authentication Required**: Yes

## Headers

```json
Authorization: Bearer [access_token]

```

```json
{
  "refresh": "[refresh_token]"
}
```

### Success Response  (Code: 205 RESET CONTENT)

```json
{
  "message": "Logout successful, token invalidated."
}
```

### Error Response

```json
{
  "error": "Invalid token or token already expired"
}
```

## Password Reset

### Request Password Reset
- **URL**: `/api/users/password_reset/`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**:

```json
{
  "email": "user@example.com"
}
```

### Success Response  (Code: 200 OK)

```json
{
  "message": "Password reset e-mail has been sent."
}
```

### Error Response

```json
{
  "error": "Email address not found."
}
```

## Confirm Password Reset

### Endpoint
- **URL**: `/api/users/password-reset/confirm/`
- **Method**: `POST`
- **Auth Required**: No
- **Rate Limiting**: 2 requests per minute per IP address
- **Description**: Confirms password reset using encrypted or traditional Django tokens

### Features
- Supports both encrypted Fernet tokens and traditional Django tokens for backward compatibility
- Enhanced password strength validation using Django's built-in validators
- Password confirmation field matching verification
- Comprehensive error messaging for security and user experience
- Token expiration and one-time use validation

### URL Patterns
- **Primary**: `/api/users/password-reset/confirm/` (supports query parameters)
- **Legacy**: `/api/users/password-reset/confirm/<uidb64>/<token>/` (backward compatibility)
- **Query Parameters**: `?uid=<uid>&token=<token>`

### Request Format

#### Required Parameters
```json
{
  "uid": "base64-encoded-user-id",
  "token": "encrypted-or-django-token",
  "new_password1": "newpassword123",
  "new_password2": "newpassword123"
}
```

#### Parameter Details
- `uid`: Base64 encoded user ID (can be passed in URL, query params, or request body)
- `token`: Encrypted Fernet token or traditional Django token
- `new_password1`: New password (must meet strength requirements)
- `new_password2`: Password confirmation (must match new_password1)

### Response Formats

#### Success Response (200 OK)
```json
{
  "message": "Password has been reset successfully"
}
```

#### Missing Parameters (400 Bad Request)
```json
{
  "error": "Missing reset parameters"
}
```

#### Invalid User ID (400 Bad Request)
```json
{
  "error": "Invalid user ID"
}
```

#### Inactive User Account (400 Bad Request)
```json
{
  "error": "User account is inactive"
}
```

#### Email Not Verified (400 Bad Request)
```json
{
  "error": "Please verify your email before resetting your password. Check your inbox for the verification link or contact support if you need assistance."
}
```

#### Missing Password Fields (400 Bad Request)
```json
{
  "error": "Both password fields are required"
}
```

#### Password Mismatch (400 Bad Request)
```json
{
  "error": "Password confirmation does not match"
}
```

#### Password Validation Failed (400 Bad Request)
```json
{
  "error": "Password validation failed",
  "details": [
    "This password is too short. It must contain at least 8 characters.",
    "This password is too common."
  ]
}
```

#### Invalid or Expired Token (400 Bad Request)
```json
{
  "error": "Invalid or expired reset token"
}
```

#### Form Validation Error (400 Bad Request)
```json
{
  "error": "Password reset failed",
  "details": {
    "new_password1": ["This field is required."]
  }
}
```

### Security Features

#### Token Security
- Encrypted Fernet tokens with 24-hour expiration
- Traditional Django tokens for backward compatibility
- Tokens are single-use and expire after successful reset
- URL-safe base64 encoding for secure transmission

#### Password Validation
- Django's built-in password validators
- Minimum length requirements
- Common password detection
- Password similarity to user information validation
- Numeric-only password prevention

#### Rate Limiting
- IP-based rate limiting (2 requests per minute)
- Protection against brute force attacks
- Automatic cleanup of rate limit records

#### Input Validation
- Required field validation
- Password confirmation matching
- User account status verification
- Email verification requirement enforcement

### Frontend Integration

#### Standard URL Format
```
http://localhost:3000/verify-email?uid=<uid>&token=<token>
```

#### Production URL Format
```
http://frontend-url/verify-email?uid=<uid>&token=<token>
```

### Example Usage

#### cURL Example
```bash
curl -X POST \
  http://localhost:8000/api/users/password-reset/confirm/ \
  -H 'Content-Type: application/json' \
  -d '{
    "uid": "MQ",
    "token": "encrypted_token_here",
    "new_password1": "SecurePassword123!",
    "new_password2": "SecurePassword123!"
  }'
```

#### JavaScript Example
```javascript
const resetPassword = async (uid, token, password1, password2) => {
  try {
    const response = await fetch('/api/users/password-reset/confirm/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        uid: uid,
        token: token,
        new_password1: password1,
        new_password2: password2
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      console.log('Password reset successful:', data.message);
    } else {
      console.error('Password reset failed:', data.error);
    }
  } catch (error) {
    console.error('Network error:', error);
  }
};
```

### Success Response  (Code: 200 OK)

```json
{
  "message": "Password has been reset successfully."
}
```

### Error Response

```json
{
  "error": "Invalid token or user ID"
}
```

# Bulk Upload Functionality Documentation

## Overview
This document provides an overview of the bulk upload functionality implemented for the product management module in the e-commerce backend. The functionality allows admin users to upload multiple products at once using a CSV file, significantly simplifying the process of populating the product database.

## Features
1. **CSV File Upload**:
   - Admin users can upload products in bulk by submitting a CSV file.
   - The CSV file needs to include specific columns like name, description, category ID, inventory, and price-weight combinations.

2. **Error Handling**:
   - The system validates the CSV file for the correct format and completeness.
   - Errors are reported back to the user, including missing fields, data format errors, and validation issues such as duplicate product names or nonexistent category IDs.

3. **Security and Permissions**:
   - Only users with admin privileges can perform bulk uploads, ensuring that the functionality is securely managed.

## How It Works
1. **Uploading the CSV**:
   - Admin users access the bulk upload feature through a dedicated API endpoint.
   - They must provide a well-formatted CSV file containing the product data.

2. **Validation**:
   - The system checks each row of the CSV for errors.
   - It validates against existing data to prevent duplicates and checks for the existence of referenced entities like product categories.

3. **Database Update**:
   - Valid entries are saved to the database.
   - Each new product entry includes details such as name, description, inventory levels, and associated category.

4. **CSV File Format Requirements**:
  The CSV file should include headers and the following columns:

  - name: The product's name (unique).
  - description: A brief description of the product.
  - category_id: The ID of the category this product belongs to.
  - inventory: The number of items available.
  - price_weights: Combinations of price and weight, separated by commas. 
5. **Example CSV content**:
      - name,description,category_id,inventory,price_weights
      - Smartphone,Latest model smartphone,001,100,2000-100gms,3000-200gms,4000-300gms
      - Laptop,High performance laptop,002,50,50000-1kg,75000-1.5kg,100000-2kg



## API Endpoint
- **Bulk Upload Endpoint**:
  - **Method**: POST
  - **URL**: `/api/products/bulk-upload/`
  - **Authentication**: Required (Admin only)
  - **Data Constraints (for POST request)**:
  ```json
  {
  "file": "Uploaded file (CSV or Excel)"
  }
  ```

### Success Response  (Code: 201 CREATED)

```json
{
  "status": "success",
  "message": "Products uploaded successfully"
}
```

### Error Response (Detailed)

```json
{
  "error": "Detailed error messages including any row-specific issues."
}
```

## Error Reporting
Errors during the upload process are detailed in the response, providing clear feedback to the user. This includes information on any row that fails to process due to validation issues or incorrect data formatting.

## Usage Example
To use the bulk upload feature, admin users will:

1. Prepare a CSV file with the required data columns.
2. Log in to obtain authentication credentials.
3. Send a POST request to the bulk upload endpoint with the CSV file attached.

## Conclusion
The bulk upload functionality enhances the backend's capabilities by allowing quick and efficient updates to the product catalog, making it an essential tool for administrative users managing large datasets.



### Products CRUD Docs :


- **List and Create Products**:
  
  - **API Endpoint**:
  - **Method**: `GET` FOR LISTING, `POST` FOR CREATING
  - **URL**: `/api/products/`
  - **Authentication**: Yes (Admin for POST, No authentication for GET)
  - **Permissions**: `GET` is public, `POST` requires admin privileges
  
### Product POST Request Body :
  ```json
  {
  "name": "Laptop",
  "description": "High performance laptop",
  "category": 2,
  "tags": ["Computing", "High-End"],
  "price_weights": [
    {"price": "50000.00", "weight": "1kg", "inventory": 50},
    {"price": "75000.00", "weight": "1.5kg", "inventory": 50},
    {"price": "100000.00", "weight": "2kg", "inventory": 50}
  ],
  "image_urls": ["http://example.com/image2.jpg"],
  "is_active": true
}

  ```

### Success Response for POST  (Code: 201 CREATED):

```json
{
  "id": 2,
  "name": "Laptop",
  "description": "High performance laptop",
  "category": {
    "id": 2,
    "name": "Computing"
  },
  "inventory": 150,  // Computed from the price_weights, for example
  "price_weights": [
    {"id": 5, "price": "50000.00", "weight": "1kg", "inventory": 50, "status": "In stock"},
    {"id": 6, "price": "75000.00", "weight": "1.5kg", "inventory": 50, "status": "In stock"},
    {"id": 7, "price": "100000.00", "weight": "2kg", "inventory": 50, "status": "In stock"}
  ],
  "tags": ["Computing", "High-End"],
  "image_urls": ["http://example.com/image2.jpg"],
  "is_active": true,
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T12:00:00Z"
}


```

### Success Response for GET  (Code: 200 OK)

```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "Smartphone",
            "description": "Latest model smartphone",
            "category": {
                "id": 1,
                "name": "Electronics"
            },
            "inventory": 100,
            "price_weights": [
                {"id": 1, "price": "2000.00", "weight": "100gms", "inventory": 30, "status": "In stock"},
                {"id": 2, "price": "3000.00", "weight": "200gms", "inventory": 40, "status": "In stock"},
                {"id": 3, "price": "4000.00", "weight": "300gms", "inventory": 30, "status": "In stock"}
            ],
            "tags": ["Electronics", "Gadgets"],
            "image_urls": ["http://example.com/image1.jpg"],
            "is_active": true,
            "created_at": "2023-10-01T12:00:00Z",
            "updated_at": "2023-10-01T12:00:00Z"
        }
    ]
}

```


### Error Response (Code: 400 Bad Request)

```json
{
  "error": "Product with this name already exists or missing required fields"
}
```



- **Single Product Detail**:

  - **API Endpoint**:
  - **Method**: `GET` FOR detail
  - **URL**: `/api/products/{id}/`
  - **Authentication**: Yes
  - **Permissions**: Public access for viewing
  - **Description**: Retrieves details of a specific product by its ID.

### Success Response for GET (Code: 200 OK):

```json
{
  "id": 1,
  "name": "Smartphone",
  "description": "Latest model smartphone",
  "category": {
    "id": 1,
    "name": "Electronics"
  },
  "inventory": 100,
  "price_weights": "2000-100gms, 3000-200gms, 4000-300gms",
  "tags": ["Electronics", "Gadgets"],
  "image_urls": ["http://example.com/image1.jpg"],
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T12:00:00Z"
}
```
### Error Response (404 NOT FOUND)

```json
{
  "error": "Product not found or inactive."
}

```

- **Update Product**:

  - **API Endpoint**:
  - **Method**: `PUT` OR `PATCH` 
  - **URL**: `/api/products/{id}/`
  - **Authentication**: Yes(Admin only)
  - **Permissions**: Admin access required
  - **Description**: Updates the details of a specific product by its ID.

### Product PUT Request Body:
```json
{
  "name": "Updated Product Name",
  "description": "Updated Description",
  "category_id": 1,
  "inventory": 150,
  "price_weights": "2500-100gms,3500-200gms",
  "tags": ["Updated", "Tags"],
  "image_urls": ["http://example.com/updated_image.jpg"],
  "is_active": false
}
```

### Success Response for PUT/PATCH (Code: 200 OK):

```json
{
  "message": "Product updated successfully."
}
```

### Product DELETE Operation:

- **URL**: `/api/products/{id}/`
- **Method**: `DELETE`
- **Auth Required**: Yes(Admin only)
- **Permissions**: Admin access required
- **Description**: Deletes the product with the specified ID.


### Success Response for DELETE (Code: 204 NO CONTENT):
```json
{}
```


### Error Response (Code: 404 NOT FOUND):
```json
{
  "error": "Product not found."
}
```



## Unified Search API

- **URL**: `/api/search/`
- **Method**: `GET`
- **Authentication Required**: No (for search), Yes (to view specific details if required by internal rules)
- **Query Parameters**:
  - **q**: The query string to search for in products and categories.
  - **type**: Optional. Specify 'product' to search only products, 'category' to search only categories, or leave blank to search both.

### Fuzzy Search Suggestions:
-**Code: 200 OK**:

  ```json
  {
    "detail": "No exact match found, did you mean:",
    "product_suggestions": ["prodtest1", "prodtest3"],
    "category_suggestions": ["cattest1", "cattest3"]
  }
  ```

### Error Response (Code: 404 NOT FOUND):
  ```json
  {
    "detail": "No matches found."
  }
  ```

### Example 1: Search for a random thing see if its available or anything close to it :

  ```bash
    GET http://127.0.0.1:8000/api/search/?q=test
  ```

### Success Response (Code: 200 OK):
```json
{
    "products": [
        {
            "id": 1,
            "name": "prodtest1",
            "category": 1,
            "inventory": 11,
            "tags": [
                "spicy"
            ],
            "price_weights": [
                {
                    "price": "2100.00",
                    "weight": "102gms"
                },
                {
                    "price": "2200.00",
                    "weight": "100gms"
                },
                {
                    "price": "2002.00",
                    "weight": "100gms"
                }
            ],
            "images": [
                {
                    "image_url": "/media/products/1/bedroom.webp",
                    "description": "photo"
                }
            ],
            "is_active": true,
            "status": "In stock"
        },
        {
            "id": 2,
            "name": "prodtest2",
            "category": 2,
            "inventory": 20,
            "tags": [
                "test2",
                "prod2"
            ],
            "price_weights": [
                {
                    "price": "20999.99",
                    "weight": "100gms"
                },
                {
                    "price": "2000.01",
                    "weight": "100gms"
                },
                {
                    "price": "2000.02",
                    "weight": "100gms"
                }
            ],
            "images": [
                {
                    "image_url": "/media/products/2/bg-fur.webp",
                    "description": "prod22"
                }
            ],
            "is_active": true,
            "status": "In stock"
        },
        {
            "id": 3,
            "name": "prodtest3",
            "category": 2,
            "inventory": 20,
            "tags": [
                "test2",
                "prod2",
                "pt2"
            ],
            "price_weights": [
                {
                    "price": "2000.02",
                    "weight": "100gms"
                },
                {
                    "price": "1999.99",
                    "weight": "100gms"
                },
                {
                    "price": "1999.98",
                    "weight": "100gms"
                }
            ],
            "images": [
                {
                    "image_url": "/media/products/3/bedroom.webp",
                    "description": "prod221"
                }
            ],
            "is_active": true,
            "status": "In stock"
        }
    ],
    "categories": [
        {
            "category_id": "1",
            "name": "Cat1test",
            "description": "this is is a test",
            "tags": [
                "spices"
            ],
            "image": "/media/category_images/bedroom_aJWpeWz.webp",
            "products": [
                {
                    "id": 1,
                    "name": "prodtest1",
                    "category": 1,
                    "inventory": 11,
                    "tags": [
                        "spicy"
                    ],
                    "price_weights": [
                        {
                            "price": "2100.00",
                            "weight": "102gms"
                        },
                        {
                            "price": "2200.00",
                            "weight": "100gms"
                        },
                        {
                            "price": "2002.00",
                            "weight": "100gms"
                        }
                    ],
                    "images": [
                        {
                            "image_url": "/media/products/1/bedroom.webp",
                            "description": "photo"
                        }
                    ],
                    "is_active": true,
                    "status": "In stock"
                }
            ]
        },
        {
            "category_id": "catid2",
            "name": "cattest2",
            "description": "testing cat_2",
            "tags": [
                "test2"
            ],
            "image": "/media/category_images/decorative.webp",
            "products": [
                {
                    "id": 2,
                    "name": "prodtest2",
                    "category": 2,
                    "inventory": 20,
                    "tags": [
                        "test2",
                        "prod2"
                    ],
                    "price_weights": [
                        {
                            "price": "20999.99",
                            "weight": "100gms"
                        },
                        {
                            "price": "2000.01",
                            "weight": "100gms"
                        },
                        {
                            "price": "2000.02",
                            "weight": "100gms"
                        }
                    ],
                    "images": [
                        {
                            "image_url": "/media/products/2/bg-fur.webp",
                            "description": "prod22"
                        }
                    ],
                    "is_active": true,
                    "status": "In stock"
                },
                {
                    "id": 3,
                    "name": "prodtest3",
                    "category": 2,
                    "inventory": 20,
                    "tags": [
                        "test2",
                        "prod2",
                        "pt2"
                    ],
                    "price_weights": [
                        {
                            "price": "2000.02",
                            "weight": "100gms"
                        },
                        {
                            "price": "1999.99",
                            "weight": "100gms"
                        },
                        {
                            "price": "1999.98",
                            "weight": "100gms"
                        }
                    ],
                    "images": [
                        {
                            "image_url": "/media/products/3/bedroom.webp",
                            "description": "prod221"
                        }
                    ],
                    "is_active": true,
                    "status": "In stock"
                }
            ]
        }
    ]
}

```

### Error Response (Code: 404 NOT FOUND):
```json
{
  "error": "Product not found."
}
```


### Example 2: Search for a Specific Product
- **Request**: `GET /api/search/?q=prodtest2`
- **Response** (200 OK):
  ```json
    {
      "products": [
        {
          "id": 2,
          "name": "prodtest2",
          "category": 2,
          "inventory": 20,
          "tags": ["test2", "prod2"],
          "price_weights": [
            {"price": "20999.99", "weight": "100gms"},
            {"price": "2000.01", "weight": "100gms"},
            {"price": "2000.02", "weight": "100gms"}
          ],
          "images": [
            {
              "image_url": "/media/products/2/bg-fur.webp",
              "description": "prod22"
            }
          ],
          "is_active": true,
          "status": "In stock"
        }
      ],
      "categories": []
    }
  ```


### Example 3: Search for categories related to a query exact name

- **Request**: `http://127.0.0.1:8000/api/search/?q=cattest2`
- **Response** (200 OK):
  ```json
    {
      "products": [],
        "categories": [
            {
                "category_id": "catid2",
                "name": "cattest2",
                "description": "testing cat_2",
                "tags": [
                    "test2"
                ],
                "image": "/media/category_images/decorative.webp",
                "products": [
                    {
                        "id": 2,
                        "name": "prodtest2",
                        "category": 2,
                        "inventory": 20,
                        "tags": [
                            "test2",
                            "prod2"
                        ],
                        "price_weights": [
                            {
                                "price": "20999.99",
                                "weight": "100gms"
                            },
                            {
                                "price": "2000.01",
                                "weight": "100gms"
                            },
                            {
                                "price": "2000.02",
                                "weight": "100gms"
                            }
                        ],
                        "images": [
                            {
                                "image_url": "/media/products/2/bg-fur.webp",
                                "description": "prod22"
                            }
                        ],
                        "is_active": true,
                        "status": "In stock"
                    },
                    {
                        "id": 3,
                        "name": "prodtest3",
                        "category": 2,
                        "inventory": 20,
                        "tags": [
                            "test2",
                            "prod2",
                            "pt2"
                        ],
                        "price_weights": [
                            {
                                "price": "2000.02",
                                "weight": "100gms"
                            },
                            {
                                "price": "1999.99",
                                "weight": "100gms"
                            },
                            {
                                "price": "1999.98",
                                "weight": "100gms"
                            }
                        ],
                        "images": [
                            {
                                "image_url": "/media/products/3/bedroom.webp",
                                "description": "prod221"
                            }
                        ],
                        "is_active": true,
                        "status": "In stock"
                    }
                ]
            }
        ]
    }
  ``` 


### Cart API CRUD Docs :


- **1. Add Item to Cart**:
  
  - **API Endpoint**:
  - **Method**:  `POST` 
  - **URL**: `/api/cart/add_to_cart/`
  - **Authentication**: Yes (JWT or session-based)

  
### Product POST Request Body :
  ```json
  {
  "product_id": 1,
  "quantity": 2,
  "price_weight": {
    "price": "2100.00",
    "weight": "100gms"
  }
}
  ```

### Success Response for POST  (Code: 201 CREATED):

```json
{
  "status": "Added to cart"
}

```
### Error Response (Code: 400 Bad Request)

```json
{
  "error": "Product not found"
}

OR
{
  "error": "Price-weight combination not found"
}

OR
{
  "error": "Not enough stock for prodcutname"
}

OR
{
  "error": "Price and weight must be provided"
}
```

- **2. Retrieve Cart**:

  - **API Endpoint**:
  - **Method**: `GET` 
  - **URL**: `/api/cart/retrieve_cart/`
  - **Authentication**: Yes (JWT or session-based)
  - **Description**: Retrieves the current cart for the user or guest session.

### Success Response for GET (Code: 200 OK):

```json
{
    "cart_id": 4,
    "user": 28,
    "items": [
        {
            "cart_item_id": 3,
            "product": {
                "product_id": 2,
                "name": "prodtest2",
                "category_id": 2,
                "inventory": 20,
                "images": [
                    {
                        "image_url": "/media/products/2/bg-fur.webp",
                        "description": "prod22"
                    }
                ],
                "is_active": true,
                "status": "In stock"
            },
            "selected_price_weight": {
                "price": "2200.00",
                "weight": "100gms"
            },
            "quantity": 1,
            "total_price": 2200.0
        }
    ],
    "created_at": "2024-09-18T10:37:33.873065Z",
    "updated_at": "2024-09-18T10:37:33.873089Z"
}
```
### Error Response (404 NOT FOUND)

```json
{
  "error": "Cart not found"
}

```

- **3. Update Cart Item**:

  - **API Endpoint**:
  - **Method**: `PUT`
  - **URL**: `/api/cart/{cart_item_id}/update_cart_item/`
  - **Authentication**: Yes (JWT or session-based)
  - **Description**: Updates the quantity of an existing item in the cart.

### Product PUT Request Body (you can update the quantity and/or price_weight):
```json
{
  "quantity": 2,
  "price_weight": {
    "price": "2100.00",
    "weight": "102gms"
  }
}

```
### Product PUT Request Body (you can update the quantity only):
```json
{
  "quantity": 2
}
```
### Product PUT Request Body (you can update the Price-Weight Combo only):
```json
{
  "price_weight": {
    "price": "2100.00",
    "weight": "102gms"
  }
}

```
### Success Response for PUT/PATCH (Code: 200 OK):

```json
{
    "status": "Cart item updated"
}

```
### Error Response (Code: 404 NOT FOUND):
```json
{
    "error": "Price-weight combination not found",
    "available_combinations": [
        {
            "price": "2100.00",
            "weight": "102gms"
        },
        {
            "price": "2200.00",
            "weight": "100gms"
        },
        {
            "price": "2000.00",
            "weight": "100gms"
        }
    ]
}

```


### Product DELETE Operation:

- **URL**: `/api/products/{id}/`
- **Method**: `DELETE`
- **Auth Required**: Yes(Admin only)
- **Permissions**: Admin access required
- **Description**: Deletes the product with the specified ID.


### Success Response for DELETE (Code: 204 NO CONTENT):
```json
{}
```


### Error Response (Code: 404 NOT FOUND):
```json
{
    "error": "Price-weight combination not found",
    "available_combinations": [
        {
            "price": "2100.00",
            "weight": "102gms"
        },
        {
            "price": "2200.00",
            "weight": "100gms"
        }
    ]
}

```

## Usage Example:

-**To manage products, users will**:

  1. Prepare the necessary data in the format specified above
  2. Authenticate to obtain necessary credentials if required
  3. Send appropriate HTTP requests to the endpoints to list, create, update, or delete product records

  # Orders Module Documentation

## Overview

The Orders module is a core part of the MyEcommerce backend. It manages the complete order lifecycle – from checkout and payment processing to invoice generation, email notifications, and order history retrieval. The module ensures that inventory is updated correctly and that users receive timely notifications about their orders.

## Features

- **Checkout Process**
  - Converts the user's cart into an order.
  - Processes payment (with support for simulating failures during testing).
  - Deducts inventory from the associated price-weight combinations.
  - Generates a PDF invoice for the order.
  - Sends an order confirmation email with the invoice attached.
  - Clears the cart after a successful checkout.

- **Order History Retrieval**
  - Provides an endpoint for users to view their past orders.

- **Order Details**
  - Allows users to retrieve detailed information for a specific order using the order number.

- **Order Cancellation**
  - Enables users to cancel an order if it is still in a cancellable state (i.e., `PENDING` or `PROCESSING`).
  - Sends an order cancellation email upon successful cancellation.

- **Helper Functions**
  - `calculate_gst(amount)`: Calculates GST (18%) for the provided amount.
  - `generate_invoice_pdf(order)`: Uses ReportLab to generate a PDF invoice that includes company details, order details (order number, date, shipping address), a table of order items, and totals (subtotal, GST, grand total).
  - `send_order_confirmation_email(order, invoice_pdf)`: Sends an HTML email with the PDF invoice attached to the user after a successful checkout.
  - `send_order_cancellation_email(order)`: Sends an email notifying the user of order cancellation.

- **Error Handling**
  - Returns appropriate HTTP status codes (e.g., 400 for bad requests, 404 for not found).
  - Handles scenarios such as an empty cart, insufficient inventory, or invalid payment data.

## Endpoints

### Checkout

- **URL**: `/api/orders/checkout/`
- **Method**: `POST`
- **Authentication**: Required (JWT token)
- **Description**: Creates an order from the authenticated user's cart.
- **Request Body**:
  ```json
  {
      "address_id": 1,
      "payment_data": {"simulate_failure": false}
  }


### Success Response (201 Created):

```json
{
    "order_number": "ORD-XXXXXXXX",
    "user": 1,
    "address": 1,
    "total_price": "1234.56",
    "payment_status": "COMPLETED",
    "status": "PROCESSING",
    
}

```

###	400 Bad Request if the cart is empty, no cart exists, or inventory is insufficient.

- **URL**: `/api/orders/history/`
- **Method**: `GET`
- **Authentication**: Required (JWT token)
- **Description**: Retrieves a list of past orders for the authenticated user.
- **Request Body**:
  ```json
  [
    {
        "order_number": "ORD-XXXXXXXX",
        "total_price": "1234.56",
        "status": "PROCESSING",
        "created_at": "2022-01-01T12:00:00Z",
      
    },
    
  ]


### Success Response (201 Created):

```json
{
    "order_number": "ORD-XXXXXXXX",
    "user": 1,
    "address": 1,
    "total_price": "1234.56",
    "payment_status": "COMPLETED",
    "status": "PROCESSING",
    
}
```


# Shipping API Documentation

## Track Shipment
- **URL**: `/api/shipping/track/{awb_number}/`
- **Method**: `GET`
- **Auth Required**: Yes
- **Description**: Track shipment status using AWB number

### Success Response (200 OK):
```json
{
    "awb_number": "123456789",
    "current_status": "In Transit",
    "current_location": "Mumbai Hub",
    "expected_delivery_date": "2024-03-25",
    "tracking_history": [
        {
            "status": "Picked Up",
            "location": "Delhi Warehouse",
            "timestamp": "2024-03-22T10:00:00Z"
        }
    ]
}
```

## Generate Shipping Label
- **URL**: `/api/shipping/label/{order_id}/`
- **Method**: `GET`
- **Auth Required**: Yes
- **Description**: Generate shipping label for an order

### Success Response (200 OK):
```json
{
    "label_url": "https://api.example.com/labels/123.pdf",
    "shipping_details": {
        "courier": "Shiprocket Express",
        "service_type": "Standard Delivery",
        "estimated_delivery": "2024-03-25"
    }
}
```

## Get Shipping Rates
- **URL**: `/api/shipping/rates/`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
```json
{
    "pickup_pincode": "110001",
    "delivery_pincode": "400001",
    "weight": "1.5",
    "dimensions": {
        "length": 10,
        "width": 10,
        "height": 10
    }
}
```

### Success Response (200 OK):
```json
{
    "available_services": [
        {
            "courier": "Shiprocket Express",
            "rate": "150.00",
            "estimated_days": "2-3"
        }
    ]
}
```

# Payment API Documentation

## Payment Gateway Integration
- **URL**: `/api/payments/initiate/`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
```json
{
    "order_id": "ORD-123456",
    "amount": "1500.00",
    "currency": "INR",
    "payment_method": "card"
}
```

### Success Response (200 OK):
```json
{
    "payment_id": "PAY-123456",
    "checkout_url": "https://payment-gateway.com/checkout/123",
    "status": "pending"
}
```

## Payment Webhook
- **URL**: `/api/payments/webhook/`
- **Method**: `POST`
- **Auth Required**: No (but requires webhook signature verification)
- **Request Body**:
```json
{
    "payment_id": "PAY-123456",
    "order_id": "ORD-123456",
    "status": "completed",
    "amount": "1500.00"
}
```

## Check Payment Status
- **URL**: `/api/payments/status/{payment_id}/`
- **Method**: `GET`
- **Auth Required**: Yes

### Success Response (200 OK):
```json
{
    "payment_id": "PAY-123456",
    "status": "completed",
    "amount": "1500.00",
    "payment_method": "card",
    "timestamp": "2024-03-22T10:00:00Z"
}
```

## Process Refund
- **URL**: `/api/payments/refund/`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
```json
{
    "order_id": "ORD-123456",
    "amount": "1500.00",
    "reason": "Customer requested refund"
}
```

### Success Response (200 OK):
```json
{
    "refund_id": "REF-123456",
    "status": "processing",
    "amount": "1500.00",
    "estimated_days": "5-7"
}
```

## Payment History
- **URL**: `/api/payments/history/`
- **Method**: `GET`
- **Auth Required**: Yes
- **Query Parameters**:
  - `page`: Page number (optional)
  - `limit`: Results per page (optional)
  - `start_date`: Filter by start date (optional)
  - `end_date`: Filter by end date (optional)

### Success Response (200 OK):
```json
{
    "total": 50,
    "page": 1,
    "limit": 10,
    "results": [
        {
            "payment_id": "PAY-123456",
            "order_id": "ORD-123456",
            "amount": "1500.00",
            "status": "completed",
            "payment_method": "card",
            "timestamp": "2024-03-22T10:00:00Z"
        }
    ]
}
```

# Shipping API Documentation

## Track Shipment
- **URL**: `/api/shipping/track/{awb_number}/`
- **Method**: `GET`
- **Auth Required**: Yes
- **Description**: Track shipment status using AWB number

### Success Response (200 OK):
```json
{
    "awb_number": "123456789",
    "current_status": "In Transit",
    "current_location": "Mumbai Hub",
    "expected_delivery_date": "2024-03-25",
    "tracking_history": [
        {
            "status": "Picked Up",
            "location": "Delhi Warehouse",
            "timestamp": "2024-03-22T10:00:00Z"
        }
    ]
}
```

## Generate Shipping Label
- **URL**: `/api/shipping/label/{order_id}/`
- **Method**: `GET`
- **Auth Required**: Yes
- **Description**: Generate shipping label for an order

### Success Response (200 OK):
```json
{
    "label_url": "https://api.example.com/labels/123.pdf",
    "shipping_details": {
        "courier": "Shiprocket Express",
        "service_type": "Standard Delivery",
        "estimated_delivery": "2024-03-25"
    }
}
```

## Get Shipping Rates
- **URL**: `/api/shipping/rates/`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
```json
{
    "pickup_pincode": "110001",
    "delivery_pincode": "400001",
    "weight": "1.5",
    "dimensions": {
        "length": 10,
        "width": 10,
        "height": 10
    }
}
```

### Success Response (200 OK):
```json
{
    "available_services": [
        {
            "courier": "Shiprocket Express",
            "rate": "150.00",
            "estimated_days": "2-3"
        }
    ]
}
```

# Payment API Documentation

## Payment Gateway Integration
- **URL**: `/api/payments/initiate/`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
```json
{
    "order_id": "ORD-123456",
    "amount": "1500.00",
    "currency": "INR",
    "payment_method": "card"
}
```

### Success Response (200 OK):
```json
{
    "payment_id": "PAY-123456",
    "checkout_url": "https://payment-gateway.com/checkout/123",
    "status": "pending"
}
```

## Payment Webhook
- **URL**: `/api/payments/webhook/`
- **Method**: `POST`
- **Auth Required**: No (but requires webhook signature verification)
- **Request Body**:
```json
{
    "payment_id": "PAY-123456",
    "order_id": "ORD-123456",
    "status": "completed",
    "amount": "1500.00"
}
```

## Check Payment Status
- **URL**: `/api/payments/status/{payment_id}/`
- **Method**: `GET`
- **Auth Required**: Yes

### Success Response (200 OK):
```json
{
    "payment_id": "PAY-123456",
    "status": "completed",
    "amount": "1500.00",
    "payment_method": "card",
    "timestamp": "2024-03-22T10:00:00Z"
}
```

## Process Refund
- **URL**: `/api/payments/refund/`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body**:
```json
{
    "order_id": "ORD-123456",
    "amount": "1500.00",
    "reason": "Customer requested refund"
}
```

### Success Response (200 OK):
```json
{
    "refund_id": "REF-123456",
    "status": "processing",
    "amount": "1500.00",
    "estimated_days": "5-7"
}
```

## Payment History
- **URL**: `/api/payments/history/`
- **Method**: `GET`
- **Auth Required**: Yes
- **Query Parameters**:
  - `page`: Page number (optional)
  - `limit`: Results per page (optional)
  - `start_date`: Filter by start date (optional)
  - `end_date`: Filter by end date (optional)

### Success Response (200 OK):
```json
{
    "total": 50,
    "page": 1,
    "limit": 10,
    "results": [
        {
            "payment_id": "PAY-123456",
            "order_id": "ORD-123456",
            "amount": "1500.00",
            "status": "completed",
            "payment_method": "card",
            "timestamp": "2024-03-22T10:00:00Z"
        }
    ]
}
```

# Analytics API Documentation

## Overview
The Analytics module provides comprehensive data collection and reporting capabilities for the e-commerce platform. It automatically tracks user activities, order patterns, search behaviors, and detailed API events to provide valuable business insights.

## Features
- **Automatic Data Collection**: User activities, orders, searches, and API events are automatically tracked via Django signals and middleware
- **User Activity Tracking**: Login/logout events, page views, and user engagement metrics
- **Order Analytics**: Order creation, completion, and cancellation tracking with revenue metrics
- **Search Analytics**: Search queries, results, and user search patterns
- **Enhanced API Event Tracking**: Comprehensive API request/response monitoring with user context, error tracking, and performance metrics
- **Advanced Analytics Models**: Sales metrics, product analytics, conversion funnels, cart abandonment analytics, and customer lifetime value tracking
- **Admin Dashboard**: Enhanced admin interface with advanced filtering, searching, and analytics visualization
- **Real-time Monitoring**: Live API performance monitoring and error tracking through middleware
- **Security Auditing**: IP address tracking, user agent logging, and session monitoring for security analysis
- **Performance Monitoring**: Request/response size tracking, response time analysis, and performance indicators

## Admin Interface Security and Permissions

All analytics models implement strict security measures:

### Read-Only Analytics Data
- **No Add Permissions**: All analytics admin interfaces disable add functionality (`has_add_permission` returns `False`)
- **Automatic Data Generation**: Analytics data is generated automatically through signals, middleware, and background processes
- **Data Integrity**: Prevents manual data manipulation that could compromise analytics accuracy

### Enhanced Security Features
- **IP Address Tracking**: All user activities and API events include IP address logging
- **Session Monitoring**: Session IDs tracked for user journey analysis
- **User Agent Logging**: Browser and device information captured for security analysis
- **Error Tracking**: Comprehensive error logging with stack traces for debugging

### Performance Monitoring
- **Response Time Tracking**: All API requests monitored for performance
- **Request/Response Size Monitoring**: Data transfer metrics for optimization
- **Performance Indicators**: Visual indicators for fast/slow/critical response times
- **Endpoint Analysis**: Built-in tools for analyzing API endpoint performance

## Enhanced Analytics Models

The analytics system now includes advanced models for comprehensive business intelligence:

### Order Analytics
- **Model**: `OrderAnalytics`
- **Purpose**: Track daily order metrics and revenue performance
- **Key Fields**: `date`, `total_orders`, `total_revenue`, `avg_order_value`, `shipping_revenue`
- **Admin Access**: Read-only access in Django admin under Analytics section
- **Permissions**: No add/edit permissions - data generated automatically

### User Activity Log
- **Model**: `UserActivityLog`
- **Purpose**: Track user interactions and behavior patterns
- **Key Fields**: `user`, `activity_type`, `timestamp`, `ip_address`, `details`
- **Admin Access**: Read-only with detailed view links
- **Permissions**: No add/edit/delete permissions - data captured automatically
- **Features**: Advanced filtering by activity type, user, and timestamp

### Search Analytics
- **Model**: `SearchAnalytics`
- **Purpose**: Monitor search queries and user search behavior
- **Key Fields**: `query`, `user`, `timestamp`, `results_count`, `category`
- **Admin Access**: Read-only access with search and filtering capabilities
- **Permissions**: No add permissions - data captured automatically

### Error Log
- **Model**: `ErrorLog`
- **Purpose**: Track system errors and debugging information
- **Key Fields**: `timestamp`, `endpoint`, `error_message`, `stack_trace`, `user`
- **Admin Access**: Read-only with error preview functionality
- **Permissions**: No add/delete permissions - errors logged automatically
- **Features**: Error message preview, endpoint filtering, user tracking

### Sales Metrics
- **Model**: `SalesMetrics`
- **Purpose**: Track daily, weekly, and monthly sales performance
- **Key Fields**: `date`, `total_visitors`, `unique_visitors`, `conversion_rate`, `cart_abandonment_rate`, `new_customers`, `returning_customers`, `customer_acquisition_cost`
- **Admin Access**: Read-only with formatted display of rates and costs
- **Permissions**: No add permissions - metrics calculated automatically
- **Features**: Date hierarchy navigation, conversion rate formatting

### Product Analytics
- **Model**: `ProductAnalytics`
- **Purpose**: Monitor individual product performance and trends
- **Key Fields**: `product`, `date`, `views`, `cart_additions`, `purchases`, `revenue`, `conversion_rate`, `cart_to_purchase_rate`
- **Admin Access**: Read-only with product search and category filtering
- **Permissions**: No add permissions - analytics generated automatically
- **Features**: Revenue formatting, conversion rate calculations, product name display

### Conversion Funnel
- **Model**: `ConversionFunnel`
- **Purpose**: Track user journey from view to purchase
- **Key Fields**: `user`, `session_id`, `stage`, `product`, `timestamp`, `metadata`
- **Admin Access**: Read-only with stage badges and user/product filtering
- **Permissions**: No add permissions - funnel data captured automatically
- **Features**: Stage visualization, user and product name display, session tracking

### Cart Abandonment Analytics
- **Model**: `CartAbandonmentAnalytics`
- **Purpose**: Analyze cart abandonment patterns and recovery opportunities
- **Key Fields**: `user`, `session_id`, `cart_created`, `cart_abandoned`, `cart_value`, `items_count`, `abandonment_stage`, `recovery_email_sent`, `recovered`, `recovery_date`
- **Admin Access**: Read-only with recovery status tracking
- **Permissions**: No add permissions - abandonment data tracked automatically
- **Features**: Cart value formatting, recovery status badges, abandonment stage filtering

### Customer Lifetime Value
- **Model**: `CustomerLifetimeValue`
- **Purpose**: Calculate and track customer value over time
- **Key Fields**: `user`, `total_orders`, `total_spent`, `avg_order_value`, `first_order_date`, `last_order_date`, `predicted_ltv`, `customer_segment`, `last_updated`
- **Admin Access**: Read-only with customer segmentation and value formatting
- **Permissions**: No add permissions - LTV calculated automatically
- **Features**: Customer segment badges, monetary value formatting, order date tracking

## API Event Tracking

The system now includes comprehensive API event tracking through the `APITrackingMiddleware`:

### Enhanced APIEvent Model
The `APIEvent` model has been significantly enhanced with the following fields:
- **User Information**: `user` (linked to authenticated users)
- **Request Details**: `ip_address`, `user_agent`, `request_method`, `request_data`
- **Response Details**: `response_status_code`, `error_message`
- **Session Tracking**: `session_id`, `referer`
- **Performance Metrics**: `request_size`, `response_size`
- **Debugging Data**: Comprehensive error tracking and request/response logging

### Middleware Features
- **Automatic Tracking**: All API requests are automatically logged
- **User Context**: Associates API calls with authenticated users
- **Error Handling**: Captures and logs API errors with detailed context
- **Performance Monitoring**: Tracks request/response sizes and timing
- **Data Sanitization**: Removes sensitive information from logged data
- **Security Auditing**: IP address and user agent tracking for security analysis

### Admin Interface Enhancements
The `APIEventAdmin` has been enhanced with:
- **Advanced Filtering**: Filter by status, request method, response status code, timestamp, endpoint, and user
- **Enhanced Search**: Search across endpoints, usernames, emails, IP addresses, error messages, and user agents
- **User Pattern Analysis**: Built-in actions to analyze endpoint performance and user patterns
- **Organized Display**: Fieldsets for basic info, user details, request data, and response data
- **Read-only Fields**: All fields are read-only to prevent accidental modifications
- **Custom Methods**: 
  - `get_status_badge()`: Color-coded status indicators
  - `get_response_time()`: Formatted response time with performance indicators
  - `get_performance_indicator()`: Visual performance status (Fast/Slow/Critical)
  - `get_user_info()`: Formatted user display with username and email
  - `get_ip_address()`: Formatted IP address display
- **Performance Features**: Response time analysis, performance indicators, endpoint performance analysis
- **Security Features**: IP address tracking, user agent logging, session tracking
- **Permissions**: No add/delete permissions - events logged automatically via middleware

## Endpoints

### API Events Analytics
- **URL**: `/api/analytics/api-events/`
- **Method**: `GET`
- **Auth Required**: Yes (Admin only)
- **Description**: Retrieve comprehensive API event analytics
- **Query Parameters**:
  - `start_date`: Filter by start date (YYYY-MM-DD format, optional)
  - `end_date`: Filter by end date (YYYY-MM-DD format, optional)
  - `user_id`: Filter by specific user ID (optional)
  - `endpoint`: Filter by API endpoint (optional)
  - `status_code`: Filter by HTTP status code (optional)
  - `ip_address`: Filter by IP address (optional)

### Success Response (200 OK):
```json
{
    "count": 150,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "endpoint": "/api/products/",
            "method": "GET",
            "status": "success",
            "status_code": 200,
            "response_time": 0.15,
            "timestamp": "2024-03-22T10:00:00Z",
            "user": {
                "id": 1,
                "username": "testuser",
                "email": "test@example.com"
            },
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "request_size": 1024,
            "response_size": 2048,
            "session_id": "abc123def456",
            "referer": "https://example.com/products",
            "request_data": "{\"page\": 1, \"limit\": 10}",
            "error_message": null
        },
        {
            "id": 2,
            "endpoint": "/api/orders/",
            "method": "POST",
            "status": "error",
            "status_code": 400,
            "response_time": 0.25,
            "timestamp": "2024-03-22T10:05:00Z",
            "user": {
                "id": 2,
                "username": "customer2",
                "email": "customer2@example.com"
            },
            "ip_address": "192.168.1.2",
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
            "request_size": 2048,
            "response_size": 512,
            "session_id": "def456ghi789",
            "referer": "https://example.com/checkout",
            "request_data": "{\"items\": [], \"shipping_address\": {}}",
            "error_message": "Invalid shipping address format"
        }
    ]
}
```

## Enhanced Order Export Functionality

### Order Admin Export Features
The Order admin interface has been enhanced with comprehensive export capabilities:

#### CSV Export
- **Custom Action**: `export_orders_csv` action available in order list view
- **Comprehensive Fields**: Exports detailed order information including:
  - Basic order details (order number, status, dates)
  - User information (username, email, phone)
  - Payment details (status, method, transaction ID)
  - Shipping information (addresses, carrier, costs, tracking)
  - Order items with product details and quantities
  - Calculated metrics (total weight, item count)
- **Filename**: `orders_comprehensive_export_YYYY-MM-DD.csv`

#### Excel Export (Import/Export Integration)
- **Multiple Formats**: Supports CSV, XLS, and XLSX formats
- **Resource Class**: `OrderResource` with enhanced field mapping
- **Additional Fields**: 
  - `user_phone`: Customer phone number
  - `shipping_address_line2`: Secondary address line
  - `order_items_count`: Total number of items
  - `order_items_details`: Detailed item breakdown
  - `total_weight`: Calculated total weight
  - `razorpay_order_id`: Payment gateway reference

#### Export Field Mapping
```python
# OrderResource fields include:
fields = (
    'id', 'order_number', 'user__username', 'user__email', 'user_phone',
    'status', 'payment_status', 'payment_method', 'razorpay_order_id',
    'total_price', 'shipping_cost', 'created_at', 'updated_at',
    'shipping_name', 'shipping_address_line1', 'shipping_address_line2',
    'shipping_city', 'shipping_state', 'shipping_postal_code',
    'shipping_country', 'carrier', 'tracking_number',
    'estimated_delivery_date', 'order_items_count',
    'order_items_details', 'total_weight'
)
```

#### Dehydrate Methods
Custom data extraction methods for complex fields:
- `dehydrate_shipping_address_line2`: Extracts secondary address line
- `dehydrate_order_items_count`: Counts total order items
- `dehydrate_order_items_details`: Formats item details as readable string
- `dehydrate_total_weight`: Calculates total weight from all items

### Admin Interface Enhancements
- **Import/Export Templates**: Custom templates for import/export operations
- **Pagination**: 25 orders per page for better performance
- **Date Hierarchy**: Date-based navigation for order filtering
- **Enhanced Filtering**: Filter by status, payment status, creation date, and carrier
- **Search Functionality**: Search by order number, username, and email
- **Inline Order Items**: View and manage order items directly within order admin

### User Activity Analytics
- **URL**: `/api/analytics/user-activity/`
- **Method**: `GET`
- **Auth Required**: Yes (Admin only)
- **Description**: Retrieve user activity analytics data
- **Query Parameters**:
  - `start_date`: Filter by start date (YYYY-MM-DD format, optional)
  - `end_date`: Filter by end date (YYYY-MM-DD format, optional)
  - `user_id`: Filter by specific user ID (optional)
  - `activity_type`: Filter by activity type (LOGIN, LOGOUT, PAGE_VIEW, optional)

### Success Response (200 OK):
```json
{
    "count": 25,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "user": {
                "id": 1,
                "username": "testuser",
                "email": "test@example.com"
            },
            "activity_type": "LOGIN",
            "timestamp": "2024-03-22T10:00:00Z",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
            "additional_data": {}
        }
    ]
}
```

### Order Analytics
- **URL**: `/api/analytics/orders/`
- **Method**: `GET`
- **Auth Required**: Yes (Admin only)
- **Description**: Retrieve order analytics data
- **Query Parameters**:
  - `start_date`: Filter by start date (YYYY-MM-DD format, optional)
  - `end_date`: Filter by end date (YYYY-MM-DD format, optional)
  - `user_id`: Filter by specific user ID (optional)
  - `event_type`: Filter by event type (ORDER_CREATED, ORDER_COMPLETED, ORDER_CANCELLED, optional)

### Success Response (200 OK):
```json
{
    "count": 15,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "user": {
                "id": 1,
                "username": "testuser",
                "email": "test@example.com"
            },
            "order": {
                "order_number": "ORD-12345678",
                "total_price": "1500.00",
                "status": "COMPLETED"
            },
            "event_type": "ORDER_COMPLETED",
            "timestamp": "2024-03-22T10:30:00Z",
            "order_value": "1500.00",
            "additional_data": {
                "payment_method": "card",
                "items_count": 3
            }
        }
    ]
}
```

### Search Analytics
- **URL**: `/api/analytics/searches/`
- **Method**: `GET`
- **Auth Required**: Yes (Admin only)
- **Description**: Retrieve search analytics data
- **Query Parameters**:
  - `start_date`: Filter by start date (YYYY-MM-DD format, optional)
  - `end_date`: Filter by end date (YYYY-MM-DD format, optional)
  - `user_id`: Filter by specific user ID (optional)
  - `query`: Filter by search query (optional)

### Success Response (200 OK):
```json
{
    "count": 30,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "user": {
                "id": 1,
                "username": "testuser",
                "email": "test@example.com"
            },
            "query": "smartphone",
            "timestamp": "2024-03-22T10:15:00Z",
            "results_count": 5,
            "additional_data": {
                "search_type": "product",
                "filters_applied": ["category", "price_range"]
            }
        }
    ]
}
```

### Enhanced Analytics Summary
- **URL**: `/api/analytics/summary/`
- **Method**: `GET`
- **Auth Required**: Yes (Admin only)
- **Description**: Get comprehensive aggregated analytics summary including API performance metrics
- **Query Parameters**:
  - `period`: Time period for summary (day, week, month, year, optional, defaults to month)

### Success Response (200 OK):
```json
{
    "period": "month",
    "start_date": "2024-03-01",
    "end_date": "2024-03-31",
    "user_activities": {
        "total_logins": 150,
        "unique_users": 45,
        "page_views": 1200
    },
    "orders": {
        "total_orders": 25,
        "completed_orders": 20,
        "cancelled_orders": 2,
        "total_revenue": "45000.00",
        "average_order_value": "1800.00"
    },
    "searches": {
        "total_searches": 300,
        "unique_queries": 180,
        "average_results_per_search": 4.2,
        "top_search_terms": [
            {"query": "smartphone", "count": 45},
            {"query": "laptop", "count": 32},
            {"query": "headphones", "count": 28}
        ]
    },
    "api_performance": {
        "total_requests": 5000,
        "success_rate": 98.5,
        "average_response_time": 0.25,
        "error_rate": 1.5,
        "top_endpoints": [
            {"endpoint": "/api/products/", "requests": 1200},
            {"endpoint": "/api/cart/", "requests": 800},
            {"endpoint": "/api/orders/", "requests": 600}
        ],
        "error_breakdown": {
            "4xx_errors": 50,
            "5xx_errors": 25
        }
    },
    "sales_metrics": {
        "conversion_rate": 3.2,
        "cart_abandonment_rate": 68.5,
        "average_customer_lifetime_value": "2500.00"
    }
}
```

### Error Responses

#### 401 Unauthorized:
```json
{
    "detail": "Authentication credentials were not provided."
}
```

#### 403 Forbidden:
```json
{
    "detail": "You do not have permission to perform this action."
}
```

#### 400 Bad Request:
```json
{
    "error": "Invalid date format. Use YYYY-MM-DD."
}
```

## Data Collection

The enhanced analytics system automatically collects data through multiple mechanisms:

### Django Signals
- **User Activities**: Triggered on user login/logout and can be manually triggered for page views
- **Order Events**: Automatically tracked when orders are created, completed, or cancelled
- **Search Events**: Captured when users perform searches through the unified search API

### Middleware Integration
- **API Event Tracking**: The `APITrackingMiddleware` automatically captures all API requests and responses
- **Real-time Monitoring**: Live tracking of API performance, errors, and user behavior
- **Security Auditing**: Automatic logging of IP addresses, user agents, and session information
- **Error Tracking**: Comprehensive error logging with context and debugging information

### Enhanced Data Points
- **User Context**: All events are linked to authenticated users when available
- **Performance Metrics**: Request/response times, data sizes, and throughput measurements
- **Error Analysis**: Detailed error messages, stack traces, and failure patterns
- **Business Intelligence**: Sales metrics, conversion funnels, and customer lifetime value calculations

## Enhanced Admin Interface

All analytics data can be viewed and managed through the enhanced Django admin interface:

### Core Analytics
- `/admin/analytics/useractivity/` - User activity logs with enhanced filtering
- `/admin/analytics/orderanalytics/` - Order analytics with revenue tracking
- `/admin/analytics/searchanalytics/` - Search analytics with pattern analysis

### Enhanced Analytics Models
- `/admin/core/salesmetrics/` - Sales performance metrics and trends
- `/admin/core/productanalytics/` - Product-specific analytics and insights
- `/admin/core/conversionfunnel/` - Conversion funnel analysis
- `/admin/core/cartabandonmentanalytics/` - Cart abandonment tracking
- `/admin/core/customerlifetimevalue/` - Customer value analytics

### API Event Monitoring
- `/admin/analytics/apievent/` - Comprehensive API event tracking with:
  - Advanced filtering by user, endpoint, status code, and date ranges
  - Search functionality across all relevant fields
  - User pattern analysis tools
  - Error tracking and debugging capabilities
  - Performance monitoring and optimization insights

### Admin Features
- **Enhanced Filtering**: Multi-field filtering for precise data analysis
- **Advanced Search**: Full-text search across all analytics data
- **User Pattern Analysis**: Built-in tools to analyze user behavior patterns
- **Export Capabilities**: Export analytics data for external analysis
- **Real-time Updates**: Live data updates for monitoring active systems
- **Security Auditing**: IP tracking and session analysis for security monitoring

## Middleware Configuration

The analytics system includes the `APITrackingMiddleware` which has been integrated into the Django middleware stack:

### Middleware Setup
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'analytics.middleware.APITrackingMiddleware',  # Added for comprehensive API tracking
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### Middleware Features
- **Automatic API Tracking**: Captures all API requests and responses
- **User Association**: Links API events to authenticated users
- **Error Handling**: Comprehensive error tracking and logging
- **Performance Monitoring**: Request/response time and size tracking
- **Security Auditing**: IP address and user agent logging
- **Data Sanitization**: Removes sensitive data from logs

## Database Migrations

The enhanced analytics system includes new database migrations:

### APIEvent Model Enhancements
- **Migration**: `0004_apievent_error_message_apievent_ip_address_and_more.py`
- **New Fields**: `user`, `ip_address`, `user_agent`, `request_method`, `request_data`, `response_status_code`, `error_message`, `session_id`, `referer`, `request_size`, `response_size`
- **New Indexes**: Optimized indexes for `timestamp`/`status`, `user`/`timestamp`, `endpoint`/`status`, and `ip_address`/`timestamp`

### Performance Optimizations
- **Database Indexes**: Strategic indexes for improved query performance
- **Query Optimization**: Efficient data retrieval for analytics dashboards
- **Data Retention**: Configurable data retention policies for large datasets

## Critical E-commerce Configuration Issues

The following issues have been identified in the project configuration (primarily in `settings.py`):

- **DEBUG Mode Enabled**: DEBUG is set to True, which is a security risk in production as it can expose sensitive information.
- **Insecure CORS Settings**: CORS_ALLOW_ALL_ORIGINS is set to True, which should be restricted in production to prevent unauthorized access.
- **Placeholder API Keys**: Razorpay and Shiprocket use dummy keys as defaults, which need to be replaced with actual credentials for live operations.
- **Email Configuration**: Set to Gmail SMTP with commented-out alternatives (e.g., GoDaddy); ensure proper setup for production email sending.
- **Commented-out Production Settings**: Security features like SECURE_SSL_REDIRECT, SESSION_COOKIE_SECURE, and AWS S3 storage are commented out and need enabling for production.
- **Analytics Data Privacy**: Ensure compliance with data protection regulations when collecting user analytics data.
- **API Rate Limiting**: Consider implementing rate limiting to prevent abuse of the enhanced API tracking system.

Address these before deploying to production to ensure security and functionality.

# Email Verification API Documentation

## Resend Verification Email

### Endpoint
- **URL**: `/api/users/resend-verification-email/`
- **Method**: `POST`
- **Auth Required**: Yes (JWT Token)
- **Rate Limiting**: 2 requests per minute per IP address
- **Description**: Resends email verification link to authenticated users who haven't verified their email address

### Purpose
This endpoint allows authenticated users to request a new verification email for their account if:
- Their original verification email was not received
- The verification link has expired
- They need to resend the verification for any reason

The endpoint implements rate limiting (5 attempts per day per email address) to prevent abuse and includes comprehensive error handling for various scenarios. The endpoint automatically uses the authenticated user's email address for identity verification.

### Authentication
This endpoint requires a valid JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

### Request Format

#### Required Parameters
```json
{}
```
*Note: No request body parameters are required. The endpoint automatically uses the authenticated user's email address.*

#### Request Headers
```
Content-Type: application/json
Authorization: Bearer <your_jwt_token>
```

### Response Formats

#### Success Response (200 OK)
```json
{
    "message": "Please verify your email at user@example.com before logging in.",
    "stored_email_address": "user@example.com",
    "email_sent": true,
    "verification_required": true,
    "remaining_attempts": 4
}
```

#### Rate Limit Exceeded (429 Too Many Requests)
```json
{
    "error": "Daily email resend limit exceeded (5 attempts per day)",
    "attempts_remaining": 0,
    "support_contact": "support@gujjumasala.com",
    "message": "Please contact support if you continue to have issues with email verification"
}
```

#### Email Delivery Failed (500 Internal Server Error)
```json
{
    "error": "Failed to send verification email. Please try again later or contact support.",
    "stored_email_address": "user@example.com",
    "email_sent": false,
    "action_required": "contact_support",
    "remaining_attempts": 3
}
```

#### User Account Inactive (403 Forbidden)
```json
{
    "error": "User account is inactive. Please contact support.",
    "email_sent": false
}
```

#### Email Already Verified (400 Bad Request)
```json
{
    "error": "Email address is already verified.",
    "stored_email_address": "user@example.com",
    "email_sent": false
}
```

#### Authentication Required (401 Unauthorized)
```json
{
    "detail": "Authentication credentials were not provided."
}
```

#### Invalid Token (401 Unauthorized)
```json
{
    "detail": "Given token not valid for any token type",
    "code": "token_not_valid",
    "messages": [
        {
            "token_class": "AccessToken",
            "token_type": "access",
            "message": "Token is invalid or expired"
        }
    ]
}
```

### Error Codes

| Status Code | Error Type | Description |
|-------------|------------|-------------|
| 200 | Success | Verification email sent successfully |
| 400 | Bad Request | Email already verified |
| 401 | Unauthorized | Authentication credentials not provided or invalid token |
| 403 | Forbidden | User account is inactive |
| 429 | Too Many Requests | Daily rate limit exceeded (5 attempts per day) |
| 500 | Internal Server Error | Email delivery failed |

### Rate Limiting Details

#### Daily Limits
- **Limit**: 5 resend attempts per email address per day
- **Reset**: Limits reset at midnight UTC
- **Tracking**: Attempts are tracked per email address, not per IP
- **Cleanup**: Old attempt records are automatically cleaned up

#### Rate Limit Response Fields
- `attempts_remaining`: Number of attempts left for the day
- `support_contact`: Contact email when limit is exceeded
- `message`: Helpful message directing users to support

### Security Features

#### Input Validation
- Email format validation using Django's built-in validators
- Required field validation
- Sanitization of input data

#### Rate Limiting Protection
- Per-email daily limits to prevent spam
- IP-based rate limiting (2 requests per minute)
- Automatic cleanup of old rate limit records

#### Email Delivery Validation
- Tracks email delivery success/failure
- Records failed delivery attempts
- Provides appropriate error messages for delivery failures

### Implementation Details

#### Database Models
- `EmailResendAttempt`: Tracks resend attempts with fields:
  - `email`: Email address
  - `attempted_at`: Timestamp of attempt
  - `success`: Whether the email was sent successfully
  - `ip_address`: IP address of the request

#### Email Verification Process
1. Validates email format and required fields
2. Checks if user exists with the provided email
3. Verifies email is not already verified
4. Checks daily rate limits for the email address
5. Generates new verification token and encrypted link
6. Sends verification email
7. Records the attempt for rate limiting
8. Returns appropriate response

#### Token Security
- Uses encrypted tokens with 24-hour expiration
- Tokens are URL-safe and base64 encoded
- Includes user ID and token type in encrypted payload
- Supports both traditional Django tokens and encrypted Fernet tokens

### Example Usage

#### cURL Example
```bash
# First, obtain JWT token by logging in
TOKEN="your_jwt_access_token_here"

curl -X POST \
  http://localhost:8000/api/users/resend-verification-email/ \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN"
```

#### JavaScript Example
```javascript
// Assuming you have the JWT token stored (e.g., in localStorage)
const token = localStorage.getItem('access_token');

const response = await fetch('/api/users/resend-verification-email/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  }
});

const data = await response.json();

if (response.ok) {
  console.log('Verification email sent:', data.message);
  console.log('Email address:', data.stored_email_address);
  console.log('Remaining attempts:', data.remaining_attempts);
} else {
  console.error('Error:', data.error);
  if (response.status === 401) {
    console.log('Authentication required - please log in');
  } else if (response.status === 429) {
    console.log('Contact support:', data.support_contact);
  }
}
```

### Related Endpoints

- **Email Verification**: `/api/users/email-verify/<uidb64>/<token>/` - Verify email with token
- **Encrypted Email Verification**: `/api/users/email-verify/?uid=<uid>&token=<token>` - Verify with encrypted token
- **User Registration**: `/api/users/register/` - Register new user with automatic verification email
- **User Login**: `/api/users/login/` - Login endpoint that checks email verification status

### Best Practices

#### Frontend Implementation
1. **User Feedback**: Provide clear feedback about rate limits and remaining attempts
2. **Error Handling**: Handle all error cases gracefully with user-friendly messages
3. **Rate Limit Awareness**: Show users their remaining attempts and reset time
4. **Support Contact**: Display support contact information when limits are exceeded

#### Backend Considerations
1. **Email Delivery Monitoring**: Monitor email delivery success rates
2. **Rate Limit Tuning**: Adjust rate limits based on usage patterns
3. **Cleanup Tasks**: Implement regular cleanup of old attempt records
4. **Security Monitoring**: Monitor for abuse patterns and suspicious activity
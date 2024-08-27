# API Documentation

## Overview
This document describes the endpoints available in the MyEcommerce API and how to interact with them.

## Authentication
This API uses JWT (JSON Web Tokens) for authentication. To access protected endpoints, you need to include the JWT token in the `Authorization` header of your requests. Tokens can be obtained by logging in through the provided login endpoint.


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
    "birthdate": "[date in YYYY-MM-DD format optional]",
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
* **Data Constraints (Request Body):**


```json
{
  "login": "[username or phone number]",
  "password": "[password]"
}
`````

### Success Response (Code: 200 OK)



```json
{
  "refresh": "[refresh token]",
  "access": "[access token]"
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
* **Data Constraints (for POST request):**
```json

{
  "category_id": "[unique category id]",
  "name": "[category name]",
  "description": "[category description]",
  "image": "[upload image file]"
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
    "image": "url_to_image"
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
  "image": "url_to_newly_uploaded_image"
}

```
### Error Response :

```json
{
  "error": "Permissions required"
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
  "image": "[new image or keep existing]"
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
  "image": "url_to_updated_image"
}


```

### PUT/PATCH:
```json
{
  "category_id": "001",
  "name": "Updated Category Name",
  "description": "Updated description here",
  "tags": ["Updated", "Tags"],
  "image": "url_to_updated_image"
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

### Request Password Reset
- **URL**: `/api/users/password_reset/confirm/`
- **Method**: `POST`
- **Auth Required**: No
- **Request Body**:

```json
{
  "uid": "base64-encoded-user-id",
  "token": "password-reset-token",
  "new_password": "newpassword123",
  "re_new_password": "newpassword123"
}
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
  "category_id": 2,
  "inventory": 50,
  "price_weights": [
    {"price": "50000", "weight": "1kg"},
    {"price": "75000", "weight": "1.5kg"},
    {"price": "100000", "weight": "2kg"}
  ],
  "tags": ["Computing", "High-End"],
  "image_urls": ["http://example.com/image2.jpg"]
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
                    "image_url": "http://127.0.0.1:8000/media/products/1/bedroom.webp",
                    "description": "photo"
                }
            ]
        }
    ]
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
  "inventory": 50,
  "price_weights": "50000-1kg, 75000-1.5kg, 100000-2kg",
  "tags": ["Computing", "High-End"],
  "image_urls": ["http://example.com/image2.jpg"]
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
  "image_urls": ["http://example.com/image1.jpg"]
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
  "image_urls": ["http://example.com/updated_image.jpg"]
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

### Product Search:

- **URL**: `/api/products/search/?q=<query>`
- **Method**: `GET`
- **Auth Required**: No
- **Permissions**: Public access
- **Description**: Allows searching products by name, tags, or description.

## Example Request:
```json

GET /api/products/search/?q=Smartphone

```

### Success Response for Search (Code: 200 OK):

```json
[
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
        ]
    }
]
```

## Usage Example:

-**To manage products, users will**:

  1. Prepare the necessary data in the format specified above
  2. Authenticate to obtain necessary credentials if required
  3. Send appropriate HTTP requests to the endpoints to list, create, update, or delete product records
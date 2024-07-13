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
    "birthdate": "[date in YYYY-MM-DD format optional]"
  }

### Request Body Example

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

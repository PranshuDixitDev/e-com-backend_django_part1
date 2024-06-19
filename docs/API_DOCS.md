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
    "username": "[unique username]",
    "password": "[password]",
    "email": "[valid email address]",
    "phone_number": "[unique phone number in +919876543210 format]",
    "address": "[user address]",
    "postal_code": "[postal code]",
    "birthdate": "[date in YYYY-MM-DD format]"
  }


### Success Response (Code: 201 CREATED)


```json

{
  "id": "[new user id]",
  "username": "[username]"
}

`````
### Error Response:

```json

{
  "error": "A user with this phone number already exists."
}

`````

### 2. Login

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
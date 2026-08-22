# API Reference

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All endpoints require JWT token in Authorization header (except signup/login):
```
Authorization: Bearer <token>
```

---

## Authentication Endpoints

### Signup
**POST** `/auth/signup`

Create a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "securepassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "createdAt": "2024-01-15T10:30:00"
  }
}
```

### Login
**POST** `/auth/login`

Authenticate user and get JWT token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "firstName": "John",
    "lastName": "Doe",
    "createdAt": "2024-01-15T10:30:00"
  }
}
```

### Get Current User
**GET** `/auth/me`

Get authenticated user details.

**Response:** `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00"
}
```

### Logout
**POST** `/auth/logout`

Logout current user.

**Response:** `200 OK`
```json
{
  "message": "Logged out successfully"
}
```

---

## Tax Profile Endpoints

### Create Tax Profile
**POST** `/tax-profiles`

Create a new tax profile for the current user.

**Request:**
```json
{
  "date_of_birth": "1990-05-15",
  "pan_number": "ABCDE1234F",
  "aadhaar_number": "1234567890123456",
  "gender": "male",
  "marital_status": "married",
  "address": "123 Main St",
  "city": "Mumbai",
  "state": "Maharashtra",
  "pincode": "400001",
  "residential_status": "resident",
  "employment_type": "salaried",
  "salary_income": 1000000,
  "employer_name": "Tech Company Ltd",
  "employer_address": "Tech Park, Mumbai",
  "other_income": 50000,
  "other_income_type": "interest",
  "house_property_income": 100000,
  "property_description": "2BHK Flat in Mumbai",
  "investments": [
    {
      "type": "ppf",
      "amount": 150000
    }
  ],
  "deductions": [
    {
      "type": "80c",
      "amount": 150000
    }
  ],
  "tds_paid": 50000,
  "advance_tax_paid": 25000,
  "self_assessment_tax": 0,
  "bank_name": "HDFC Bank",
  "account_number": "12345678901234",
  "ifsc_code": "HDFC0000001",
  "account_type": "savings"
}
```

**Response:** `200 OK`
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "date_of_birth": "1990-05-15",
  "pan_number": "ABCDE1234F",
  // ... all fields from request
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

### Get Current User's Tax Profile
**GET** `/tax-profiles/current`

Get the current user's tax profile.

**Response:** `200 OK`
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  // ... profile fields
}
```

### Get Tax Profile by ID
**GET** `/tax-profiles/{profile_id}`

Get a specific tax profile (must be owner).

**Parameters:**
- `profile_id` (path): UUID of the tax profile

**Response:** `200 OK`
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  // ... profile fields
}
```

### Update Tax Profile
**PUT** `/tax-profiles/{profile_id}`

Update an existing tax profile.

**Parameters:**
- `profile_id` (path): UUID of the tax profile

**Request:**
```json
{
  "salary_income": 1200000,
  "tds_paid": 60000
  // ... other fields to update
}
```

**Response:** `200 OK`
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  // ... updated profile fields
}
```

### Upload Document
**POST** `/tax-profiles/{profile_id}/documents`

Upload supporting documents for tax profile.

**Parameters:**
- `profile_id` (path): UUID of the tax profile
- `file` (form-data): File to upload (PDF, JPG, PNG, max 10MB)

**Response:** `200 OK`
```json
{
  "message": "Document uploaded successfully"
}
```

### Delete Tax Profile
**DELETE** `/tax-profiles/{profile_id}`

Delete a tax profile.

**Parameters:**
- `profile_id` (path): UUID of the tax profile

**Response:** `200 OK`
```json
{
  "message": "Tax profile deleted successfully"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request data"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 404 Not Found
```json
{
  "detail": "Tax profile not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting
Currently no rate limiting. To be implemented in production.

## Version
API Version: v1 (2024-01-15)

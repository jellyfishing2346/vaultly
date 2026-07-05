# Vaultly API Documentation

This document provides comprehensive documentation for the Vaultly REST API.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Endpoints](#endpoints)
  - [Authentication](#authentication)
  - [User Profile](#user-profile)
  - [Transfers](#transfers)
- [Data Models](#data-models)
- [Idempotency](#idempotency)
- [Fraud Detection](#fraud-detection)

## Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://api.vaultly.com/api/v1
```

## Authentication

Vaultly uses JWT (JSON Web Token) authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

### Obtaining a Token

Tokens are obtained through the `/auth/login` or `/auth/signup` endpoints. Tokens expire after 15 minutes.

### Token Refresh

Currently, clients must re-authenticate to obtain a new token. Refresh token functionality is planned for future releases.

## Response Format

All API responses follow a consistent format:

### Success Response

```json
{
  "data": {
    // Response data specific to the endpoint
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2025-01-15T10:30:00Z"
  }
}
```

### Error Response

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional error details
    }
  }
}
```

## Error Handling

The API uses standard HTTP status codes:

- `200 OK` - Request succeeded
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `401 Unauthorized` - Missing or invalid authentication
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists
- `422 Unprocessable Entity` - Business logic validation failed
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

### Common Error Codes

| Code | Description |
|------|-------------|
| `INVALID_CREDENTIALS` | Email or password is incorrect |
| `USER_EXISTS` | Email or handle already registered |
| `INSUFFICIENT_FUNDS` | Account balance is too low |
| `INVALID_RECIPIENT` | Recipient handle does not exist |
| `SELF_TRANSFER` | Cannot transfer to yourself |
| `RATE_LIMIT_EXCEEDED` | Too many requests |

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **Transfers**: 10 transfers per minute per user
- **General**: 100 requests per minute per IP

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642237200
```

## Endpoints

### Authentication

#### Signup

Create a new user account.

**Endpoint:** `POST /auth/signup`

**Request Body:**
```json
{
  "email": "user@example.com",
  "handle": "johndoe",
  "full_name": "John Doe",
  "password": "securepassword123"
}
```

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Validation Rules:**
- `email`: Valid email address
- `handle`: 3-30 characters, lowercase alphanumeric and underscores only
- `full_name`: 1-100 characters
- `password`: 8-128 characters

**Notes:**
- New users receive a $100 signup bonus
- Email and handle must be unique
- Password is hashed using bcrypt

#### Login

Authenticate with existing credentials.

**Endpoint:** `POST /auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401 Unauthorized` - Invalid email or password

**Security Notes:**
- Response timing is uniform whether user exists or not
- Password verification uses constant-time comparison

### User Profile

#### Get Current User

Get the authenticated user's profile information.

**Endpoint:** `GET /me`

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "handle": "johndoe",
  "full_name": "John Doe"
}
```

#### Get Account Balance

Get the authenticated user's wallet account information.

**Endpoint:** `GET /me/account`

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "balance": 10000,
  "currency": "USD"
}
```

**Notes:**
- Balance is in cents (integer)
- Returns the user's wallet account only

### Transfers

#### Create Transfer

Send money to another user.

**Endpoint:** `POST /transfers`

**Headers:**
```
Authorization: Bearer <token>
Idempotency-Key: <unique_key>
```

**Request Body:**
```json
{
  "to_handle": "janedoe",
  "amount": 5000,
  "note": "Thanks for dinner!"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "amount": 5000,
  "note": "Thanks for dinner!",
  "replayed": false
}
```

**Response (201 Created - Held for Review):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending_review",
  "amount": 5000,
  "note": "Thanks for dinner!",
  "replayed": false
}
```

**Validation Rules:**
- `to_handle`: Must be a valid existing user handle
- `amount`: Must be positive integer (cents)
- `note`: Optional, max 280 characters
- `Idempotency-Key`: Required, 8-100 characters

**Error Responses:**
- `400 Bad Request` - Self-transfer attempted
- `404 Not Found` - Recipient handle not found
- `422 Unprocessable Entity` - Insufficient funds
- `429 Too Many Requests` - Rate limit exceeded

**Status Values:**
- `completed` - Transfer processed successfully
- `pending_review` - Held for fraud review
- `failed` - Transfer failed (rare)

#### Get Activity Feed

Get the user's transfer activity feed.

**Endpoint:** `GET /transfers/activity`

**Headers:**
```
Authorization: Bearer <token>
```

**Query Parameters:**
- `limit` (optional): Number of items to return (1-100, default: 25)

**Response (200 OK):**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "direction": "sent",
    "counterparty_handle": "janedoe",
    "counterparty_name": "Jane Doe",
    "amount": 5000,
    "note": "Thanks for dinner!",
    "status": "completed",
    "created_at": "2025-01-15T10:30:00Z"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "direction": "received",
    "counterparty_handle": "bobsmith",
    "counterparty_name": "Bob Smith",
    "amount": 2500,
    "note": "Split the bill",
    "status": "completed",
    "created_at": "2025-01-14T15:45:00Z"
  }
]
```

**Notes:**
- Returns both sent and received transfers
- Ordered by creation date (newest first)
- System transfers (like signup bonus) are excluded

## Data Models

### User

```typescript
interface User {
  id: string;          // UUID
  email: string;       // Email address
  handle: string;      // @handle (unique)
  full_name: string;   // Display name
}
```

### Account

```typescript
interface Account {
  id: string;          // UUID
  balance: number;     // Balance in cents (integer)
  currency: string;    // ISO currency code (e.g., "USD")
}
```

### Transfer

```typescript
interface Transfer {
  id: string;          // UUID
  status: string;      // "completed" | "pending_review" | "failed"
  amount: number;      // Amount in cents (integer)
  note: string | null; // Optional note
  replayed: boolean;   // True if idempotency replay occurred
}
```

### ActivityItem

```typescript
interface ActivityItem {
  id: string;                    // UUID
  direction: string;            // "sent" | "received"
  counterparty_handle: string;   // Other user's handle
  counterparty_name: string;     // Other user's name
  amount: number;                // Amount in cents
  note: string | null;           // Optional note
  status: string;                // Transfer status
  created_at: string;           // ISO 8601 timestamp
}
```

## Idempotency

All transfer requests support idempotency to prevent duplicate charges on network failures or retries.

### How It Works

1. Client generates a unique idempotency key (UUID recommended)
2. Include the key in the `Idempotency-Key` header
3. If the request fails, retry with the same key
4. Server returns the original result without charging again

### Example

```bash
# First attempt
curl -X POST https://api.vaultly.com/api/v1/transfers \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{"to_handle": "janedoe", "amount": 5000}'

# If network fails, retry with same key
curl -X POST https://api.vaultly.com/api/v1/transfers \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{"to_handle": "janedoe", "amount": 5000}'
```

### Response on Replay

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "amount": 5000,
  "note": null,
  "replayed": true  // Indicates this was a replayed request
}
```

### Key Scope

Idempotency keys are scoped per user. The same key can be used by different users without collision.

### Key Expiration

Idempotency keys are stored indefinitely for audit purposes, but only active transfers are checked for idempotency.

## Fraud Detection

Vaultly uses real-time fraud detection to protect users and the platform.

### How It Works

1. Each transfer is scored by an XGBoost machine learning model
2. The model analyzes multiple features (amount, frequency, patterns, etc.)
3. High-risk transfers are held for manual review
4. Low-risk transfers proceed automatically

### Scoring Features

- Transfer amount (normalized)
- Sender's recent transaction frequency
- Recipient's recent transaction frequency
- Time of day
- Account age
- Historical fraud patterns
- Note content analysis (planned)

### Thresholds

- **Low Risk** (score < 0.7): Transfer proceeds immediately
- **High Risk** (score ≥ 0.7): Transfer held for review

### Held Transfers

When a transfer is held for review:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending_review",
  "amount": 5000,
  "note": "Large transfer",
  "replayed": false
}
```

The transfer:
- Is recorded in the system
- Does not affect balances yet
- Will be reviewed by the fraud team
- Will be completed or rejected within 24 hours

### False Positives

If you believe a transfer was incorrectly held:
1. Contact support with the transfer ID
2. The fraud team will review manually
3. Legitimate transfers are typically approved within 1-2 hours

## Testing

### Demo Accounts

For testing, use these demo accounts:

| Email | Handle | Password |
|-------|--------|----------|
| alice@demo.vaultly | alice | demo123 |
| bob@demo.vaultly | bob | demo123 |
| charlie@demo.vaultly | charlie | demo123 |
| diana@demo.vaultly | diana | demo123 |

### cURL Examples

```bash
# Signup
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "handle": "testuser",
    "full_name": "Test User",
    "password": "password123"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@demo.vaultly",
    "password": "demo123"
  }'

# Get profile
curl -X GET http://localhost:8000/api/v1/me \
  -H "Authorization: Bearer <token>"

# Get balance
curl -X GET http://localhost:8000/api/v1/me/account \
  -H "Authorization: Bearer <token>"

# Send money
curl -X POST http://localhost:8000/api/v1/transfers \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{
    "to_handle": "bob",
    "amount": 5000,
    "note": "Test transfer"
  }'

# Get activity
curl -X GET http://localhost:8000/api/v1/transfers/activity \
  -H "Authorization: Bearer <token>"
```

## WebSocket API (Planned)

Real-time updates for:
- Transfer status changes
- Balance updates
- New activity feed items

WebSocket endpoints are planned for future releases.

## SDKs

Official SDKs are planned for:
- JavaScript/TypeScript
- Python
- iOS (Swift)
- Android (Kotlin)

## Support

For API support:
- Documentation: https://docs.vaultly.com
- Email: api-support@vaultly.com
- Issues: https://github.com/vaultly/vaultly/issues
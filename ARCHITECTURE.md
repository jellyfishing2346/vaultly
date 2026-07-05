# Vaultly Architecture

This document provides a comprehensive overview of Vaultly's system architecture, design decisions, and technical implementation details.

## Table of Contents

- [System Overview](#system-overview)
- [Technology Stack](#technology-stack)
- [Database Schema](#database-schema)
- [Double-Entry Ledger System](#double-entry-ledger-system)
- [Concurrency Control](#concurrency-control)
- [Fraud Detection System](#fraud-detection-system)
- [API Architecture](#api-architecture)
- [Frontend Architecture](#frontend-architecture)
- [Security Considerations](#security-considerations)
- [Scalability Considerations](#scalability-considerations)

## System Overview

Vaultly is a peer-to-peer payment system built on a double-entry ledger architecture with real-time fraud detection. The system consists of:

- **Frontend**: Next.js application with TypeScript and Tailwind CSS
- **Backend**: FastAPI application with PostgreSQL and Redis
- **Fraud Detection**: XGBoost machine learning model for real-time scoring
- **Infrastructure**: Docker Compose for local development

```
┌─────────────────┐         ┌─────────────────┐
│   Next.js App   │◄────────┤    FastAPI      │
│  (Frontend)     │  REST+WS │   (Backend)     │
└─────────────────┘         └────────┬────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
             ┌──────────┐    ┌──────────┐    ┌──────────────┐
             │PostgreSQL│    │  Redis   │    │XGBoost Model │
             │  Ledger  │    │ Cache    │    │Fraud Scoring │
             └──────────┘    └──────────┘    └──────────────┘
```

## Technology Stack

### Frontend
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript 5.0
- **Styling**: Tailwind CSS 3.4
- **State Management**: React hooks and context
- **HTTP Client**: Axios
- **Form Handling**: React Hook Form with Zod validation

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.9+
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Authentication**: JWT tokens
- **Machine Learning**: XGBoost via scikit-learn

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Process Management**: Uvicorn ASGI server
- **Database Migrations**: Alembic (planned)

## Database Schema

### Core Tables

#### Accounts
```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    balance DECIMAL(19, 4) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Ledger Entries
```sql
CREATE TABLE ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transfer_id UUID NOT NULL REFERENCES transfers(id),
    account_id UUID NOT NULL REFERENCES accounts(id),
    amount DECIMAL(19, 4) NOT NULL,
    entry_type VARCHAR(10) NOT NULL CHECK (entry_type IN ('debit', 'credit')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Transfers
```sql
CREATE TABLE transfers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key TEXT UNIQUE NOT NULL,
    from_account_id UUID NOT NULL REFERENCES accounts(id),
    to_account_id UUID NOT NULL REFERENCES accounts(id),
    amount DECIMAL(19, 4) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    fraud_score DECIMAL(5, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);
```

### Indexes
```sql
CREATE INDEX idx_ledger_entries_account_id ON ledger_entries(account_id);
CREATE INDEX idx_ledger_entries_transfer_id ON ledger_entries(transfer_id);
CREATE INDEX idx_transfers_from_account ON transfers(from_account_id);
CREATE INDEX idx_transfers_to_account ON transfers(to_account_id);
CREATE INDEX idx_transfers_status ON transfers(status);
CREATE INDEX idx_transfers_created_at ON transfers(created_at DESC);
```

## Double-Entry Ledger System

### Principles

Vaultly implements a double-entry bookkeeping system where every financial transaction creates equal and opposite ledger entries:

1. **Balance Derivation**: Account balances are derived from ledger entries, not stored as mutable state
2. **Atomic Transactions**: Every transfer creates exactly two entries (debit and credit)
3. **Reconciliation**: Cached balances can be verified against derived balances at any time

### Transfer Flow

```python
async def create_transfer(
    from_account: UUID,
    to_account: UUID,
    amount: Decimal,
    idempotency_key: str
) -> Transfer:
    async with database.transaction():
        # 1. Lock accounts with deterministic ordering
        first, second = sorted([from_account, to_account])
        accounts = await lock_accounts([first, second])
        
        # 2. Check sufficient funds
        if accounts[from_account].balance < amount:
            raise InsufficientFundsError()
        
        # 3. Create transfer record
        transfer = await create_transfer_record(
            from_account, to_account, amount, idempotency_key
        )
        
        # 4. Create ledger entries (double-entry)
        await create_ledger_entries(transfer.id, from_account, to_account, amount)
        
        # 5. Update cached balances
        await update_balances(from_account, to_account, amount)
        
        return transfer
```

### Reconciliation

The system can verify ledger integrity at any time:

```python
async def reconcile() -> List[Discrepancy]:
    """Find accounts where cached balance ≠ derived balance"""
    query = """
        SELECT a.id, a.balance AS cached, 
               COALESCE(SUM(l.amount), 0) AS derived
        FROM accounts a
        LEFT JOIN ledger_entries l ON l.account_id = a.id
        GROUP BY a.id, a.balance
        HAVING a.balance <> COALESCE(SUM(l.amount), 0)
    """
    return await database.fetch_all(query)
```

## Concurrency Control

### The Problem

When multiple transfers target the same account simultaneously, race conditions can cause:
- Money creation (double-spending)
- Money destruction (lost transfers)
- Incorrect balances

### Solution: Three-Layer Protection

#### 1. Row-Level Locking with Deterministic Ordering

```python
# Always lock accounts in consistent order to prevent deadlocks
first, second = sorted([from_account_id, to_account_id])
accounts = await conn.fetch(
    "SELECT * FROM accounts WHERE id = ANY($1) ORDER BY id FOR UPDATE",
    [first, second]
)
```

- `FOR UPDATE` locks rows until transaction commits
- Deterministic ordering prevents deadlocks
- Serializable isolation level prevents phantom reads

#### 2. Idempotency Keys

```sql
CREATE UNIQUE INDEX idx_transfers_idempotency_key 
ON transfers(idempotency_key);
```

- Clients provide unique idempotency keys
- Database UNIQUE constraint prevents duplicate transfers
- Retries return original transfer result

#### 3. Database Constraints

```sql
-- Prevent negative balances
ALTER TABLE accounts 
ADD CONSTRAINT check_non_negative_balance 
CHECK (balance >= 0);

-- Ensure transfer amounts are positive
ALTER TABLE transfers 
ADD CONSTRAINT check_positive_amount 
CHECK (amount > 0);
```

### Concurrency Testing

The system includes comprehensive concurrency tests:

```python
@pytest.mark.asyncio
async def test_concurrent_transfers_conserve_money():
    """Verify total balance remains constant under concurrent transfers"""
    initial_total = await get_total_balance()
    
    # Fire 100 concurrent transfers
    tasks = [transfer_money(account_a, account_b, 1.00) 
             for _ in range(100)]
    await asyncio.gather(*tasks)
    
    final_total = await get_total_balance()
    assert initial_total == final_total
```

## Fraud Detection System

### Architecture

```
Transfer Request → Feature Extraction → XGBoost Model → Risk Score
                                                    ↓
                                    Low Risk: Process normally
                                    High Risk: Hold for review
```

### Features

The fraud model uses these features:
- Transfer amount (normalized)
- Sender's transaction frequency
- Recipient's transaction frequency
- Time of day
- Geographic distance (if available)
- Account age
- Historical fraud patterns

### Integration

```python
async def score_transfer(transfer: Transfer) -> float:
    features = extract_features(transfer)
    score = fraud_model.predict_proba(features)[0][1]
    
    if score > FRAUD_THRESHOLD:
        transfer.status = 'held_for_review'
    else:
        transfer.status = 'approved'
    
    transfer.fraud_score = score
    return transfer
```

### Model Training

- **Algorithm**: XGBoost classifier
- **Training Data**: Historical transfer data with labeled fraud cases
- **Retraining**: Scheduled weekly with new data
- **Performance**: Target >95% precision, >90% recall

## API Architecture

### Design Principles

- **RESTful**: Resource-oriented URLs with proper HTTP methods
- **Versioned**: `/api/v1/` prefix for future compatibility
- **Consistent**: Standard response format across all endpoints
- **Secure**: JWT authentication, rate limiting, input validation

### Response Format

```json
{
  "data": { /* response data */ },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

### Error Format

```json
{
  "error": {
    "code": "INSUFFICIENT_FUNDS",
    "message": "Account has insufficient funds for this transfer",
    "details": {
      "balance": 50.00,
      "requested": 100.00
    }
  }
}
```

### Key Endpoints

- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User authentication
- `POST /api/v1/transfers` - Create transfer
- `GET /api/v1/transfers/:id` - Get transfer details
- `GET /api/v1/accounts/:id/transfers` - Get account transfer history
- `GET /api/v1/accounts/:id/balance` - Get account balance

## Frontend Architecture

### Component Structure

```
src/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   └── register/
│   ├── dashboard/
│   ├── send/
│   └── activity/
├── components/
│   ├── ui/
│   ├── forms/
│   └── layouts/
├── lib/
│   ├── api/
│   ├── hooks/
│   └── utils/
└── types/
```

### State Management

- **Authentication**: React Context with localStorage persistence
- **Forms**: React Hook Form with Zod schema validation
- **Data Fetching**: Custom hooks with Axios and error handling
- **Real-time Updates**: WebSocket connections for transfer status

### Performance Optimizations

- **Code Splitting**: Next.js automatic route-based splitting
- **Image Optimization**: Next.js Image component
- **Font Optimization**: Next.js Font with self-hosting
- **Caching**: React Query for API response caching

## Security Considerations

### Authentication & Authorization

- **Password Hashing**: bcrypt with salt rounds
- **JWT Tokens**: Short-lived access tokens (15 min) + refresh tokens (7 days)
- **Token Storage**: HttpOnly, Secure, SameSite cookies
- **Rate Limiting**: Redis-based per-IP and per-user limits

### Data Protection

- **Encryption**: TLS 1.3 for all communications
- **Input Validation**: Zod schemas on frontend, Pydantic on backend
- **SQL Injection Prevention**: Parameterized queries only
- **XSS Prevention**: React's automatic escaping, CSP headers

### Financial Security

- **Idempotency**: All write operations require idempotency keys
- **Atomic Transactions**: Database ACID guarantees
- **Audit Trail**: All financial operations logged
- **Reconciliation**: Daily automated balance verification

## Scalability Considerations

### Horizontal Scaling

- **Stateless Backend**: FastAPI can be horizontally scaled
- **Database Connection Pooling**: PgBouncer for connection management
- **Cache Sharding**: Redis Cluster for distributed caching
- **Load Balancing**: Nginx or cloud load balancer

### Database Scaling

- **Read Replicas**: Offload read queries to replicas
- **Partitioning**: Partition transfers by date range
- **Connection Pooling**: Optimize pool size based on load
- **Query Optimization**: Regular query performance analysis

### Caching Strategy

- **API Responses**: Cache GET requests with proper invalidation
- **Session Data**: Redis for fast session access
- **Fraud Model**: In-memory model serving for low latency
- **Static Assets**: CDN for frontend assets

### Monitoring & Observability

- **Application Metrics**: Prometheus endpoint for metrics
- **Logging**: Structured JSON logs with correlation IDs
- **Tracing**: Distributed tracing for request flows
- **Alerting**: Alerts for anomalies and performance degradation

## Future Enhancements

### Planned Features

- **Webhooks**: Real-time notifications for external systems
- **Multi-currency Support**: Multiple currency handling
- **Recurring Transfers**: Scheduled payment automation
- **Transaction Notes**: User-added memo fields
- **Advanced Fraud Features**: Behavioral biometrics, device fingerprinting

### Architecture Improvements

- **Event Sourcing**: Append-only event log for auditability
- **CQRS**: Separate read/write models for complex queries
- **Microservices**: Split fraud detection into separate service
- **Message Queue**: RabbitMQ/Kafka for async processing
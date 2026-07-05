# Changelog

All notable changes to Vaultly will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- WebSocket support for real-time updates
- Multi-currency support
- Recurring transfers
- Transaction memo enhancement
- Advanced fraud detection features
- Mobile applications (iOS/Android)

## [0.1.0] - 2025-01-15

### Added
- **Core Ledger System**
  - Double-entry bookkeeping implementation
  - Account management with derived balances
  - Transfer engine with atomic transactions
  - Ledger reconciliation system
  
- **Authentication**
  - User registration with email validation
  - JWT-based authentication
  - Secure password hashing with bcrypt
  - Session management

- **Transfer System**
  - P2P money transfers
  - Idempotency key support for safe retries
  - Transfer status tracking
  - Activity feed with sent/received history

- **Concurrency Control**
  - Row-level locking with deterministic ordering
  - Serializable transaction isolation
  - Race condition prevention
  - Comprehensive concurrency tests

- **Fraud Detection**
  - Real-time XGBoost fraud scoring
  - Feature extraction from transfer patterns
  - High-risk transfer hold system
  - Fraud model integration

- **API**
  - RESTful API with FastAPI
  - Comprehensive request/response schemas
  - Rate limiting with Redis
  - Error handling and validation

- **Frontend**
  - Next.js 14 application with App Router
  - User authentication flows
  - Money transfer interface
  - Activity feed display
  - Responsive design with Tailwind CSS

- **Infrastructure**
  - Docker Compose setup for local development
  - PostgreSQL database schema
  - Redis caching layer
  - Demo data seeding

- **Documentation**
  - Comprehensive README
  - Architecture documentation
  - API documentation
  - Deployment guide
  - Contribution guidelines

- **Testing**
  - Concurrency test suite
  - API integration tests
  - Ledger integrity tests
  - Fraud detection tests

### Security
- Password hashing with bcrypt
- JWT token authentication
- SQL injection prevention via parameterized queries
- Input validation on frontend and backend
- Rate limiting to prevent abuse

### Performance
- Database connection pooling
- Redis caching for frequently accessed data
- Optimized database queries with proper indexing
- Frontend code splitting and lazy loading

## [0.0.1] - 2025-01-10

### Added
- Initial project scaffold
- Basic FastAPI application structure
- Next.js frontend setup
- Database schema design
- Docker Compose configuration

---

## Version Format

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality additions
- **PATCH**: Backwards-compatible bug fixes

## Release Process

1. Update version in `backend/package.json` and `frontend/package.json`
2. Update this CHANGELOG.md
3. Create git tag: `git tag -a v0.1.0 -m "Release v0.1.0"`
4. Push tag: `git push origin v0.1.0`
5. Create GitHub release with changelog notes
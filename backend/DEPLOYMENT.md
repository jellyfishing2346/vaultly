# Deployment Guide

## Local Development

```bash
# Start services
docker compose up -d

# Run backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Production Deployment

### AWS Infrastructure

Recommended AWS setup:

1. **RDS PostgreSQL** - Managed database with automatic backups
2. **ElastiCache Redis** - Managed Redis for rate limiting
3. **ECS/Fargate** - Container orchestration for the FastAPI app
4. **Application Load Balancer** - HTTPS termination and routing
5. **CloudWatch** - Logging and monitoring

### Environment Variables

Set these in your production environment:

```bash
DATABASE_URL=postgresql://user:password@rds-endpoint:5432/vaultly
REDIS_URL=redis://elasticache-endpoint:6379/0
JWT_SECRET=<strong-random-32-char-string>
RATE_LIMIT_TRANSFERS_PER_MINUTE=10
```

### Security Considerations

1. **Database**: Use RDS with VPC, security groups, and SSL
2. **Redis**: Use ElastiCache with AUTH and VPC
3. **Secrets**: Store in AWS Secrets Manager, not environment variables
4. **HTTPS**: Force HTTPS via ALB with valid SSL certificate
5. **Rate Limiting**: Adjust based on your threat model
6. **JWT**: Use strong secret, consider shortening expiration

### Docker Build

```bash
# Build image
docker build -t vaultly-backend ./backend

# Tag for ECR
docker tag vaultly-backend:latest <account-id>.dkr.ecr.<region>.amazonaws.com/vaultly-backend:latest

# Push to ECR
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/vaultly-backend:latest
```

### Health Checks

The app includes a health check endpoint:
```bash
GET /health
# Returns: {"status": "ok"}
```

Configure your load balancer to use this for health checks.

### Database Migrations

For production, use a migration tool like Alembic instead of running SQL directly:

```bash
# Initialize Alembic (one-time)
alembic init alembic

# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

### Monitoring

1. **Application logs**: Send to CloudWatch Logs
2. **Metrics**: Track transfer volume, fraud scores, error rates
3. **Alerts**: Set up CloudWatch alarms for:
   - High error rates
   - Unusual transfer volumes
   - Database connection issues
   - Redis connectivity issues

### Scaling

- **Horizontal scaling**: Add more ECS tasks based on CPU/memory
- **Database**: RDS read replicas for read-heavy workloads
- **Redis**: Cluster mode for high throughput
- **Rate limiting**: Consider distributed rate limiting with Redis

### Backup Strategy

- **Database**: Enable RDS automated backups (7-35 day retention)
- **Point-in-time recovery**: Enable for RDS
- **Redis**: Enable AOF persistence, regular snapshots
- **Disaster recovery**: Cross-region replication for critical deployments
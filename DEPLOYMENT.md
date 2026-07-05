# Vaultly Deployment Guide

This guide covers deploying Vaultly to production infrastructure.

## Table of Contents

- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Frontend Deployment](#frontend-deployment)
- [Troubleshooting](#troubleshooting)

## Local Development

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Node.js 18+ and npm

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/vaultly.git
cd vaultly

# Start infrastructure services
docker compose up -d

# Run backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Run frontend (in a new terminal)
cd frontend
npm install
npm run dev
```

### Services

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Seed Demo Data

```bash
cd backend
python seed_demo_data.py
```

This creates 4 demo users with $100 each for testing.

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

## Frontend Deployment

### Vercel Deployment (Recommended)

1. **Connect Repository**
   ```bash
   # Install Vercel CLI
   npm i -g vercel

   # Deploy
   cd frontend
   vercel
   ```

2. **Environment Variables**
   Set these in Vercel project settings:
   ```
   NEXT_PUBLIC_API_URL=https://api.vaultly.com/api/v1
   ```

3. **Build Configuration**
   The `vercel.json` configuration:
   ```json
   {
     "buildCommand": "npm run build",
     "outputDirectory": ".next",
     "framework": "nextjs"
   }
   ```

### Docker Deployment

Build and deploy the frontend as a container:

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Production image
FROM base AS runner
WORKDIR /app
ENV NODE_ENV production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT 3000
CMD ["node", "server.js"]
```

Build and push:
```bash
docker build -t vaultly-frontend ./frontend
docker tag vaultly-frontend:latest <registry>/vaultly-frontend:latest
docker push <registry>/vaultly-frontend:latest
```

### Environment Variables

Frontend requires:
- `NEXT_PUBLIC_API_URL`: Backend API URL

### Performance Optimization

1. **Enable CDN**: Use Vercel's built-in CDN or Cloudflare
2. **Image Optimization**: Next.js Image component with remote patterns
3. **Code Splitting**: Automatic with Next.js App Router
4. **Font Optimization**: Use `next/font` for self-hosted fonts
5. **Cache Strategy**: Implement proper cache headers for static assets

## Troubleshooting

### Common Issues

#### Database Connection Errors

```bash
# Check PostgreSQL is running
docker compose ps postgres

# View logs
docker compose logs postgres

# Restart services
docker compose restart postgres
```

#### Redis Connection Errors

```bash
# Check Redis is running
docker compose ps redis

# Test connection
redis-cli -h localhost -p 6379 ping

# View logs
docker compose logs redis
```

#### Migration Failures

```bash
# Check current migration status
alembic current

# Rollback to previous version
alembic downgrade -1

# Force reset (development only)
alembic downgrade base
alembic upgrade head
```

#### Build Errors

```bash
# Clear Next.js cache
cd frontend
rm -rf .next
npm run build

# Clear Python cache
cd backend
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### Health Checks

Verify all services are healthy:

```bash
# Backend health
curl http://localhost:8000/health

# Database connectivity
docker compose exec postgres pg_isready

# Redis connectivity
docker compose exec redis redis-cli ping
```

### Log Locations

- **Backend logs**: `docker compose logs backend`
- **Frontend logs**: Vercel dashboard or container logs
- **Database logs**: CloudWatch Logs (AWS) or `docker compose logs postgres`
- **Redis logs**: CloudWatch Logs (AWS) or `docker compose logs redis`

### Getting Help

- **Documentation**: Check [ARCHITECTURE.md](../ARCHITECTURE.md) and [API.md](../API.md)
- **Issues**: Open an issue on GitHub
- **Support**: Contact deployment support at your organization
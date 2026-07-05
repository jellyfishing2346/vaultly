# Contributing to Vaultly

Thank you for your interest in contributing to Vaultly! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Welcome newcomers and help them learn
- Prioritize the project's collective success

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Node.js 18+
- npm or yarn

### Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/vaultly.git
   cd vaultly
   ```

3. Install dependencies:
   ```bash
   # Backend
   cd backend
   pip install -r requirements.txt
   
   # Frontend
   cd ../frontend
   npm install
   ```

4. Start infrastructure:
   ```bash
   docker compose up -d
   ```

5. Run the development servers:
   ```bash
   # Backend (terminal 1)
   cd backend
   uvicorn app.main:app --reload
   
   # Frontend (terminal 2)
   cd frontend
   npm run dev
   ```

## Development Workflow

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. Make your changes following the coding standards

3. Test your changes thoroughly

4. Commit your changes with a clear message:
   ```bash
   git commit -m "feat: add user authentication"
   # or
   git commit -m "fix: resolve race condition in transfer logic"
   ```

5. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

6. Create a pull request

## Coding Standards

### Python (Backend)

- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and single-purpose
- Use async/await for I/O operations

### TypeScript/JavaScript (Frontend)

- Follow ESLint configuration
- Use TypeScript strict mode
- Prefer functional programming patterns
- Use meaningful variable and function names
- Keep components small and focused

### Database

- Use snake_case for table and column names
- Always use parameterized queries
- Include foreign key constraints
- Add indexes for frequently queried columns

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v
```

### Frontend Tests

```bash
cd frontend
npm test
```

### Concurrency Tests

To verify the ledger integrity under high concurrency:

```bash
cd backend
pytest tests/test_concurrency.py -v
```

### Test Coverage

We aim for:
- Backend: >80% coverage
- Frontend: >70% coverage

## Submitting Changes

### Pull Request Guidelines

- **Title**: Use a clear, descriptive title (e.g., "feat: add two-factor authentication")
- **Description**: Explain the what, why, and how of your changes
- **Related Issues**: Link to related GitHub issues
- **Screenshots**: Include screenshots for UI changes
- **Testing**: Describe how you tested your changes

### PR Template

When creating a PR, please include:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added/updated
- [ ] All tests passing
```

## Reporting Issues

### Bug Reports

When reporting a bug, please include:

- **Description**: Clear description of the problem
- **Steps to Reproduce**: Detailed steps to reproduce the issue
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**: OS, Python/Node version, browser
- **Logs**: Relevant error messages or logs

### Feature Requests

When requesting a feature, please include:

- **Description**: Clear description of the desired feature
- **Use Case**: Why this feature would be useful
- **Alternatives**: Any alternative solutions you've considered
- **Implementation Ideas**: Any thoughts on how to implement it

## Areas Where We Need Help

We welcome contributions in these areas:

- **Frontend**: Mobile responsiveness, additional payment features
- **Backend**: Additional fraud detection features, performance optimization
- **Documentation**: Tutorials, examples, API documentation
- **Testing**: End-to-end tests, load testing
- **DevOps**: CI/CD improvements, deployment automation

## Questions?

Feel free to open an issue for questions or discussion. We're happy to help!

## License

By contributing to Vaultly, you agree that your contributions will be licensed under the Apache License 2.0.
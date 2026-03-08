
# AGENTS.md

A comprehensive guide for LLM agents on REST API development, coding standards, and implementation patterns.

---

## Project Overview

This document provides coding agents with the context, conventions, and instructions needed to build, maintain, and extend REST APIs effectively. Follow these guidelines to ensure consistency, security, and maintainability across all API implementations.

---

## REST API Design Principles

### Core Architecture

- **Use RESTful architecture** with standard HTTP methods (GET, POST, PUT, PATCH, DELETE)
- **Implement stateless communication** - each request must contain all necessary information
- **Design for loose coupling** using standard protocols and agreed data formats
- **Follow API-first development** - define contracts before implementation

### URL Structure

```
# Good examples
GET    /api/v1/users
POST   /api/v1/users
GET    /api/v1/users/{id}
PUT    /api/v1/users/{id}
DELETE /api/v1/users/{id}
GET    /api/v1/users/{id}/orders

# Bad examples
GET    /api/v1/getUsers
POST   /api/v1/createUser
GET    /api/v1/user?id=123
```

**Rules:**
- Use **nouns** for resources, not verbs
- Use **plural** naming for collections
- Use **lowercase** with hyphens for multi-word resources
- Include **version** in URL path from day one
- Keep URLs **intuitive and predictable**

### HTTP Methods

| Method | Purpose | Idempotent | Safe |
|--------|---------|------------|------|
| GET | Retrieve resource(s) | Yes | Yes |
| POST | Create new resource | No | No |
| PUT | Replace entire resource | Yes | No |
| PATCH | Partially update resource | No* | No |
| DELETE | Remove resource | Yes | No |

*PATCH idempotency depends on implementation

---

## HTTP Status Codes

Return **meaningful status codes** so clients understand outcomes without parsing response bodies.

### Success Codes (2xx)

- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful resource creation (include Location header)
- `204 No Content` - Successful DELETE or update with no response body

### Client Error Codes (4xx)

- `400 Bad Request` - Invalid request syntax or validation errors
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Authenticated but lacks permissions
- `404 Not Found` - Resource doesn't exist
- `405 Method Not Allowed` - HTTP method not supported
- `406 Not Acceptable` - Unsupported response format
- `409 Conflict` - Resource conflict (e.g., duplicate)
- `422 Unprocessable Entity` - Validation errors with semantic issues
- `429 Too Many Requests` - Rate limit exceeded

### Server Error Codes (5xx)

- `500 Internal Server Error` - Generic server error
- `502 Bad Gateway` - Invalid upstream response
- `503 Service Unavailable` - Server temporarily unavailable
- `504 Gateway Timeout` - Upstream timeout

---

## Response Format Standards

### Success Response Structure

```json
{
  "data": {
    "id": "uuid-string",
    "type": "users",
    "attributes": {
      "email": "user@example.com",
      "name": "John Doe",
      "createdAt": "2026-03-08T22:15:24Z"
    },
    "relationships": {
      "orders": {
        "links": {
          "related": "/api/v1/users/{id}/orders"
        }
      }
    }
  },
  "meta": {
    "requestId": "req-abc123",
    "timestamp": "2026-03-08T22:15:24Z"
  }
}
```

### Collection Response with Pagination

```json
{
  "data": [
    { "id": "1", "type": "users", "attributes": {...} },
    { "id": "2", "type": "users", "attributes": {...} }
  ],
  "meta": {
    "pagination": {
      "total": 150,
      "count": 20,
      "perPage": 20,
      "currentPage": 1,
      "totalPages": 8
    }
  },
  "links": {
    "self": "/api/v1/users?page=1",
    "first": "/api/v1/users?page=1",
    "last": "/api/v1/users?page=8",
    "next": "/api/v1/users?page=2",
    "prev": null
  }
}
```

### Error Response Structure

Follow **RFC 7807 Problem Details** format for error responses:

```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 400,
  "detail": "The request contains invalid data",
  "instance": "/api/v1/users",
  "traceId": "trace-xyz789",
  "errors": [
    {
      "source": { "pointer": "/data/attributes/email" },
      "code": "INVALID_FORMAT",
      "title": "Invalid Email Format",
      "detail": "Email must be a valid email address"
    },
    {
      "source": { "pointer": "/data/attributes/password" },
      "code": "MIN_LENGTH",
      "title": "Password Too Short",
      "detail": "Password must be at least 8 characters"
    }
  ]
}
```

**Error Response Rules:**
- Always return **Content-Type: application/json** or **application/problem+json**
- Include **human-readable messages** in the detail field
- Provide **machine-readable error codes** for programmatic handling
- Add **traceId** for debugging and support
- Use **JSON pointer** (RFC 6901) to indicate error location

---

## API Documentation

### OpenAPI Specification

Use **OpenAPI 3.1.0** or **3.2.0** for API documentation:

```yaml
openapi: 3.1.0
info:
  title: User Management API
  version: 1.0.0
  description: API for managing user accounts and profiles
  contact:
    name: API Support
    email: support@example.com

servers:
  - url: https://api.example.com/v1
    description: Production server
  - url: https://staging-api.example.com/v1
    description: Staging server

paths:
  /users:
    get:
      summary: List all users
      operationId: listUsers
      tags:
        - Users
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: limit
          in: query
          schema:
            type: integer
            default: 20
            maximum: 100
      responses:
        '200':
          description: Successful response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/UserCollection'
        '401':
          description: Unauthorized
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

components:
  schemas:
    User:
      type: object
      required:
        - email
        - name
      properties:
        id:
          type: string
          format: uuid
        email:
          type: string
          format: email
        name:
          type: string
          minLength: 1
          maxLength: 100
        createdAt:
          type: string
          format: date-time
    Error:
      type: object
      properties:
        type:
          type: string
          format: uri
        title:
          type: string
        status:
          type: integer
        detail:
          type: string
        traceId:
          type: string
```

**Documentation Requirements:**
- Write **OpenAPI specs in YAML** for better readability
- Include **examples** for all request/response bodies
- Document **authentication methods** clearly
- Specify **rate limits** in documentation
- Keep specs **self-contained** in single file when possible

---

## Security Best Practices

### Authentication & Authorization

- **Use HTTPS only** - never transmit sensitive data over unencrypted connections
- **Implement OAuth 2.0** or **JWT tokens** for stateless authentication
- **Validate all input** on server-side, never trust client
- **Use API keys** for service-to-service communication

### Rate Limiting

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1773008124
Retry-After: 3600
```

**When rate limited:**
```json
{
  "type": "https://api.example.com/errors/rate-limit",
  "title": "Rate Limit Exceeded",
  "status": 429,
  "detail": "Too many requests. Please retry after 1 hour.",
  "retryAfter": 3600
}
```

### Security Headers

Always include these headers in responses:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Content-Security-Policy: default-src 'self'`
- `X-Request-Id: <unique-id>` for tracing

---

## Code Style & Formatting

### TypeScript Configuration

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "lib": ["ES2022"],
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "./dist",
    "rootDir": "./src",
    "resolveJsonModule": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

### ESLint Configuration

```javascript
// eslint.config.js
import globals from "globals";
import pluginJs from "@eslint/js";
import tseslint from "typescript-eslint";
import pluginPrettier from "eslint-plugin-prettier";

export default [
  { files: ["**/*.{js,mjs,cjs,ts}"] },
  { languageOptions: { globals: globals.node } },
  pluginJs.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: {
      prettier: pluginPrettier,
    },
    rules: {
      "prettier/prettier": "error",
      "@typescript-eslint/no-unused-vars": "error",
      "@typescript-eslint/consistent-type-definitions": ["error", "type"],
      "@typescript-eslint/explicit-function-return-type": "warn",
      "no-console": "warn",
    },
  },
];
```

### Prettier Configuration

```json
{
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "semi": true,
  "singleQuote": true,
  "trailingComma": "es5",
  "bracketSpacing": true,
  "arrowParens": "always",
  "endOfLine": "lf",
  "overrides": [
    {
      "files": "*.json",
      "options": {
        "printWidth": 120
      }
    }
  ]
}
```

### Code Style Rules

- **Use TypeScript strict mode** for type safety
- **Single quotes** for strings (consistent with Prettier config)
- **No semicolons** if using Prettier with that configuration
- **Functional patterns** where possible (immutability, pure functions)
- **Explicit return types** on functions for better documentation
- **Consistent naming**: camelCase for variables/functions, PascalCase for types/classes
- **Max line length**: 100 characters

---

## Testing Instructions

### Test Structure

```typescript
// tests/users.test.ts
import { describe, it, expect, beforeEach } from 'vitest';
import { createUser, getUser, deleteUser } from '../src/users';

describe('Users API', () => {
  beforeEach(async () => {
    // Reset test database
  });

  describe('POST /users', () => {
    it('should create a user with valid data', async () => {
      const userData = { email: 'test@example.com', name: 'Test User' };
      const user = await createUser(userData);
      
      expect(user).toHaveProperty('id');
      expect(user.email).toBe(userData.email);
      expect(user.createdAt).toBeDefined();
    });

    it('should return 400 for invalid email', async () => {
      await expect(createUser({ email: 'invalid', name: 'Test' }))
        .rejects.toThrow('Invalid email format');
    });
  });

  describe('GET /users/:id', () => {
    it('should return 404 for non-existent user', async () => {
      await expect(getUser('non-existent-id'))
        .rejects.toThrowErrorMatchingInlineSnapshot('"User not found"');
    });
  });
});
```

### Testing Commands

```bash
# Run all tests
pnpm test

# Run tests with coverage
pnpm test --coverage

# Run specific test file
pnpm vitest run tests/users.test.ts

# Run tests matching pattern
pnpm vitest run -t "should create a user"

# Watch mode for development
pnpm vitest watch

# Run CI test suite
pnpm turbo run test --filter <package-name>
```

### Test Requirements

- **Minimum 80% code coverage** for all new code
- **Test all error scenarios** (4xx and 5xx responses)
- **Include integration tests** for API endpoints
- **Mock external dependencies** in unit tests
- **Run linting** before committing: `pnpm lint --filter <package-name>`

---

## Versioning Strategy

### URL Versioning (Recommended)

```
https://api.example.com/v1/users
https://api.example.com/v2/users
```

### Versioning Rules

- **Plan versioning from the start** - include v1 in initial release
- **Support minimum 2 versions** simultaneously during transition
- **Deprecate gradually** with 6-12 month notice
- **Document breaking changes** clearly in changelog
- **Use semantic versioning** for API versions (MAJOR.MINOR.PATCH)

### Deprecation Headers

```http
HTTP/1.1 200 OK
Deprecation: true
Sunset: Sat, 08 Mar 2027 00:00:00 GMT
Link: <https://api.example.com/v2/users>; rel="successor-version"
```

---

## Pagination & Filtering

### Query Parameters

```
GET /api/v1/users?page=1&limit=20&sort=-createdAt&filter[status]=active
```

### Supported Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `limit` | integer | 20 | Items per page (max: 100) |
| `sort` | string | -createdAt | Sort field (+asc, -desc) |
| `filter[field]` | string | - | Filter by field value |
| `fields` | string | all | Comma-separated fields to include |
| `include` | string | - | Related resources to include |

### Pagination Response

Always include pagination metadata in collection responses (see Response Format section above).

---

## Error Handling Patterns

### Validation Errors

```typescript
// src/middleware/validation.ts
import { Request, Response, NextFunction } from 'express';
import { ValidationError } from '../errors';

export function validateRequest(schema: any) {
  return (req: Request, res: Response, next: NextFunction) => {
    try {
      schema.validate(req.body, { abortEarly: false });
      next();
    } catch (error) {
      const validationErrors = error.details.map((detail: any) => ({
        source: { pointer: `/data/attributes/${detail.path[0]}` },
        code: detail.code.toUpperCase(),
        title: detail.message,
        detail: detail.message
      }));
      
      next(new ValidationError('Validation failed', validationErrors));
    }
  };
}
```

### Global Error Handler

```typescript
// src/middleware/errorHandler.ts
import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';

export function errorHandler(
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction
) {
  const traceId = req.headers['x-request-id'] as string || uuidv4();
  
  // Log error with traceId for debugging
  console.error(`[${traceId}] ${err.name}: ${err.message}`);
  
  // Determine status code
  const status = err['status'] || 500;
  
  // Build error response
  const errorResponse = {
    type: `https://api.example.com/errors/${err.name.toLowerCase()}`,
    title: err.name,
    status,
    detail: err.message,
    instance: req.path,
    traceId,
    ...(err['errors'] && { errors: err['errors'] })
  };
  
  res.status(status).json(errorResponse);
}
```

---

## Build & Development Commands

### Setup

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Build for production
pnpm build

# Run linting
pnpm lint

# Fix linting issues automatically
pnpm lint:fix

# Run type checking
pnpm typecheck

# Run all tests
pnpm test

# Generate OpenAPI documentation
pnpm docs:generate

# Start production server
pnpm start
```

### Monorepo Commands

```bash
# Create new package
pnpm create vite@latest <package-name> -- --template react-ts

# Install package-specific dependency
pnpm install --filter <package-name> <dependency>

# Run command in specific package
pnpm dlx turbo run <command> --filter <package-name>

# Find package location
pnpm dlx turbo run where <package-name>
```

---

## PR & Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Example:**
```
feat(users): add user profile endpoint

- Implement GET /api/v1/users/:id/profile
- Add profile validation middleware
- Include OpenAPI documentation

Closes #123
```

### PR Requirements

- **Title format**: `[<package-name>] <Description>`
- **Run linting**: `pnpm lint` must pass
- **Run tests**: `pnpm test` must pass
- **Update documentation**: OpenAPI specs must reflect changes
- **Add tests**: Include tests for new functionality
- **Check types**: `pnpm typecheck` must pass

---

## Agent-Specific Instructions

### When Modifying Code

1. **Read existing patterns** - Follow established code style in the codebase
2. **Check nearest AGENTS.md** - In monorepos, subproject AGENTS.md takes precedence
3. **Run tests after changes** - Execute relevant test suite before finishing
4. **Fix linting errors** - Address all ESLint and TypeScript errors
5. **Update documentation** - Modify OpenAPI specs if API changes

### When Creating New Endpoints

1. **Define OpenAPI spec first** - Create/modify YAML specification
2. **Implement endpoint** - Follow existing controller patterns
3. **Add validation** - Include input validation middleware
4. **Write tests** - Cover success and error scenarios
5. **Document errors** - List all possible error responses

### When Fixing Bugs

1. **Reproduce the issue** - Write failing test first
2. **Check error logs** - Use traceId to find relevant logs
3. **Fix root cause** - Not just symptoms
4. **Add regression test** - Prevent future occurrences
5. **Verify with existing tests** - Ensure no breakage

### Security Considerations

- **Never commit secrets** - Use environment variables
- **Validate all input** - Server-side validation required
- **Use parameterized queries** - Prevent SQL injection
- **Implement rate limiting** - Protect against abuse
- **Log security events** - Authentication failures, rate limit hits

---

## Large Datasets & Performance

### Optimization Guidelines

- **Paginate large collections** - Break results into manageable chunks
- **Implement caching** - Use ETag and Last-Modified headers
- **Support field selection** - Allow clients to request specific fields
- **Use compression** - Enable gzip/brotli for responses
- **Set appropriate timeouts** - Prevent hanging requests

### Caching Headers

```http
ETag: "33a64df551425fcc55e4d42a148795d9f25f89d4"
Last-Modified: Wed, 21 Oct 2025 07:28:00 GMT
Cache-Control: public, max-age=3600
```

---

## Tools & Resources

### Recommended Tools

- **API Testing**: Postman, Insomnia, httpie
- **Documentation**: Stoplight, Swagger UI, Redoc
- **Linting**: ESLint with TypeScript plugin
- **Formatting**: Prettier
- **Testing**: Vitest, Jest, Supertest
- **Monitoring**: DataDog, New Relic, Prometheus

### Useful Commands

```bash
# Test API endpoint
curl -X GET https://api.example.com/v1/users \
  -H "Authorization: Bearer <token>" \
  -H "Accept: application/json"

# Validate OpenAPI spec
pnpm openapi validate openapi.yaml

# Generate API client from spec
pnpm openapi-generator generate -i openapi.yaml -g typescript-axios -o ./client

# Check API performance
pnpm k6 run load-test.js
```

---

## Continuous Improvement

This AGENTS.md is **living documentation**. Update it when:
- New patterns are established
- Best practices evolve
- Team conventions change
- Security requirements update

**Last Updated**: 2026-03-08  
**Version**: 1.0.0

---

## References

- AGENTS.md format specification
- REST API Best Practices
- OpenAPI Specification 3.1.0/3.2.0
- RFC 7807 Problem Details
- TypeScript ESLint Configuration
- Prettier Configuration
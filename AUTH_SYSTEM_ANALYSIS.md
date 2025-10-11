# Authentication System Analysis

## Current Authentication Setup

### Backend Configuration

#### 1. **API Key Authentication (ACTIVE)**
- **Location**: `src/crypto_news_aggregator/core/auth.py`
- **Header Name**: `X-API-Key`
- **Validation Function**: `get_api_key()`
- **Default Key**: `test-api-key` (from `config.py`)

#### 2. **JWT Authentication (PRESENT BUT NOT USED)**
- **Location**: `src/crypto_news_aggregator/core/security.py`
- **Functions**: `create_access_token()`, `get_current_user()`, etc.
- **Status**: Code exists but is NOT actively used by any endpoints

### Frontend Configuration

#### Environment Files
1. **Production (`.env`)**:
   ```
   VITE_API_URL=https://context-owl-production.up.railway.app
   VITE_API_KEY=b9c5e92b426c96d7fe1573e015b0ca7576de9147497916f2b65690faac8988a8
   ```

2. **Development (`.env.local`)**:
   ```
   VITE_API_URL=http://localhost:8000
   VITE_API_KEY=b9c5e92b426c96d7fe1573e015b0ca7576de9147497916f2b65690faac8988a8
   ```

#### API Client
- **Location**: `context-owl-ui/src/api/client.ts`
- **Header Sent**: `X-API-Key: <api_key>`
- **Implementation**: Lines 48-50
  ```typescript
  if (this.apiKey) {
    headers['X-API-Key'] = this.apiKey;
  }
  ```

### Route Protection

#### API Key Protected Routes (from `api/v1/__init__.py`)
```python
# Line 59-63: API key protected routes
api_key_router = APIRouter()
api_key_router.include_router(price.router, prefix="/price", tags=["price"])
api_key_router.include_router(signals.router, prefix="/signals", tags=["signals"])
api_key_router.include_router(narratives.router, prefix="/narratives", tags=["narratives"])
api_key_router.include_router(entity_alerts.router, prefix="", tags=["entity-alerts"])
```

**Note**: These routers are included WITHOUT explicit dependencies (line 78), meaning they should be **PUBLIC** but the individual endpoints might have dependencies.

#### JWT Protected Routes
```python
# Line 54-57: JWT protected routes
protected_router = APIRouter()
protected_router.include_router(articles.router, prefix="/articles", tags=["articles"])
protected_router.include_router(sources.router, prefix="/sources", tags=["sources"])

# Line 73-75: Applied with JWT dependency
router.include_router(
    protected_router, dependencies=[Depends(security.get_current_active_user)]
)
```

#### Public Routes
- `/health` - Health check
- `/auth/*` - Authentication endpoints
- `/` - Root endpoint

### Key Findings

1. **API Key is Being Sent**: Frontend correctly sends `X-API-Key` header
2. **Backend Expects API Key**: Backend has `get_api_key()` validation function
3. **Route Protection Issue**: The `api_key_router` is included WITHOUT dependencies
   - Line 78: `router.include_router(api_key_router)` - NO dependencies!
   - This means `/signals`, `/narratives`, `/entity-alerts` are **UNPROTECTED**

4. **Inconsistent Protection**:
   - `/price` endpoints explicitly use `Depends(get_api_key)` on each endpoint
   - `/signals`, `/narratives`, `/entity-alerts` routers have NO dependencies
   - Individual endpoints in these routers don't use `Depends(get_api_key)`

### The Problem

**The `api_key_router` is included without any dependencies**, making all these endpoints public:
- `/api/v1/signals/*`
- `/api/v1/narratives/*`
- `/api/v1/entity-alerts/*`

This is why the frontend can access them without authentication!

### Solution Options

#### Option 1: Add API Key Dependency to Router (Recommended)
```python
# In api/v1/__init__.py, line 78
from ...core.auth import get_api_key
from fastapi import Security

router.include_router(
    api_key_router, 
    dependencies=[Security(get_api_key)]
)
```

#### Option 2: Add Dependency to Individual Routers
```python
# In signals.py, narratives.py, entity_alerts.py
from ....core.auth import get_api_key
from fastapi import Security

router = APIRouter(dependencies=[Security(get_api_key)])
```

#### Option 3: Add to Each Endpoint
```python
# On each endpoint
@router.get("/trending")
async def get_trending(api_key: str = Depends(get_api_key)):
    ...
```

### Recommendation

**Use Option 1** - Add the dependency when including the `api_key_router`:
- Centralized control
- Easy to maintain
- Consistent with the pattern used for JWT routes
- Matches the comment on line 58: "API key protected routes (no JWT required)"

Now I have all the context needed. Here is the structured analysis:

---

# MIAS Codebase Analysis for AI Coding Agent Instructions

## 1. Architecture Overview

### System Architecture
- **Monorepo** at `/Users/niranjankarthick/Dev/MIAS-SV-F` with two main projects:
  - `backend/` — Python FastAPI async REST API
  - `mias-client/` — SvelteKit 2 + Svelte 5 frontend (mobile-first PWA)
- **Docker Compose** orchestrates: PostgreSQL 15, Redis 7, Backend (Gunicorn/Uvicorn)
- **Frontend runs locally** via `npm run dev` (Vite dev server on port 5173)
- The app is a **Medical Information Application System** for Saveetha Medical College — manages patients, students, faculty, admissions, prescriptions, vitals, reports, case records, wallets, clinics, and approvals

### Key Ports
| Service  | Internal | External/Host |
|----------|----------|---------------|
| PostgreSQL | 5432   | **5433**      |
| Redis    | 6379     | 6379          |
| Backend  | 8000     | **8001**      |
| Frontend | —        | **5173**      |

API base URL from frontend: `http://localhost:8001/api/v1`

---

## 2. Backend Architecture

### Framework & Stack
- **FastAPI** 0.109 with async throughout
- **SQLAlchemy 2.0** async (asyncpg driver), `declarative_base()`
- **Pydantic v2** (`pydantic==2.5.3`, `pydantic-settings==2.1.0`) for schemas
- **python-jose** for JWT, **passlib+bcrypt** for password hashing
- **slowapi** + Redis for rate limiting (200 req/min)
- **Gunicorn** with 4 Uvicorn workers in production

### App Initialization ([main.py](backend/app/main.py))
- Uses `lifespan` context manager (not deprecated `on_event`)
- Creates tables via `Base.metadata.create_all` on startup
- Starts background `notification_scheduler` task
- Mounts `/uploads` as static files for photos/signatures
- Single router prefix: `/api/v1`
- CORS origins: `['http://localhost:5173', 'http://localhost:5174', 'http://localhost:3000']`

### Database ([database.py](backend/app/database.py))
- Converts `postgresql://` to `postgresql+asyncpg://` automatically
- Connection pool: `pool_size=20`, `max_overflow=30`, `pool_pre_ping=True`, `pool_recycle=300`
- `get_db()` generator: yields `AsyncSession`, auto-commits on success, rollbacks on exception
- `expire_on_commit=False` on session maker

### Configuration ([config.py](backend/app/config.py))
- `pydantic_settings.BaseSettings` with `.env` file support
- Key settings: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` (30), `REFRESH_TOKEN_EXPIRE_DAYS` (7), `CORS_ORIGINS`, `RATE_LIMIT_PER_MINUTE` (200)
- Singleton: `settings = Settings()`

### Authentication & Security ([security.py](backend/app/core/security.py), [deps.py](backend/app/api/deps.py))
- **JWT tokens**: access (30 min) + refresh (7 days), both contain `type` field
- Token payload: `{"sub": user_id, "exp": ..., "type": "access"|"refresh"}`
- **HTTPBearer** scheme (not OAuth2PasswordBearer)
- `get_current_user` dependency: decodes token, fetches User from DB, checks `is_active`
- `require_role(*roles)` dependency factory: returns role checker that depends on `get_current_user`
- Password hashing: bcrypt via passlib

### Error Handling ([exceptions.py](backend/app/core/exceptions.py))
- Custom exceptions extending `HTTPException`: `NotFoundException`, `UnauthorizedException`, `ForbiddenException`, `BadRequestException`
- Each has sensible default messages

### Middleware ([middleware.py](backend/app/core/middleware.py))
- Minimal — only rate limiting via slowapi `Limiter` with Redis storage
- CORS handled by FastAPI built-in middleware

### Model Patterns

**Base pattern** (all models):
- `id = Column(String, primary_key=True)` — UUID strings generated in application code
- `created_at` / `updated_at` with `default=lambda: datetime.utcnow()` and `onupdate=lambda: datetime.utcnow()`
- Enums as `class MyEnum(str, enum.Enum)` + `SQLEnum(MyEnum)` columns
- Relationships use `back_populates`, not `backref`
- String PKs and FKs everywhere (UUIDs as strings)
- Custom indexes with `__table_args__` tuple of `Index()` objects

**User model** ([user.py](backend/app/models/user.py)):
- Four roles: `PATIENT`, `STUDENT`, `FACULTY`, `ADMIN`
- One-to-one relationships to Patient, Student, Faculty via `uselist=False`
- Separate `RefreshToken` model with user FK

**Domain entity ID pattern**: Each domain entity (Patient, Student, Faculty) has:
- `id` — internal UUID PK
- `{entity}_id` — human-readable generated ID (e.g., `PT20260301ABCDEF`, `STU-001`)
- `user_id` — FK to users table (unique, one-to-one)

### Schema Patterns ([schemas/](backend/app/schemas/))
- Pydantic v2 `BaseModel` with `model_config = {"from_attributes": True}` for ORM mode
- Separate schemas for Request vs Response
- Flat schemas — no deep nesting generally
- Optional fields use `Optional[str] = None`
- Enums replicated in schemas as `str, Enum`

### API Route Patterns

**Router setup**: Each module creates `router = APIRouter(prefix="/resource", tags=["Resource"])`

**Common endpoint patterns**:
- `GET /resource/me` — current authenticated user's own resource (uses `require_role()`)
- `GET /resource/{id}` — by ID (uses `get_current_user` for any authenticated user)
- Response is typically **dict literals** built manually in the endpoint, not always Pydantic `response_model`
- Uses `selectinload()` for eager loading relationships
- Pattern: `result = await db.execute(select(Model).where(...))` then `result.scalar_one_or_none()`
- ID generation: `str(uuid.uuid4())` for internal IDs, custom `generate_X_id()` for display IDs

**Registration flow** ([auth.py](backend/app/api/v1/auth.py)):
- Single `POST /auth/register` handles all roles via `RegisterRequest` (discriminated by `role` + optional nested data)
- Creates User + role-specific record in same transaction
- Public endpoints `GET /auth/departments` and `GET /auth/programmes` for registration form dropdowns

**Route registration** ([router.py](backend/app/api/v1/router.py)):
- All routers imported and included in `api_router` without additional prefix (each router defines its own prefix)
- Order: auth, patients, students, faculty, vitals, prescriptions, reports, admissions, wallet, notifications, approvals, autocomplete, admin, clinics

### Seed Script ([seed.py](backend/scripts/seed.py))
- **Drops all tables and recreates** on every run
- Run command: `docker compose exec backend python scripts/seed.py`

**Test Credentials:**
| Role | Username | Password | Name |
|------|----------|----------|------|
| Faculty | d1 | d1 | Dr. Arun Kumar |
| Faculty | d2 | d2 | Dr. Priya Sharma |
| Faculty | d3 | d3 | Dr. Ravi Menon |
| Student | s1–s9 | s1–s9 | Various names |
| Patient | p1–p10 | p1–p10 | Various names |

- Also seeds: Departments, Programmes, Clinics, ClinicAppointments, Admissions, Vitals, Prescriptions, etc.
- Admin user credentials not in seed (likely created separately or added later)

---

## 3. Frontend Architecture

### Framework & Stack
- **SvelteKit 2** with **Svelte 5** (runes: `$state`, `$derived`, `$effect`, `$props`, `$bindable`)
- **TypeScript** (strict mode)
- **Tailwind CSS v4** (via `@tailwindcss/vite` plugin, imported as `@import 'tailwindcss'` in CSS)
- **Axios** for HTTP client
- **lucide-svelte** for icons (ALL icons come from this library)
- **chart.js** for charts
- **No component library** — custom "Aqua" design system components

### Svelte 5 Runes Usage (CRITICAL)
This codebase uses **Svelte 5 runes syntax exclusively** — no `$:` reactive statements, no `export let`, no `{#slot}`:

| Old Svelte 4 | Svelte 5 Used Here |
|---|---|
| `export let prop` | `let { prop } = $props()` |
| `$: derived = ...` | `const derived = $derived(...)` |
| `$: { sideEffect }` | `$effect(() => { ... })` |
| `let x = 0` (reactive) | `let x = $state(0)` |
| `<slot />` | `{@render children()}` with `Snippet` type |
| `bind:value` | Still `bind:value` but `$bindable()` for component props |

**Component props pattern** (see [AquaButton.svelte](mias-client/src/lib/components/ui/AquaButton.svelte)):
```ts
interface Props {
  variant?: 'primary' | 'secondary' | 'danger';
  children: Snippet;
}
let { variant = 'primary', children }: Props = $props();
```

**Snippet rendering**: `{@render children()}` and `{@render header?.()} `

### Routing Structure
- Root layout [+layout.svelte](mias-client/src/routes/+layout.svelte): Sets viewport, wraps in `app-background` with `max-w-md` (mobile-first)
- `(app)/` route group: Protected layout with NavBar + SideMenu, auth check in `onMount`
- `/login` and `/signup` are outside `(app)/` group (no auth required)
- Root `/` redirects to `/dashboard` or `/login` based on auth state

### State Management
- **Svelte writable stores** for auth state ([auth.ts](mias-client/src/lib/stores/auth.ts))
- `authStore` — custom store with `setTokens()` and `logout()` methods
- Derived stores: `isAuthenticated`, `userRole`, `userId`
- Tokens stored in `localStorage` (`accessToken`, `refreshToken`, `userId`, `role`)
- Store values read with `get(authStore)` in component scripts (not `$authStore` — this is used via subscription pattern: `authStore.subscribe(v => authState = v)`)

### API Client ([client.ts](mias-client/src/lib/api/client.ts))
- Axios instance with `baseURL` from `VITE_API_URL` env var (default `http://localhost:8001/api/v1`)
- Request interceptor: attaches `Bearer` token from localStorage
- Response interceptor: auto-refreshes on 401, redirects to `/login` on refresh failure
- `browser` check from `$app/environment` before localStorage access

### API Module Pattern ([students.ts](mias-client/src/lib/api/students.ts), [faculty.ts](mias-client/src/lib/api/faculty.ts), etc.)
- Each module exports a const object with async methods: `export const studentApi = { async getMe() { ... }, ... }`
- Methods return `response.data` directly
- Interface types defined alongside or imported from [types.ts](mias-client/src/lib/api/types.ts)
- RESTful patterns: `client.get('/resource/path')`, `client.post('/resource', data)`

### Page Pattern ([dashboard/+page.svelte](mias-client/src/routes/(app)/dashboard/+page.svelte))
1. Import stores, API modules, components, icons
2. Read auth state with `get(authStore)`
3. Declare `$state()` variables for loading/error/data
4. `onMount(async () => { ... })` for data fetching based on role
5. Role-conditional rendering in template: `{#if role === 'PATIENT'} ... {:else if role === 'STUDENT'} ... {/if}`
6. No SvelteKit `load` functions — all data fetching happens client-side in `onMount`
7. Auto-refresh with `$effect` + `setInterval`

### UI Design System — "Aqua" Skeuomorphic

**Design philosophy**: Mac OS X Aqua-inspired skeuomorphic design with gradients, inset shadows, and glossy effects. NOT flat/modern — intentionally retro.

**Style constants** defined in [aqua.ts](mias-client/src/lib/styles/aqua.ts):
- `appBackground` — striped linen-like pattern
- `primaryButton` — blue gradient `#4d90fe → #0066cc`
- `card` — white with multi-layer box-shadow
- `cardHeader` — gradient `#f8f9fb → #d9e1ea`
- `navBar` — gradient `#d1dbed → #b8c6df`
- Inline `style=` attributes used heavily (not just Tailwind classes)

**Component library** (all in `$lib/components/ui/`):
| Component | Key Props | Purpose |
|-----------|-----------|---------|
| `AquaButton` | `variant`, `size`, `fullWidth`, `loading`, `children: Snippet` | Gradient buttons |
| `AquaCard` | `padding`, `class`, `header: Snippet`, `children: Snippet` | Card containers |
| `AquaInput` | (standard input) | Styled inputs |
| `AquaModal` | `open`, `title`, `onclose`, `header: Snippet`, `children: Snippet` | Bottom sheet modals |
| `Avatar` | `name`, `size` | User avatars |
| `StatusBadge` | — | Status indicators |
| `TabBar` | — | Tab navigation |
| `Autocomplete` | — | Search autocomplete |

**Styling approach**:
- **Tailwind CSS** for layout, spacing, typography (`class="flex items-center gap-2 px-4"`)
- **Inline `style=`** for Aqua gradients, shadows, borders (skeuomorphic effects)
- Both are used together in the same element
- Global CSS in [layout.css](mias-client/src/routes/layout.css): imports Tailwind, defines `.app-background`
- Animations in [animations.css](mias-client/src/lib/styles/animations.css)

**Icon library**: `lucide-svelte` exclusively. Icons imported individually:
```ts
import { HeartPulse, FileText, Pill } from 'lucide-svelte';
```
Used as components: `<HeartPulse class="w-5 h-5" />`

### Layout Components
- **NavBar** ([NavBar.svelte](mias-client/src/lib/components/layout/NavBar.svelte)): Sticky top bar, blue gradient, back button, notification bell with badge, menu button
- **SideMenu** ([SideMenu.svelte](mias-client/src/lib/components/layout/SideMenu.svelte)): Right-side slide-out panel with role-based menu items, logout button

---

## 4. Role System

### Four Roles: PATIENT, STUDENT, FACULTY, ADMIN

**Backend enforcement**:
- `require_role(UserRole.PATIENT)` — dependency injection for role-restricted endpoints
- `get_current_user` — any authenticated user
- Some endpoints check role in logic (e.g., admission actions only for FACULTY/ADMIN)

**Frontend routing by role** (from SideMenu):

| Route | PATIENT | STUDENT | FACULTY | ADMIN |
|-------|---------|---------|---------|-------|
| `/dashboard` | ✓ | ✓ | ✓ | — |
| `/admin` | — | — | — | ✓ (dashboard) |
| `/profile` | ✓ | ✓ | ✓ | — |
| `/records` | ✓ | — | — | — |
| `/admissions` | ✓ | ✓ | ✓ | — |
| `/prescriptions` | ✓ | — | — | — |
| `/vitals` | ✓ | — | — | — |
| `/reports` | ✓ | — | — | — |
| `/wallet/*` | ✓ | — | — | — |
| `/patients` | — | ✓ | — | — |
| `/case-records` | — | ✓ | — | — |
| `/clinic-sessions` | ✓ | ✓ | ✓ | ✓ |
| `/approvals` | — | — | ✓ | — |
| `/students` | — | — | ✓ | — |
| `/notifications` | ✓ | ✓ | ✓ | — |
| `/admin/users` | — | — | — | ✓ |
| `/admin/departments` | — | — | — | ✓ |
| `/admin/analytics` | — | — | — | ✓ |

**Dashboard is role-polymorphic**: Single `/dashboard` page renders completely different content based on role using `{#if role === 'PATIENT'} ... {:else if role === 'STUDENT'} ... {:else if role === 'FACULTY'} ... {/if}`

---

## 5. Key Patterns — How to Add New Features

### Adding a New Backend Endpoint
1. Create/edit file in `backend/app/api/v1/` (e.g., `new_feature.py`)
2. Define `router = APIRouter(prefix="/new-feature", tags=["New Feature"])`
3. Add async endpoint functions with `Depends(get_db)` and `Depends(require_role(...))` or `Depends(get_current_user)`
4. Register in [router.py](backend/app/api/v1/router.py): `from app.api.v1 import new_feature` + `api_router.include_router(new_feature.router)`

### Adding a New Model
1. Create file in `backend/app/models/` (e.g., `new_model.py`)
2. Extend `Base` from `app.database`
3. Use String PKs, UUID generation in application code
4. Import in [models/__init__.py](backend/app/models/__init__.py)
5. Create corresponding Pydantic schemas in `backend/app/schemas/`
6. Tables auto-created on startup via `create_all`

### Adding a New Frontend Page
1. Create `mias-client/src/routes/(app)/new-page/+page.svelte`
2. Use Svelte 5 runes: `$state()`, `$derived()`, `$props()`, `$effect()`
3. Fetch data in `onMount` using API modules
4. Use Aqua components (`AquaCard`, `AquaButton`, `AquaModal`)
5. All icons from `lucide-svelte`
6. Style with Tailwind classes + inline `style=` for gradients/shadows
7. Add menu entry in [SideMenu.svelte](mias-client/src/lib/components/layout/SideMenu.svelte) for the appropriate role

### Adding a New API Module (Frontend)
1. Create `mias-client/src/lib/api/new_feature.ts`
2. Import `client` from `./client`
3. Export interface types and a const API object: `export const newFeatureApi = { async getAll() { ... } }`

---

## 6. Build/Dev Workflow

### Start Everything
```bash
# Start backend + DB + Redis
docker compose up -d --build backend

# Seed database (drops all data first!)
docker compose exec backend python scripts/seed.py

# Start frontend dev server
cd mias-client && npm run dev
```

### Rebuild Backend Only
```bash
docker compose up -d --build backend
```

### View Backend Logs
```bash
docker compose logs -f backend
```

### Frontend Commands
```bash
npm run dev          # Dev server on :5173
npm run build        # Production build
npm run check        # TypeScript + Svelte type checking
npm run lint         # Prettier + ESLint
```

### Docker Compose Services
- `db` — PostgreSQL 15 Alpine with tuned config (200 max_connections, 256MB shared_buffers)
- `redis` — Redis 7 Alpine with AOF persistence, 128MB max memory
- `backend` — Python 3.11-slim, Gunicorn with 4 Uvicorn workers, resource limits (2 CPU, 1GB RAM)
- Volumes: `pgdata`, `redisdata`, `uploads_data`

---

## 7. Critical Quirks & Non-Obvious Details

1. **No SvelteKit `load` functions**: All data fetching is client-side in `onMount`. No SSR data loading. The app is essentially a client-side SPA wrapped in SvelteKit.

2. **Mobile-first layout**: Root layout constrains to `max-w-md` (448px). This is a mobile app, not desktop.

3. **Auth check is client-side only**: The `(app)/+layout.svelte` does `onMount` auth check and `goto('/login')`. No server-side guards.

4. **Store subscription pattern**: Uses `get(authStore)` in script, and `authStore.subscribe(v => authState = v)` to make it reactive — NOT `$authStore` syntax.

5. **Inline styles for Aqua**: Skeuomorphic gradients/shadows are inline `style=` attributes, not Tailwind classes. Both are used on the same elements.

6. **UUIDs as strings**: All primary keys are `Column(String)` with `str(uuid.uuid4())` — not database-native UUID type.

7. **DB auto-commit in `get_db()`**: The session commits automatically after the endpoint returns. No explicit `.commit()` needed in most endpoints (though some do call it for mid-transaction commits like updating `last_login`).

8. **Tailwind v4 import syntax**: Uses `@import 'tailwindcss'` and `@plugin '@tailwindcss/forms'` in CSS (v4 syntax), NOT the v3 `@tailwind base; @tailwind components; @tailwind utilities` directives.

9. **Event handlers use lowercase**: Svelte 5 uses `onclick`, `onclose`, `onkeydown` (not `on:click`).

10. **Snippets instead of slots**: All child content uses `children: Snippet` prop type and `{@render children()}`.

11. **`$page` replaced by `page` from `$app/state`**: Uses `import { page } from '$app/state'` and `page.url.pathname`, not `$page`.

12. **`response_model` used selectively**: Some endpoints return Pydantic models, many return raw dicts. Patient endpoints use schemas, others build dict literals.

13. **Seed drops all tables**: Running seed script is destructive — `Base.metadata.drop_all` then `create_all`.

14. **Admin role**: ADMIN users are redirected from `/dashboard` to `/admin`.

15. **Token refresh loop protection**: Client interceptor uses `_retry` flag to prevent infinite refresh loops.

16. **Component event naming**: Uses `onclose` (lowercase, no colon) for callbacks, following Svelte 5 conventions.

17. **`$bindable()` for two-way binding**: SideMenu uses `open = $bindable(false)` for the `bind:open` pattern.

---

## 8. File Naming Conventions

### Backend
- **Models**: singular snake_case (`patient.py`, `medical_record.py`, `case_record.py`)
- **API routes**: plural snake_case (`patients.py`, `students.py`, `clinic_sessions` would be `clinics.py`)
- **Schemas**: singular snake_case matching model (`patient.py`, `auth.py`)
- **Variables/functions**: snake_case
- **Classes**: PascalCase
- **Enums**: UPPER_CASE values in PascalCase class

### Frontend
- **API modules**: plural kebab-less (`students.ts`, `patients.ts`, `auth.ts`)
- **Components**: PascalCase (`AquaButton.svelte`, `SideMenu.svelte`)
- **Routes**: kebab-case folders (`case-records/`, `clinic-sessions/`)
- **Stores**: camelCase (`auth.ts`)
- **Types/interfaces**: PascalCase
- **API object names**: camelCase (`patientApi`, `studentApi`, `facultyApi`)
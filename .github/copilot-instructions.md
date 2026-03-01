# MIAS — AI Coding Agent Instructions

Medical Information & Administration System for Saveetha Medical College. Monorepo: `backend/` (FastAPI) + `mias-client/` (SvelteKit 5). Mobile-first app (max-width 448px).

## Architecture

- **Backend**: FastAPI + SQLAlchemy 2.0 async (asyncpg) + PostgreSQL 15 + Redis 7, all Dockerized
- **Frontend**: SvelteKit 2 + Svelte 5 runes + TypeScript + Tailwind CSS v4, runs locally via Vite
- **Auth**: JWT (access 30min / refresh 7d) with `HTTPBearer`, stored in localStorage
- **Roles**: `PATIENT`, `STUDENT`, `FACULTY`, `ADMIN` — enforced via `require_role()` dependency and client-side route guards
- **No SSR**: All data fetching is client-side in `onMount`. No SvelteKit `load` functions.

| Service | Port | URL |
|---------|------|-----|
| Backend | 8001 | `http://localhost:8001/api/v1` |
| Frontend | 5173 | `http://localhost:5173` |
| PostgreSQL | 5433 | — |

## Dev Workflow

```bash
docker compose up -d --build backend          # Build & start backend
docker compose exec backend python scripts/seed.py  # Seed DB (DESTRUCTIVE — drops all tables)
cd mias-client && npm run dev                 # Frontend dev server
npm run check                                 # TypeScript + Svelte type checking
```

**Seed credentials**: `d1/d1`–`d3/d3` (faculty), `s1/s1`–`s9/s9` (students), `p1/p1`–`p10/p10` (patients), `admin/admin`

## Svelte 5 Runes (CRITICAL)

This codebase uses Svelte 5 exclusively. Never use Svelte 4 syntax.

```svelte
<!-- Props: use $props(), not `export let` -->
let { variant = 'primary', children }: Props = $props();

<!-- State: use $state(), not bare `let` -->
let items = $state([]);

<!-- Derived: use $derived() for expressions, $derived.by() for blocks -->
const count = $derived(items.length);
const filtered = $derived.by(() => { let f = items; /* logic */ return f; });

<!-- Children: use Snippet + {@render}, not <slot> -->
interface Props { children: Snippet; }
{@render children()}

<!-- Events: lowercase without colon -->
<button onclick={handler}>    <!-- NOT on:click -->
<AquaModal onclose={close}>   <!-- NOT on:close -->

<!-- Two-way binding on components -->
let open = $bindable(false);  <!-- for bind:open from parent -->
```

## Backend Patterns

**Adding an endpoint** in `backend/app/api/v1/`:
```python
router = APIRouter(prefix="/resource", tags=["Resource"])

@router.get("/{id}")
async def get_item(id: str, db: AsyncSession = Depends(get_db), user = Depends(require_role(UserRole.FACULTY))):
    result = await db.execute(select(Model).options(selectinload(Model.relation)).where(Model.id == id))
    item = result.scalar_one_or_none()
    if not item:
        raise NotFoundException("Item not found")
    return {"id": item.id, "name": item.name}  # Dict literals common, not always response_model
```
Register in `api/v1/router.py`: `api_router.include_router(module.router)`

**Models**: String UUIDs (`id = Column(String, primary_key=True)`), generated via `str(uuid.uuid4())`. Each entity has `id` (internal) + `entity_id` (display, e.g. `PAT-003`). Relationships use `back_populates`. DB auto-commits via `get_db()`.

## Frontend Patterns

**Page structure** — every page in `routes/(app)/`:
1. Read auth via `get(authStore)`, declare `$state()` variables
2. Fetch data in `onMount` based on role
3. Role-conditional rendering: `{#if role === 'PATIENT'} ... {:else if role === 'STUDENT'} ... {/if}`
4. After mutations, always re-fetch data (e.g., `items = await api.getAll(id)`)

**API modules** in `lib/api/`: export const objects with async methods returning `response.data`:
```ts
export const featureApi = {
  async getAll(id: string) { return (await client.get(`/feature/${id}`)).data; },
  async create(id: string, data: any) { return (await client.post(`/feature/${id}`, data)).data; },
};
```

**UI**: "Aqua" skeuomorphic design — Tailwind for layout + inline `style=` for gradients/shadows:
```svelte
<div class="flex items-center gap-2 px-4 py-3 rounded-xl"
     style="background: linear-gradient(to bottom, #3b82f6, #2563eb); box-shadow: 0 1px 3px rgba(0,0,0,0.3);">
```
Components: `AquaButton` (variant/size/loading/fullWidth), `AquaCard` (padding/header snippet), `AquaModal` (title/onclose), `StatusBadge`, `TabBar`, `Avatar`. Icons: `lucide-svelte` only.

**SideMenu** (`lib/components/layout/SideMenu.svelte`): Add new routes per role in the appropriate `*MenuItems` array.

## Naming Conventions

| Layer | Convention | Example |
|-------|-----------|---------|
| Backend models | singular snake_case | `patient.py`, `case_record.py` |
| Backend routes | plural snake_case | `patients.py`, `admissions.py` |
| Frontend API | camelCase objects | `studentApi`, `facultyApi` |
| Frontend routes | kebab-case dirs | `case-records/`, `clinic-sessions/` |
| Components | PascalCase | `AquaButton.svelte` |
| Enums (Python) | `class Name(str, enum.Enum)` | `UserRole.FACULTY` |

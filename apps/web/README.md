# ServiceMind Web

React + TypeScript frontend for the ServiceMind Agents console.

## Current scope

- Vite application baseline.
- ServiceMind console shell with sidebar navigation.
- `/health` integration against the FastAPI backend.

Business pages are placeholders in this phase.

## Commands

```powershell
cd G:\ServiceMind_Agents
pnpm install
pnpm --dir apps/web dev
pnpm --dir apps/web preview
pnpm --dir apps/web typecheck
pnpm --dir apps/web lint
pnpm --dir apps/web build
```

## Environment

```text
VITE_API_BASE_URL=http://localhost:8000
```

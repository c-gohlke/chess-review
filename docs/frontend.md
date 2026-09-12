# Frontend

TypeScript, one Vite project under `frontend/`.

## Tools

| Tool | Role |
|------|------|
| Vite | Dev server and build. |
| React | UI. |
| react-chessboard | Board rendering with mouse and touch drag. |
| chess.js | Client-side move legality so the board responds without a round trip. |
| Tailwind CSS | Styling. Utility classes only, no component library. |
| openapi-typescript | Generates API types from the backend's OpenAPI schema. |

## Structure

```
frontend/src/
  api/          generated types plus a thin fetch wrapper
  board/        chessboard component and move handling
  pages/        one component per screen: import, review, patterns, puzzles
  components/   shared UI, kept small
```

## Data fetching

Plain `fetch` through the generated types. Each page loads what it needs on mount and holds it in
component state. No data-fetching library; revisit only if caching or background refetching
becomes a real problem. The dev server proxies `/api` to the backend on port 8000.
Run `npm run generate-api` to regenerate the types from the backend's OpenAPI schema;
`openapi.json` and `src/api/schema.d.ts` are committed.

## Styling

Tailwind utilities directly in JSX. Shared visual decisions live in `tailwind.config` (colours,
spacing), not in wrapper components. Layout is mobile-first: default styles target phones and
`md:` breakpoints widen for desktop.

## Mobile

The app is responsive rather than native. The board must be usable by touch, which
react-chessboard handles. Nothing else is mobile-specific.

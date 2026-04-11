# Next.js Dev Asset Corruption Note

Date: 2026-04-10

## Symptom

Local `next dev` on `http://localhost:3000` can make the landing page look broken even though the deployed site and local production build are fine.

Observed behavior:

- The left side of the homepage still renders.
- The right-side hero stack collapses into a plain vertical text list.
- Large parts of the page lose class-based styling.
- Interactive behavior is only partially hydrated.

This can look like a landing-page code regression, but it is not.

## Root Cause

The local Next dev server can end up with a corrupted `.next` asset graph.

Concrete failure seen in logs:

```text
Error: Cannot find module './948.js'
Require stack:
- frontend/.next/server/webpack-runtime.js
```

When this happens, critical frontend assets start returning `500`, including:

- `/_next/static/css/app/layout.css`
- `/_next/static/chunks/app/layout.js`
- `/_next/static/chunks/main-app.js`
- `/_next/static/chunks/app/page.js`
- `/_next/static/chunks/app-pages-internals.js`
- `/_next/static/chunks/webpack.js`

Because the server-rendered HTML still arrives, the page can appear "half correct" and mislead debugging toward CSS or component code.

## Why The Hero Looked Wrong

The homepage mixes:

- inline styles that still render from server HTML
- class-based styled-jsx rules that depend on the frontend assets loading correctly

When the dev assets fail:

- `.iso-scene`, `.iso-cube`, `.slab`, `.s-front`, `.s-side`, and `.s-cap` lose their generated CSS
- the hero falls back to unstyled DOM layout
- the labels appear as a plain stacked list

## Verification Pattern

Healthy local production and deployed behavior:

- `cubeTransformStyle = preserve-3d`
- `scenePerspective = 1800px`
- `labelPosition = absolute`

Broken local dev behavior:

- `cubeTransformStyle = flat`
- `scenePerspective = none`
- `labelPosition = static`

## Fix

Kill the broken `next dev` process, clear the dev cache, and restart.

```bash
pkill -f "next dev" || true
rm -rf frontend/.next
cd frontend && npm run dev
```

After restart, verify that the broken asset responses are gone and reload the page.

## Practical Rule

If localhost looks broken but deployed and `next start` look fine, check dev-asset integrity before changing homepage code.

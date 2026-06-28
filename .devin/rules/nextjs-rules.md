---
trigger: glob
globs: "**/*.tsx,**/*.ts,**/next.config.*,**/app/**,**/pages/**"
---

# Next.js Development Rules

Invoke the `next-best-practices` skill when working on any Next.js file.

- Default to React Server Components (RSC); add `'use client'` only when needed (hooks, events, browser APIs)
- Never `async` a Client Component — async data fetching only in Server Components or Route Handlers
- Use `next/image` instead of `<img>`, always set `width`/`height` or `fill` + `sizes`
- Use `next/font` instead of `<link>` for fonts
- Params and `searchParams` in Next.js 15+ are async — always `await` them
- Wrap `useSearchParams` / `usePathname` in `<Suspense>` to avoid CSR bailout
- Prefer Server Actions over Route Handlers for form mutations
- Use `Promise.all` or `preload` pattern to avoid data waterfalls
- Cache: invoke `next-cache-components` skill when using `use cache`, `cacheLife`, or `cacheTag`

---
trigger: model_decision
description: "Invoke when user asks to upgrade Next.js version, migrate to a new Next.js major, or run next upgrade codemods"
---

# Next.js Upgrade Rules

Invoke the `next-upgrade` skill for any Next.js version migration task.

- Always check current version in `package.json` before upgrading
- Run official codemods before manual changes
- Test async params/searchParams, cookies, headers after upgrading to 15+
- Verify `middleware.ts` rename if upgrading to 16+

## Planning Task Workflow

Use this workflow when planning any new feature or technical task.

Follow steps in order.
Do not skip steps.
Do not produce implementation code during planning phase.

---

### Pre-Step — Scan Relevant Rules, Skills, and Agents

Before starting Step 1, scan the workspace for files that may improve planning quality.

Search for:

- `.windsurf/rules/*.md` — project-specific coding rules and constraints
- `.windsurf/skills/*.md` and `.agents/skills/**/*.md` — available agent skills relevant to the task domain
- `.windsurf/workflows/*.md` — other workflows that may overlap or be referenced
- any `AGENTS.md`, `CLAUDE.md`, or similar agent instruction files at root or in subdirectories

For each relevant file found:

- read its content
- note any rules, constraints, or patterns that apply to this task
- incorporate them into planning decisions throughout Steps 1–8

Do not skip this pre-step. Planning quality depends on awareness of existing rules and available skills.

---

### Step 1 — Clarify Scope

First, ask the user:

> Is this a **new project from scratch**, or a **new feature added to an existing codebase**?

This answer affects how subsequent steps are executed:

- **New project** — propose tech stack freely, no existing modules to inspect, architecture starts from zero
- **Existing codebase** — inspect current dependencies and modules first, constrain proposals to existing stack unless justified

Wait for the user's answer before continuing.

Then confirm:

- what the task is trying to achieve
- who is affected (user roles, systems, integrations)
- what is explicitly out of scope
- known constraints (existing tech stack, system boundaries)

Before asking the user to confirm constraints, inspect the project first and propose specific constraint candidates:

- read existing dependency files (package.json, requirements.txt, pyproject.toml, etc.)
- identify frameworks, libraries, and runtime versions already in use
- note any architectural boundaries visible in the codebase (monorepo, microservices, shared modules)
- propose a constraints list based on findings, e.g.:
  - language/runtime: Python 3.11, Node 20
  - frameworks: Django 4.2, React 18, Next.js 14
  - infra: PostgreSQL, Redis, Celery
  - boundaries: no new state library, no new third-party auth provider

Then ask the user to confirm, correct, or extend the proposed constraints.

Ask the user to confirm scope explicitly.

Do not assume. Do not proceed without confirmed scope.

Example confirmed scope:

- feature: notification system
- affected: all logged-in users
- out of scope: push notifications, mobile
- constraints: existing Django + React stack, no new state library

---

### Step 2 — Define Functional Requirements

Based on the confirmed scope, propose a draft list of functional requirements.

For each proposed requirement:

- describe user-facing behavior
- describe system behavior
- define acceptance criteria
- label as must-have or nice-to-have

Present the draft list to the user. Ask:

- are these requirements correct?
- are any missing?
- should any be removed or changed?
- are any must-have items actually nice-to-have or vice versa?

Wait for user confirmation before finalizing the requirements list.

Do not combine requirements and implementation.

---

### Step 3 — Identify Edge Cases

For every confirmed requirement, propose a list of likely edge cases.

Cover at minimum:

- empty states
- boundary inputs (empty, max length, zero, negative)
- concurrent operations
- network / system failures (timeout, 500, auth expiry)
- permission edge cases (unauthorized, role mismatch)
- data integrity (cascades, orphaned records)

For each edge case, define:

- how it should be handled
- what error message or response is shown to the user (must be explicit, not silent)
- what HTTP status code or system state results (if applicable)

Do not leave any edge case with an undefined or silent failure. Every error must have a clear, user-facing message.

Present the proposed edge cases to the user. Ask:

- are these edge cases correct and relevant?
- are any missing?
- how should each be handled — any specific business rules?
- are the proposed error messages appropriate and clear enough for the user?

Wait for user confirmation before finalizing edge case handling.

Do not skip this step.

---

### Step 4 — Confirm Tech Stack

Inspect existing project dependencies and propose a tech stack based on findings.

For each proposed technology:

- state what it is
- state why it was chosen or already in use
- state alternatives considered and why they were rejected

If new technology is needed, flag it explicitly and explain why the existing stack is insufficient.

Present the proposed stack to the user. Ask:

- does this stack match your expectations?
- are there any technologies you want to add or swap?
- are there any constraints not yet captured?

Wait for user confirmation before finalizing the tech stack.

Do not introduce dependencies without justification.

---

### Step 5 — Define Optimization Strategy

Based on the confirmed requirements and tech stack, propose an optimization strategy.

Propose specific approaches for:

- read/write patterns (what gets queried most and how often)
- indexing needs (which fields, which models)
- caching opportunities (Redis, CDN, query cache — with specific targets)
- async / background job needs (Celery, queues — with specific triggers)
- pagination and lazy loading strategy
- N+1 query prevention approach

Present the proposed strategy to the user. Ask:

- does this strategy fit the expected scale and usage patterns?
- are any optimizations unnecessary for this scope?
- are there any missing performance concerns?

Wait for user confirmation before finalizing the optimization strategy.

---

### Step 6 — Define Architecture & Module Breakdown

Based on confirmed requirements and tech stack, propose a module breakdown.

Propose for Backend:

- affected existing modules
- new apps / files to create
- data model changes (new models, new fields, migrations)
- API contract: endpoints, HTTP methods, payload, response shape

Propose for Frontend:

- affected existing components / services
- new services, hooks, components to create
- state management approach
- shared components to reuse

Present the proposed architecture to the user. Ask:

- does this module breakdown look correct?
- are there existing modules or components that should be reused instead of created new?
- are any proposed endpoints or models missing or incorrect?
- any concerns about the integration points?

Wait for user confirmation before finalizing the architecture.

Keep modules isolated.
Follow existing domain ownership.
Do not merge unrelated concerns.

---

### Step 7 — Define Implementation Order

Based on the confirmed architecture, propose a sequenced implementation plan.

Rules when sequencing:

- foundation before features
- backend API contract before frontend integration
- shared / reusable pieces before specific implementations
- define done criteria for each step

Propose a numbered order, for example:

1. data model + migration
2. API endpoints (stub)
3. serializers + basic validation
4. business logic
5. background jobs (if any)
6. frontend service layer
7. frontend components
8. integration tests
9. validation phase

Present the proposed order to the user. Ask:

- does this sequence make sense for your team and delivery timeline?
- are any steps missing?
- should any steps be merged, split, or reordered?
- are there external dependencies that affect the order?

Wait for user confirmation before finalizing the implementation order.

Complete each step before moving to next.
Do not partially implement multiple steps simultaneously.

---

### Step 8 — Validation Checklist

Propose a validation checklist based on the confirmed requirements and architecture.

Propose for Backend:

- endpoints return correct responses
- permissions enforced correctly
- edge cases return correct status codes
- no N+1 queries
- migrations apply cleanly

Propose for Frontend:

- API calls succeed and handle errors
- empty states render correctly
- loading and error states handled
- shared components reused where applicable
- no hardcoded values

Propose for General:

- no console errors
- existing tests pass
- behavior of related features preserved
- all error states have explicit, user-facing messages (no silent failures)
- error messages are specific enough for the user to understand what went wrong and what to do next

Present the proposed checklist to the user. Ask:

- are all validation criteria correct and relevant?
- are any criteria missing for this specific feature?
- are there any manual QA steps or stakeholder sign-offs required?

Wait for user confirmation before finalizing the checklist.

---

### Step 9 — Output Plan Document

Once all steps (1–8) are confirmed by the user, generate a structured plan document.

Create a file named `plan.md` in the project root (or a `docs/` or `.windsurf/` folder if one exists and is more appropriate).

The plan document must include:

```
# Plan: [Feature Name]

## Scope
[confirmed scope from Step 1]

## Functional Requirements
[confirmed requirements from Step 2]

## Edge Cases
[confirmed edge cases and handling from Step 3]

## Tech Stack
[confirmed stack from Step 4]

## Optimization Strategy
[confirmed strategy from Step 5]

## Architecture & Module Breakdown
[confirmed architecture from Step 6]

## Implementation Order
[confirmed sequence from Step 7]

## Validation Checklist
[confirmed checklist from Step 8]
```

After creating the file, tell the user the file path and ask:

- does the plan document look complete and correct?
- should it be placed in a different location?

Do not begin implementation until the user explicitly approves the plan document.

---

## Rules During Planning

Always:

- confirm scope before producing output
- cover all steps including pre-step and Steps 1–9
- identify risks and open questions explicitly
- follow existing tech stack
- flag ambiguities rather than resolving silently

Never:

- produce implementation code during planning phase
- skip edge case analysis
- assume happy path only
- propose technologies not already in project without justification
- produce partial plans

---

## Expected Agent Behavior

Act as a technical lead doing pre-implementation planning.

Prioritize:

1. scope clarity
2. requirement completeness
3. edge case coverage
4. technology fit with existing system
5. incremental implementation order

Do not behave like:

- a code generator
- a tutorial writer
- a one-shot solution provider

Produce a structured plan that another developer or agent can execute without ambiguity.

Output a `plan.md` file only after all steps are confirmed by the user.

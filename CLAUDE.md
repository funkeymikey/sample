# CLAUDE.md

## Python Code Conventions

- Imports must follow some sorting conventions (config in pyproject.toml) — correct ordering and grouping, not just line length
- Imports used across multiple functions go at the top of the file; imports used in only one function go inside that function
- Use type annotations when possible
- Use built-in types for annotations instead of `typing` equivalents — `list[str]` not `List[str]`, `dict[str, int]` not `Dict[str, int]`, `X | None` not `Optional[X]`, `X | Y` not `Union[X, Y]`
- Instead of using strings, always use enum values when an enum exists
- Use `LOGGER.exception` instead of `LOGGER.error` when logging inside an `except` block — it automatically includes the traceback
- Use descriptive variable names — avoid abbreviations like `eu`, `ur`, `sub`, `msg`, `qs`. Prefer `event_user`, `user_role`, `subevent`, `message`, `event_qs`. Single-letter variables in comprehensions (`u`, `x`) are acceptable.
- Always use f-strings for string formatting and interpolation — never use `%` formatting, `.format()`, or `+` concatenation
- When writing tests, find an appropriate balance between multiple assertions in a single test (faster execution) and pure atomic design with each assertion being a single test (slower execution)
- For well defined changes, write tests first, ensure they fail, and then implement the change to make them pass
- When changing the behaviour of a function or method, update its docstring to reflect the new behaviour; add a docstring if one is missing

## Django / DRF Patterns

Requests flow view → service → serializer:

- **Views are thin:** validate input with a serializer, call a service, and wrap the result in `Response(...)`. No business logic, and no `try`/`except` to build error responses
- **Services hold the business logic** in `<app>/services.py`: plain functions that know nothing about HTTP. They return plain values or model instances, and raise `core.exceptions` errors for rule violations (`ApiError` for a 400, `ConflictError` for a 409)
- **Serializers shape data** in and out; field-level validation lives there
- **Tests live with their app** in `<app>/tests/` (a package with `__init__.py`), named `test_*.py`
- **Don't catch unexpected errors:** let them propagate to `core.exceptions.api_exception_handler`, which logs them and returns the standard `{"error": {...}}` 500. All error responses come from the handler
- **API docs:** `core.schema.ApiAutoSchema` adds the standard error responses automatically (500 everywhere, 400 on writes, 404 on single-object paths); use `@extend_schema` only for success responses and unusual codes (e.g. a 409)
- After changing an endpoint, serializer or enum, run `make api-types` so the frontend types stay in sync

## TypeScript / Vue Code Conventions

- Components use `<script setup lang="ts">` and the Composition API; no Options API
- API types come from the generated schema (`components['schemas'][...]` via `@/api/client`); never hand-write a type for something the API returns — run `make api-types` after backend changes
- All API calls go through `@/api/client`; components never call `fetch` directly
- Never use `any`; use `unknown` plus a type guard for data of unknown shape (e.g. parsed JSON)
- Use string-literal union types (including the generated enum unions) instead of TypeScript `enum`, and never compare against a bare string when a union type exists
- Type component props and emits with `defineProps<{...}>()` / `defineEmits<{...}>()`
- Keep state local to a component; use a Pinia store only for state shared across views
- Use `async`/`await`, not `.then()` chains; catch `ApiError` and use its `errorResponse` to show the API's message
- Import app code through the `@/` alias, not relative `../../` paths; group imports as packages, then a blank line, then `@/` imports
- Use descriptive names, same as Python: `accountBalance`, not `bal`; components in PascalCase (`AccountList.vue`), composables as `useX`
- Add a JSDoc comment to exported functions; update it when behaviour changes
- Tests sit next to the file they test, named `<file>.spec.ts` (e.g. `App.spec.ts` beside `App.vue`)
- In tests, select elements by `data-test` attributes, not CSS classes or text, and mock `fetch` with real `Response` objects
- For well-defined changes, write tests first, ensure they fail, then implement (same as Python)

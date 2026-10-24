---
name: add-api-endpoint
description: Add or change a FastAPI route end to end - pydantic schemas, security dependencies, tests, the exported OpenAPI schema and the generated TypeScript client the React app uses.
---

# Add or change an API endpoint

The React app never writes API types by hand: they are generated from the OpenAPI schema, and CI fails
if `frontend/openapi.json` or `frontend/src/client/` is out of date.

## Steps
1. **Test first** in `tests/test_api.py` with FastAPI's TestClient: the happy path, a validation error
   (422), and the security cases that apply (401 without login, 403 from another origin, 429 over the
   limit, 404 for another office's ticket). AI calls are faked with `tests/fakes.py`.
2. **Schemas:** pydantic models for the body and the response with `Field` limits (lengths, ranges).
   Never return a database row or a model object directly: return a response model, so nothing leaks.
3. **Route:** a short function; the work lives in a module (`store.py`, `pipeline.py`...).
   - Public routes that cost money or touch the database get a rate-limit dependency.
   - Staff routes take `staff_member: CurrentStaff` and check the office with `visible()`.
   - Changing routes (POST, PATCH, DELETE) on cookie auth sit behind `same_origin` (CSRF).
   - Log the event with ids and codes only: never student text or e-mail addresses.
4. **Regenerate:** `make api-client` (exports `frontend/openapi.json`, then `npm run generate`).
5. **Use it in the frontend** through the generated TanStack Query hooks in `src/client/`.
6. Run the `quality-gate` skill. Add a Playwright test if the user can see the change.
7. changelog entry; ADR if the endpoint changes a security or privacy rule.

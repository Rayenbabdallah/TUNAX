# TUNAX Insomnia Testing Scenario

Use this scenario to validate the complete public and authenticated API surface in a single Insomnia workspace. Each step assumes the shared collection located at `tests/insomnia_collection.json`.

## 1. Preparation
1. Start the stack: `docker compose -f docker/docker-compose.yml up -d`.
2. Import `tests/insomnia_collection.json` into Insomnia (Workspace → Import → From File).
3. Select the `Development` environment and confirm the `base_url` resolves to `http://localhost:5000`.

## 2. Public Baseline
1. **Health Check** – Send `GET {{ base_url }}/health` to ensure the backend container is ready.
2. **Swagger UI** – Open `GET {{ base_url }}/api/v1/docs/swagger-ui` in the browser tab that Insomnia provides; verify the OpenAPI spec renders.
3. **List Communes** – Execute `GET /api/public/communes` and note the `id` for Tunis (e.g., `1` or `7101` depending on seed data).
4. **List Delegations** – Run `GET /api/public/delegations?commune_id={id}`. Confirm at least one delegation returns.
5. **List Localities** – Trigger `GET /api/public/localities?commune_id={id}&delegation=Tunis`. Expect a non-empty array (post bug fix it should contain 200+ entries for Tunis).
6. **Document Requirements** – Send `GET /api/public/document-requirements?declaration_type=property&commune_id={id}` to validate municipal guidance.
7. **Tax Rates** – Call `GET /api/public/tax-rates` to verify the YAML table loads.
8. **Tax Calculator** – Use the `Estimate Tax (TIB)` request with sample payload; repeat with the TTNB variant.

## 3. Authentication Flow
1. **Register Citizen** – Send the request with unique `username`/`email`. Update payload before each run to avoid conflicts.
2. **Register Business** – Repeat for a business account if needed.
3. **Login** – Execute `POST /api/auth/login` with the citizen credentials. Copy the returned `access_token`.
4. **Configure Auth** – In the `Development` environment set the `token` variable to the access token so Insomnia auto-injects `Authorization: Bearer ...`.
5. **Refresh Token** – Send `POST /api/auth/refresh` to confirm refresh flow works.
6. **Get Profile** – Run `GET /api/auth/me` to ensure the token identifies the user role.

## 4. Property (TIB) Scenario
1. **Declare Property** – Use `POST /api/tib/properties` with payload referencing a valid `commune_id`, `covered_surface`, and sample address.
2. **List Properties** – Execute `GET /api/tib/properties` and verify the entry created above appears with status `draft` or `pending`.
3. **Fetch Property Taxes** – Call `GET /api/tib/my-taxes` to see calculated assessments.
4. **Download Documents (Optional)** – Use `GET /api/v1/documents/documents/{id}/file` if attachments were created in the workflow.

## 5. Land (TTNB) Scenario
1. **Declare Land** – Send `POST /api/ttnb/lands` with surface, land type, and coordinates.
2. **List Lands** – Execute `GET /api/ttnb/lands` to confirm persistence.
3. **View Land Taxes** – Call `GET /api/ttnb/my-taxes` and cross-check the amount with the TTNB calculator.

## 6. Payments and Attestations
1. **Pay Tax** – Use `POST /api/payments/pay` referencing an outstanding tax ID and a mock payment method.
2. **Verify Status** – Re-run `GET /api/tib/my-taxes` or `GET /api/ttnb/my-taxes` to ensure the status switches to `paid`.
3. **Payment History** – Execute `GET /api/payments/my-payments`.
4. **Attestation** – Call `GET /api/payments/attestation/{user_id}` to confirm receipts are generated.

## 7. Disputes and Reclamations
1. **Create Dispute** – `POST /api/disputes/` with a reference tax ID and reason.
2. **List Disputes** – `GET /api/disputes/` should display the submission. For admin roles, follow up with commission review endpoints.
3. **Submit Reclamation** – `POST /api/reclamations/` then `GET /api/reclamations/my-reclamations` to verify.

## 8. Permits and Budgeting
1. **Request Permit** – `POST /api/permits/request` referencing a fully paid property.
2. **List Permits** – `GET /api/permits/my-requests` to monitor decision workflow.
3. **Participatory Budget** – Use `GET /api/budget/projects` (and `POST /api/budget/vote/{id}` if enabled) to validate civic engagement features.

## 9. Cleanup
1. **Logout** – `POST /api/auth/logout` to invalidate the token.
2. **Stop Stack** – `docker compose -f docker/docker-compose.yml down` once testing completes.

Document any deviations in a QA log so regressions can be reproduced.

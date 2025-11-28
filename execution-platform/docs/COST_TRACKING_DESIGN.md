Cost Tracking Design

- Capture usage in adapters; normalize to {input_tokens, output_tokens, cost_usd}
- Pricing tables per provider/model; versioned
- Budgets: per-persona/per-tenant per-minute/hour/day; enforced at Gateway (pre-check + mid-stream)
- Attribution: include personaId/tenantId in usage events; store in DB (Phase 2)
- Dashboards: costs over time, by provider/persona; alerts on thresholds

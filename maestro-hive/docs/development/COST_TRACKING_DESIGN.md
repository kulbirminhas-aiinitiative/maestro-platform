# Cost Tracking Design

- Capture usage per request from adapters; normalize tokens/characters.
- Pricing tables per model/provider with effective dates; minimum charges and caching rates.
- Budget enforcement at Gateway: reject or degrade when exceeded.
- Attribution: tenant, persona, feature; export to metrics and billing.
- Dashboards: p50/p95 cost/request, cost per token, budget burn-down.
- Alerts: thresholds per tenant/provider.

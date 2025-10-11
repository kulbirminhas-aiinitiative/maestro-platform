✓ Read ~/projects/maestro-platform/maestro-templates/docs/PACKAGE_COMPATIBILITY_MATRIX.md (472 lines)

 ● Here is a critical review of PACKAGE_COMPATIBILITY_MATRIX.md with corrections,
   risk flags, and pragmatic improvements to make it actionable and safe to use for
   production standardization.

   What’s strong

     * Clear triage and prioritization: security first (axios), runtime/EOL, then framework harmonization 
   and observability.
     * Concrete migration steps for aioredis → redis asyncio and attention to FastAPI’s 
   dependency-with-yield hazards.
     * Useful upgrade guidance for Node/React/Vite/Next along with Python ecosystem notes.
     * Sensible testing and validation checklists.

   Accuracy and risk flags to address

     * CVE claims and version specifics
       * The document cites “CVE-2025-27152: axios SSRF & credential leakage” and versions “fixed in 
   1.8.2+.” Because this is a forward-dated CVE, please validate the CVE ID and fixed version against 
   NVD/GitHub advisories before acting. Action: cross-check with npm audit, Snyk, or GitHub Advisories, 
   then pin the exact fixed version. If urgent, you can temporarily enforce an npm override for axios to 
   the vetted fixed version across all workspaces:
           {
             "overrides": {
           "axios": "x.y.z"
             }
           }
     * “TRANSFORMERS_CACHE” deprecation
       * Recommend listing the preferred environment variables explicitly: HF_HOME and HF_HUB_CACHE are 
   the modern equivalents. Some tooling still honors TRANSFORMERS_CACHE; call out both and the migration 
   deadline.
     * FastAPI breaking change summary
       * The “dependency-with-yield runs after response is sent” note is context-dependent. What’s 
   critical operationally is to audit:
         
       * lifespan vs dependency-with-yield usage,
           
         
       * DB session lifecycle with StreamingResponse and background tasks.
       
       * Recommendation: add a targeted checklist (see below) and link to a minimal reproducible example 
   to verify behavior per service.
     * Uvicorn workers and Gunicorn
       * The doc correctly notes uvicorn.workers deprecation; explicitly recommend using “gunicorn -k 
   uvicorn.workers.UvicornWorker” replacement “uvicorn-worker” package, or swap to “gunicorn[uvicorn]” 
   depending on your deployment style. Provide a sample command line for production.
     * Node/React/Vite versions
       * Node 18 EOL in Apr 2025 is correct; endorse moving to node:22-alpine as stated.
       
       * React 19 migration: indicate current status (RC vs stable in your repos) and recommend a cautious
    plan: upgrade to 18.3 first, adopt new patterns, then 19 when stable across your dependencies.
       
       * Vite 7 requires Node >=20.19 or 22.12; make the Node baseline explicit for all FE repos to avoid 
   CI surprises.
     * Next.js lifecycle dates
       * If your conductor dashboards are on Next 14, add the exact installed version from package.json 
   and a reminder that 15 may introduce server-actions/edge runtime differences. Suggest a test branch 
   before committing org-wide.

   Gaps and suggested improvements

     * Provenance of the scan
       * The header claims “12 projects, 1,669 dependencies, 357 unique packages.” Add a “How to 
   reproduce” box: which repos and paths were scanned, at which commit(s), with which tool and timestamp. 
   Include the inventory artifacts (JSON/CSV) and how they’re generated. That makes the matrix auditable.
     * Make it enforceable in CI/CD
       * Add a Policy section with:
         
       * Python: minimum version (3.11 baseline), Poetry 2.x, pydantic 2.11.x, uvicorn 0.37.x, FastAPI 
   0.118.x (or whatever you finalize).
           
         
       * Node: Node 22.x baseline, npm 10.x baseline, Vite 7 for FE repos.
           
         
       * Docker: Only approved base images (node:22-alpine, python:3.11-slim, etc.).
       
       * Wire these into:
         
       * Poetry constraints (constraints.txt or group-level constraints),
           
         
       * Renovate/Dependabot rules,
           
         
       * npm “engines” fields,
           
         
       * dockerfile lints, and
           
         
       * CI gates: fail on EOL runtimes or vulnerable dependencies (Trivy/Grype).
     * NPM transitive overrides strategy
       * For urgent critical fixes (e.g., axios), document how to use “overrides” to force transitive 
   dependencies, and list side effects and rollback steps. Add a global .npmrc (save-exact=true) to avoid 
   accidental minor bumps in PROD.
     * SBOM and vulnerability scanning
       * Add commands to generate SBOMs (CycloneDX or Syft) and scan them. Recommend:
         
       * Syft or cyclonedx-python/cyclonedx-nodejs for SBOM,
           
         
       * Grype or Trivy for CVE scanning (in CI) with severity thresholds.
     * Pinned versions vs caret ranges
       * The section “Always pin exact versions in production” shows caret ranges in code blocks. Clarify:
         
       * Use caret ranges in pyproject/package.json during development,
           
         
       * Enforce exact pins via lock files (poetry.lock/package-lock.json) for reproducible builds in 
   CI/CD,
           
         
       * And tag releases with lockfile snapshots so production deployments are deterministic.
     * Add a concrete “FastAPI yield” audit checklist
       * Search for dependencies that return generators (yield) and streaming responses. Ensure DB 
   sessions aren’t closed prematurely post-upgrade. Provide a code grep pattern and a quick test snippet:
         
       * grep -R "yield" in dependencies
           
         
       * Tests that open a transaction, stream N chunks, and verify session closure timing.
     * OpenTelemetry migration specifics
       * List specific packages to verify (opentelemetry-instrumentation-fastapi, -requests, -sqlalchemy, 
   -logging, -redis). Show import change examples and a one-liner for semconv mapping updates. Add a 
   canary span test (parent-child attributes) to detect breakage.
     * Python runtime unification
       * The table mentions Python 3.9 in fleet; formally declare Python 3.11 baseline and add a short 
   migration section: upgrade Docker base image, recompile wheels, run pytest. If any repo still on 3.9, 
   add owner and deadline.
     * Add an overrides matrix for Docker images
       * For each Dockerfile.* in maestro-engine-new, list found base images and target replacements 
   (node:22-alpine, python:3.11-slim, debian:bookworm-slim). This creates a clear to-do.

   High-priority action items (next 3–5 days)

     * Validate axios advisory and force a single fixed version:
       * Add an overrides block in all FE package.json and shared workspaces; run npm audit; regression 
   test critical HTTP flows.
     * Update Node base images
       * Replace node:18-alpine → node:22-alpine in all Dockerfiles; run builds; run FE e2e.
     * aioredis migration
       * Apply redis asyncio import swap and remove aioredis; run integration tests targeting Redis 
   endpoints.
     * FastAPI harmonization plan
       * Freeze current FastAPI (pin), add tests around yield dependencies and streaming responses, then 
   upgrade to 0.118.x in a branch and run the suite. Prioritize services with streaming/long-lived 
   responses.
     * CI gates
       * Add Trivy/Grype scans to pipelines with fail-on-critical; npm audit in CI with a blocklist of 
   high-severity advisories; enable dependabot/renovate with policy rules.

   Concrete edits to the document to consider

     * Add “Scan provenance” section and a “How to reproduce” block, referencing 
   package_discovery_scanner.py output and the commit SHAs.
     * Add a “Standards and constraints” table:
       * Python: 3.11.x, FastAPI 0.118.x, Pydantic 2.11.x, Uvicorn 0.37.x.
       
       * Node: 22.x, npm 10.x, Vite 7.x.
       
       * Base images: python:3.11-slim, node:22-alpine.
     * Replace the axios CVE mention with “validate advisory ID and fixed version” and reference an 
   internal ticket to track it.
     * Add SBOM generation and scanning commands, including minimum thresholds.
     * Clarify pinning approach: caret in manifests for dev, exact pins via lock files for CI/CD and 
   production.
     * Include a short “owner + deadline” matrix for each critical migration (axios, aioredis, Node 22, 
   FastAPI uplift).

   Targeted checklist you can copy into the doc

     * Axios
       * [ ]  Validate CVE ID and fixed version
       
       * [ ]  Add npm overrides to all workspaces
       
       * [ ]  Run npm audit and regression tests
     * Node 22
       * [ ]  Update Dockerfiles to node:22-alpine
       
       * [ ]  Update CI Node version matrix
       
       * [ ]  Rebuild, run e2e
     * aioredis
       * [ ]  Swap imports to redis asyncio
       
       * [ ]  Remove aioredis dependency
       
       * [ ]  Run Redis integration suite
     * FastAPI
       * [ ]  Pin current version
       
       * [ ]  Add tests for yield dependencies and streaming
       
       * [ ]  Upgrade to 0.118.x in a branch
       
       * [ ]  Fix lifecycle and retest
     * OpenTelemetry
       * [ ]  Pin to 1.37.x (or chosen)
       
       * [ ]  Update semconv imports and attribute names
       
       * [ ]  Validate spans and logs with a canary trace
     * SBOM and Scanning
       * [ ]  Generate SBOM for each service
       
       * [ ]  Scan with Trivy/Grype; fail CI on critical
       
       * [ ]  Store SBOM artifacts in the build

   Bottom line The matrix is a strong starting point. To make it deploy-safe and
   auditable:

     * Validate forward-dated advisories, and enforce fixes via overrides and CI scans.
     * Encode standards as constraints and CI/CD gates, not just guidance.
     * Add provenance, SBOM/scanning, and deterministic pinning policies.
     * Provide targeted audit checklists for FastAPI yield dependencies and OTel semconv changes.

   If you want, I can:

     * Patch the doc with the “provenance,” “standards,” and “SBOM/scanning” sections, and align the 
   pinning policy examples.
     * Search your repos for axios usage, aioredis imports, FastAPI yield dependencies, and Node 18 base 
   image references and produce a precise PR checklist per repo.
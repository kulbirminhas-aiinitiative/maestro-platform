# ADR-XXXX: Phase Gate Bypass - [Gate Name] for [Phase Name]

**Status:** [Proposed | Approved | Rejected]
**Date:** YYYY-MM-DD
**Author:** [Your Name]
**Approvers:** [Required Approvers]
**Workflow ID:** [Workflow ID]
**Phase:** [Phase Name]
**Gate:** [Gate Name]

---

## Context

**What quality gate is being bypassed?**
[Describe the specific gate: e.g., "test_coverage gate requiring 80% coverage"]

**What is the current situation?**
[Describe the current metrics/status: e.g., "Current test coverage is 65%"]

**Why is the bypass needed?**
[Explain the business context and urgency]

**What is the impact if we don't bypass?**
[Describe the consequences: e.g., "Delay of 2 weeks to add missing tests"]

---

## Decision

**Bypass Request:** [Approved | Rejected]

**Justification:**
[Provide detailed justification for the bypass]

**Alternative Considered:**
[What alternatives were evaluated?]

**Risk Assessment:**
- **Technical Risk:** [Low | Medium | High]
- **Business Risk:** [Low | Medium | High]
- **Security Risk:** [Low | Medium | High]

**Risk Description:**
[Describe the risks of bypassing this gate]

---

## Conditions and Constraints

**Bypass Duration:**
[Temporary | Permanent]

**If Temporary, Expiration Date:**
[YYYY-MM-DD]

**Remediation Plan:**
[How will the issue be addressed? What is the timeline?]

**Compensating Controls:**
[What additional measures are being taken to mitigate the risk?]

**Monitoring Requirements:**
[How will we monitor that this bypass doesn't cause issues?]

---

## Approval

**Required Approvals:**
- [ ] Technical Lead: [Name] - [Approval Date]
- [ ] Product Manager: [Name] - [Approval Date]
- [ ] Security Lead (if security-related): [Name] - [Approval Date]
- [ ] QA Lead (if quality-related): [Name] - [Approval Date]

**Approval Notes:**
[Any additional notes from approvers]

---

## Audit Trail

**Bypass Requested By:** [Name]
**Request Date:** [YYYY-MM-DD HH:MM:SS]
**Bypass Approved By:** [Name]
**Approval Date:** [YYYY-MM-DD HH:MM:SS]
**Bypass Applied Date:** [YYYY-MM-DD HH:MM:SS]
**Bypass ID:** [Generated UUID]

**Related Documentation:**
- Workflow Run: [URL or Path]
- Phase Execution Log: [URL or Path]
- Quality Report: [URL or Path]

---

## Follow-up

**Follow-up Required:** [Yes | No]

**Follow-up Tasks:**
- [ ] Task 1: [Description] - Due: [Date] - Owner: [Name]
- [ ] Task 2: [Description] - Due: [Date] - Owner: [Name]

**Follow-up Verification:**
[How will we verify the remediation was completed?]

**Lessons Learned:**
[What did we learn from this bypass that could improve our process?]

---

## Example Usage

### Good Example: Temporary Bypass with Remediation

```markdown
# ADR-0123: Phase Gate Bypass - Test Coverage for Implementation Phase

**Status:** Approved
**Date:** 2025-10-12
**Author:** Jane Developer
**Approvers:** Tech Lead, QA Lead
**Workflow ID:** wf-20251012-143022
**Phase:** Implementation
**Gate:** test_coverage (requires 80%)

## Context

**What quality gate is being bypassed?**
Test coverage gate requiring 80% coverage for implementation phase.

**What is the current situation?**
Current test coverage is 68%. Core business logic has 95% coverage, but legacy
helper utilities have minimal coverage.

**Why is the bypass needed?**
Customer-critical bug fix must be deployed today. The fix itself has 100% test
coverage, but overall project coverage is pulled down by legacy code.

**What is the impact if we don't bypass?**
Production outage continues for 24 hours while we add tests for legacy utilities
that are unrelated to the bug fix.

## Decision

**Bypass Request:** Approved

**Justification:**
- Bug fix code has 100% coverage
- Legacy utilities are being replaced next sprint
- Customer impact is severe (revenue loss)
- Technical debt for legacy code is already tracked

**Alternative Considered:**
Wait for full test coverage - rejected due to customer impact.

**Risk Assessment:**
- **Technical Risk:** Low (bug fix itself is well-tested)
- **Business Risk:** Medium (setting precedent for bypasses)
- **Security Risk:** Low (not security-related code)

**Risk Description:**
Main risk is setting a precedent for coverage bypasses. Mitigated by making this
clearly temporary and time-bound.

## Conditions and Constraints

**Bypass Duration:** Temporary

**If Temporary, Expiration Date:** 2025-10-19 (1 week)

**Remediation Plan:**
1. Sprint planning session 2025-10-14 to prioritize legacy utility testing
2. Add tests for legacy utilities by 2025-10-18
3. Re-run validation to confirm 80% coverage by 2025-10-19

**Compensating Controls:**
- Manual testing of affected utilities completed
- Smoke tests pass in staging environment
- Rollback plan documented and tested

**Monitoring Requirements:**
- Monitor error rates for 48 hours post-deployment
- Alert if error rate increases >5%
- Daily check-in with on-call engineer

## Approval

**Required Approvals:**
- [x] Technical Lead: John Smith - 2025-10-12 14:45
- [x] QA Lead: Sarah QA - 2025-10-12 14:50

**Approval Notes:**
Approved given customer impact. Legacy utilities replacement already planned for
next sprint. Monitoring plan looks good.

## Audit Trail

**Bypass Requested By:** Jane Developer
**Request Date:** 2025-10-12 14:30:00
**Bypass Approved By:** John Smith, Sarah QA
**Approval Date:** 2025-10-12 14:50:00
**Bypass Applied Date:** 2025-10-12 14:55:00
**Bypass ID:** bypass-7f3e9a2b-8c1d-4e5f-a6b7-9d8e7f6a5b4c

**Related Documentation:**
- Workflow Run: /tmp/maestro_workflow/wf-20251012-143022
- Phase Execution Log: logs/implementation_20251012.log
- Quality Report: reports/quality_20251012.json

## Follow-up

**Follow-up Required:** Yes

**Follow-up Tasks:**
- [x] Task 1: Add tests for StringUtils - Due: 2025-10-16 - Owner: Jane Developer
- [x] Task 2: Add tests for DateHelpers - Due: 2025-10-17 - Owner: Bob Dev
- [ ] Task 3: Verify 80%+ coverage - Due: 2025-10-19 - Owner: Jane Developer

**Follow-up Verification:**
Run full test suite and verify coverage report shows ≥80% coverage.

**Lessons Learned:**
- Need better separation between legacy and new code coverage metrics
- Consider excluding legacy utilities from gate requirements if replacement is planned
- Customer escalation process worked well
```

---

## Bad Example: Permanent Bypass without Justification

```markdown
# ADR-0124: Phase Gate Bypass - Code Quality for Implementation Phase

**Status:** Proposed
**Date:** 2025-10-12
**Author:** Unknown
**Gate:** code_quality (requires 8.0)

## Context

**What is the current situation?**
Code quality is 6.5.

**Why is the bypass needed?**
Code works, quality gates are too strict.

## Decision

**Bypass Request:** Approved

**Justification:**
We need to deploy.

## Conditions and Constraints

**Bypass Duration:** Permanent

❌ THIS IS A BAD EXAMPLE - LACKS:
- Specific justification
- Risk assessment
- Approver names
- Remediation plan
- Compensating controls
- Follow-up tasks
- Proper audit trail
```

---

## Notes

- All fields marked with [brackets] must be filled in
- Status starts as "Proposed" and moves to "Approved" or "Rejected"
- Security-related bypasses MUST have Security Lead approval
- Permanent bypasses require VP-level approval
- Bypass ID is auto-generated by the bypass system
- This document should be committed to version control
- Copy this template to `docs/adr/ADR-XXXX_description.md` for each bypass

---

**Template Version:** 1.0.0
**Last Updated:** 2025-10-12

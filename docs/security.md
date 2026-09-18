# Security and Governance Specification

## Authentication & Authorization
- **JWT Authentication**: Signed with HMAC-SHA256 (`HS256`).
- **Password Hashing**: Cryptographically secure `bcrypt` hashing with salt rounds.
- **Role-Based Access Control (RBAC)**:
  - `ADMIN`: Full administrative control, incident creation, remediation execution, audit log inspection.
  - `SRE_ENGINEER`: Incident management, telemetry ingestion, AI investigation, remediation approval.
  - `VIEWER`: Read-only access to dashboards, service topologies, and runbooks.

## Remediation Safety Protocols
- Destructive commands are strictly prohibited from autonomous execution.
- Human approval is mandatory for all remediation actions.
- Simulated execution provides before/after health probes to verify recovery before marking incidents as resolved.
- Comprehensive audit logging records user ID, action, target resource, and JSON execution payload.

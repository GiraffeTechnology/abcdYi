# Security and Data Policy

- Authentication required for all non-health routes (JWT)
- Role-based access control enforced at route and service level
- No secrets committed to repository — use .env only
- Append-only execution event log
- Audit log for all approvals and permission changes
- Uploaded file metadata only stored in DB (actual files stored outside repo)
- Data retention: defined per deployment by operator

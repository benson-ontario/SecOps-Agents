# Investigation Pack — Query Descriptions (AI Agent Reference)

---

## PACK: USER_COMPROMISE_V1

---

### NEW_DEVICE_DETECTION
**What it does:** Compares devices seen in the last 48 hours against a 30-day baseline for the target user. Returns sign-ins from devices with no prior history.
**Substitutions:** `UserPrincipalName`
**When to use:** Run on every user investigation. Any sign-in from an unrecognised device is a direct indicator of unauthorised access — an attacker authenticating from their own machine, a new VM, or a device enrolled specifically for this attack. Results showing unknown devices should immediately raise investigation priority.

---

### FAILED_LOGIN_PATTERN
**What it does:** Aggregates all failed sign-ins for the user. Returns total failure count, number of distinct source IPs, and a spray flag that triggers when failures come from more than 5 distinct IPs.
**Substitutions:** `UserPrincipalName`
**When to use:** Run on every user investigation. Establishes whether the account is under active credential attack and whether that attack is distributed across IPs (spray) or concentrated from a single source (brute force). A high failure count with no success still matters — it confirms the account is being targeted.

---

### MFA_ACTIVITY_CHECK
**What it does:** Counts sign-in events split by whether MFA was used or not. Returns `MFAEvents` and `NonMFAEvents` totals.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when the incident involves any sign-in anomaly or when there is reason to believe MFA was bypassed. Non-MFA sessions from a user who normally authenticates with MFA indicate legacy protocol abuse, a conditional access gap, or a successful bypass. Skip only if MFA is known to not be enforced for this user.

---

### TOKEN_REUSE_CHECK
**What it does:** Filters sign-ins using a Primary Refresh Token (PRT) and returns total uses alongside distinct IPs and devices that presented the same token.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when the incident involves unfamiliar IPs, sessions from unexpected locations, or when non-interactive activity is elevated. A PRT used from multiple IPs or devices is definitive evidence of token theft — the attacker has extracted the token and is replaying it from their own infrastructure. Skip if there is no indication of token-based activity.

---

### CROSS_TENANT_SIGNINS
**What it does:** Returns sign-in events where the user authenticated into a resource in a different Azure AD tenant. Includes access type, target tenant ID, IP, and timestamp.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when the incident suggests post-compromise lateral movement, or when the user has cross-tenant roles or partner relationships. An attacker with valid credentials may use them to pivot into external organisations the victim has access to. Skip for users with no known cross-tenant access or guest relationships.

---

### NONINTERACTIVE_TOKEN_USAGE
**What it does:** Queries background token refresh and app-to-app sign-in logs for the target user. Returns total count, distinct applications, and distinct IPs.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when interactive sign-in logs appear clean but compromise is still suspected, or when the incident involves application-level access. Non-interactive logs are frequently overlooked — an attacker with a stolen token can maintain persistent silent access across multiple applications without ever triggering an interactive sign-in alert.

---

### RISKY_USER_STATUS
**What it does:** Returns the user's current risk level, risk state, and risk detail from AAD Identity Protection.
**Substitutions:** `UserPrincipalName`
**When to use:** Run on every user investigation, always early. This is the fastest way to determine whether Microsoft has already assessed this account as compromised. A `confirmedCompromised` or `atRisk` state with `high` level immediately confirms the incident is serious and should accelerate all other queries.

---

### ADMIN_PORTAL_ACCESS
**What it does:** Filters sign-ins to Azure Portal, Microsoft Admin Center, and Azure Management for the target user. Returns timestamp, application, IP, and location.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when there is any indication the account may have elevated privileges, or when the incident involves suspicious activity from an unfamiliar IP. Attackers who gain access to a privileged account will typically pivot to admin portals to enumerate permissions, modify configurations, or create persistence. For low-privilege accounts with no admin access, this query is lower priority.

---

### PRIVILEGE_CHANGES
**What it does:** Searches audit logs for role assignment or privilege modification operations where the target user is the subject. Returns operation name, initiating identity, and affected resources.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when admin portal access is confirmed, when the account holds elevated privileges, or when the incident is high severity. Detects both privilege being granted to the user (attacker elevating a compromised account) and the user granting privilege to others (attacker creating a secondary foothold). Skip for standard user accounts with no administrative role.

---

### IMPOSSIBLE_TRAVEL
**What it does:** Returns a chronological list of every sign-in for the user with timestamp, source country, and IP address ordered by time.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when the incident involves sign-ins from unexpected locations, or when source IPs resolve to countries inconsistent with the user's normal geography. The agent must evaluate the returned sequence — flag any case where the elapsed time between sign-ins is too short to allow legitimate travel between the indicated countries.

---

### USER_ACTIVITY_TIMELINE
**What it does:** Returns the full chronological sign-in history for the user across all applications, including result codes and device detail.
**Substitutions:** `UserPrincipalName`
**When to use:** Run on every user investigation. This is the primary context query — it establishes the complete picture of what the account has been doing, which applications were accessed, and whether activity patterns are consistent with normal behaviour. Run early and use the results to inform which other queries to prioritise.

---

### TOKEN_REPLAY_DETECTION
**What it does:** Groups sign-ins by unique token identifier and returns any token that was used from more than one distinct IP or device. Returns event count, distinct IP count, and distinct device count per token.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when non-interactive token usage is elevated, when the same session appears to originate from multiple IPs, or when AiTM phishing is suspected. A single token appearing across multiple IPs or devices is the strongest possible evidence of token theft — this finding alone is sufficient to confirm compromise.

---

### CONDITIONAL_ACCESS_BYPASS
**What it does:** Returns sign-in events where Conditional Access policy was not applied or failed. Includes timestamp, application, IP, CA status, and location.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when non-MFA sessions are detected, when legacy protocol use is suspected, or when sign-ins are coming from non-compliant or unmanaged devices. A pattern of `notApplied` results indicates the attacker is deliberately using authentication paths that avoid policy enforcement — legacy SMTP, IMAP, or older OAuth flows are common vectors.

---

### MFA_METHOD_CHANGES
**What it does:** Searches audit logs for operations that modified authentication methods or MFA configuration for the target user. Returns operation name, initiating identity, and target resources.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when MFA bypass is suspected, when the account has recently had a password reset, or when the incident involves persistent re-access after apparent remediation. An attacker who registers their own authenticator app can maintain access even after the victim changes their password. This query confirms whether that has occurred.

---

### SERVICE_PRINCIPAL_CREDENTIAL_CHANGES
**What it does:** Searches audit logs for credential or secret additions, updates, or removals on service principals across the tenant.
**Substitutions:** none — this is a tenant-wide query with no entity scoping. Returns all service principal credential changes regardless of which user is under investigation.
**When to use:** Run when the compromised account holds application administrator, cloud application administrator, or equivalent roles — permissions that allow modifying app registrations. Adding credentials to an existing service principal is a common persistence technique that survives password resets and account remediation. Skip for accounts with no app management permissions.

---

### AZURE_CONTROL_PLANE_ACTIVITY
**What it does:** Queries Azure Activity logs for resource-level operations performed by the target user. Returns timestamp, operation name, resource group, resource provider, and caller IP.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when admin portal access is confirmed, when the account has Azure subscription roles, or when the incident is high severity. Shows whether the attacker has moved beyond identity activity into actual Azure resource manipulation — deploying infrastructure, modifying policies, or accessing storage and compute. Skip for accounts with no Azure resource permissions.

---

### RISKY_SIGNINS
**What it does:** Returns sign-in events that Identity Protection has flagged as risky at medium or high level. Includes risk detail, IP, and application per event.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when `RISKY_USER_STATUS` returns a risk state, or when sign-ins from unfamiliar IPs or locations are present. This surfaces the specific sign-in events Microsoft considers high-confidence threats, which helps the agent prioritise which sessions to investigate further and which IPs to feed into IP-level investigation.

---

### NONINTERACTIVE_TOKEN_ANOMALY
**What it does:** Aggregates non-interactive sign-in activity and flags it as suspicious when it involves more than 5 distinct IPs or more than 10 distinct applications. Returns counts with a boolean suspicious flag.
**Substitutions:** `UserPrincipalName`
**When to use:** Run when `NONINTERACTIVE_TOKEN_USAGE` returns elevated counts, or when token theft is suspected. High IP diversity in non-interactive logs indicates attacker tooling accessing multiple services programmatically using a stolen token — a pattern common after AiTM phishing where harvested tokens are used to enumerate and exfiltrate across cloud services.

---

### OAUTH_APP_CONSENT
**What it does:** Returns audit log entries for consent operations across the tenant. Includes timestamp, operation, initiating identity, and target application.
**Substitutions:** none — this is a tenant-wide query with no entity scoping. Returns all consent grant operations regardless of which user is under investigation.
**When to use:** Run when non-interactive application access is elevated, when unfamiliar applications appear in sign-in logs, or when the incident may involve phishing. Illicit OAuth consent grants a malicious third-party application persistent delegated access to the victim's mailbox, files, or other resources — access that survives password resets because it operates via app permissions, not user credentials.

---
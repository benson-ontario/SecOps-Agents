## PACK: IP_INVESTIGATION_V1

---

### IP_ACTIVITY_SUMMARY
**What it does:** Produces a single-row summary of all sign-in activity from the target IP over 7 days. Returns total attempts, unique user count, failed and successful attempt counts, and first/last seen timestamps.
**Substitutions:** `IPAddress`
**When to use:** Run on every IP investigation, always first. This is the baseline query — it tells the agent the scale and outcome of activity from this IP before any other query runs. A high unique user count confirms spray behaviour. Any successful authentications immediately escalate priority and should trigger user-level follow-up.

---

### MULTI_USER_SPRAY_CHECK
**What it does:** Returns the count of distinct users targeted from this IP, total failures, and a list of up to 50 targeted accounts. Only returns results when more than 5 distinct users were targeted.
**Substitutions:** `IPAddress`
**When to use:** Run on every IP investigation. Confirms whether this IP is conducting a spray attack across multiple accounts. The returned user list is the direct input for follow-up user investigation — any user in this list who also had a successful sign-in from the IP should immediately be queued for `USER_COMPROMISE_V1`.

---

### FAILURE_TO_SUCCESS_PATTERN
**What it does:** Counts failures and successes from the target IP over 3 days. Only returns results when there are more than 10 failures and at least one success.
**Substitutions:** `IPAddress`
**When to use:** Run on every IP investigation. A positive result is the highest-priority finding in any credential attack scenario — it means the attack succeeded and at least one account has been compromised. Treat any result from this query as requiring immediate user-level investigation for all accounts that had a successful sign-in from this IP.

---

### GEO_DIVERSITY_CHECK
**What it does:** Returns the set of distinct countries seen across all sign-ins from this IP and a count. A single IP authenticating on behalf of users across multiple countries indicates proxy or anonymization infrastructure.
**Substitutions:** `IPAddress`
**When to use:** Run when the IP is flagged as suspicious but its nature is unknown, or when activity patterns suggest it may be shared infrastructure. A legitimate user device shows one country consistently. High country diversity from a single IP is strong evidence the IP is a VPN exit node, Tor relay, or proxy — meaning the true attacker origin is masked.

---

### NONINTERACTIVE_TOKEN_ACTIVITY
**What it does:** Returns the count of non-interactive sign-ins from this IP and the set of user accounts involved.
**Substitutions:** `IPAddress`
**When to use:** Run when interactive sign-in volume from the IP is low but compromise is still suspected, or when the IP appears in non-interactive logs but not prominently in interactive ones. Stolen tokens are frequently replayed silently — an attacker IP may show minimal interactive activity while conducting significant non-interactive access across multiple accounts.

---

### SERVICE_PRINCIPAL_ACTIVITY
**What it does:** Returns service principal names, accessed resources, and total attempt count for service principal authentications from this IP.
**Substitutions:** `IPAddress`
**When to use:** Run when the IP shows low or no user sign-in activity but is still flagged as suspicious, or when application-level access is part of the incident. Service principal authentication from an external attacker IP indicates compromised client credentials or client secrets — the attacker is operating at the application layer, not the user layer.

---

### MANAGED_IDENTITY_ACTIVITY
**What it does:** Returns managed identity IDs and attempt count for managed identity authentications from this IP.
**Substitutions:** `IPAddress`
**When to use:** Run when service principal activity is present or when the incident involves Azure workload compromise. Managed identity traffic from an arbitrary external IP is inherently anomalous — these identities are bound to specific Azure resources and should never authenticate from an external attacker-controlled IP. Any result here is a high-confidence finding.

---

### ADMIN_PORTAL_TARGETING
**What it does:** Returns the total count of sign-in attempts from this IP against Azure Portal, Microsoft Admin Center, and Azure Management.
**Substitutions:** `IPAddress`
**When to use:** Run when `IP_ACTIVITY_SUMMARY` shows successful authentications, or when the IP is associated with a high-privilege account. Targeted admin portal access from a suspicious IP indicates the attacker is specifically seeking administrative access rather than conducting broad credential harvesting. Elevates severity of the incident significantly.

---

### AZURE_CONTROL_PLANE_ACTIVITY
**What it does:** Returns Azure resource operations performed from this IP and total operation count.
**Substitutions:** `IPAddress`
**When to use:** Run when admin portal targeting is confirmed or when successful authentications have been identified. Shows whether the IP has been used not just to authenticate but to manipulate Azure resources — creating infrastructure, modifying policies, or accessing storage. A positive result means the incident has moved beyond credential attack into active resource compromise.

---

### PRIVILEGE_CHANGE_ACTIVITY
**What it does:** Returns privilege and role assignment operations initiated from this IP and total count.
**Substitutions:** `IPAddress`
**When to use:** Run when successful authentications or admin portal access are confirmed from this IP. Privilege changes originating from a suspicious IP indicate an attacker actively establishing persistence or escalating access — this finding confirms an active hands-on intrusion rather than an automated credential attack.

---

### RISKY_USER_DETECTIONS
**What it does:** Joins sign-ins from this IP with the risky users table and returns accounts that both authenticated from this IP and are currently flagged by Identity Protection. Returns UPN, risk level, and risk state.
**Substitutions:** `IPAddress`
**When to use:** Run when `MULTI_USER_SPRAY_CHECK` or `USER_TARGET_TIMELINE` return a list of targeted users. Immediately identifies which of those users Identity Protection has already assessed as compromised — these accounts require urgent containment and should be the first queued for `USER_COMPROMISE_V1`.

---

### DEVICE_PATTERN_ANALYSIS
**What it does:** Returns the set of operating systems and browsers seen across all sign-ins from this IP.
**Substitutions:** `IPAddress`
**When to use:** Run when the nature of the IP is unknown and there is no external threat intelligence available. A narrow, consistent OS/browser combination suggests a single automated tool. A single generic user-agent string across many users confirms scripted attacks. An implausibly broad and varied set suggests spoofed user-agents. Use the result to characterise the IP as attacker tooling, proxy infrastructure, or potentially legitimate.

---

### USER_TARGET_TIMELINE
**What it does:** Returns a chronological list of every sign-in event from this IP including timestamp, targeted user, application, result code, and country.
**Substitutions:** `IPAddress`
**When to use:** Run when `FAILURE_TO_SUCCESS_PATTERN` returns a positive result, or when the full sequence of attacker activity needs to be reconstructed. Shows exactly who was targeted, in what order, against which applications, and when any successful authentications occurred. The post-success entries in the timeline reveal which applications the attacker accessed immediately after gaining entry.
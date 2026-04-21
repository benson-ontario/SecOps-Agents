import os
import json
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

MCP_BASE_URL = os.environ['MCP_BASE_URL']
# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRIVILEGED_ACCOUNT_KEYWORDS = [
    "sync", "admin", "service", "svc", "root", "global",
    "dirsync", "adsync", "aadsync", "connector",
]

SEVERITY_RANK = {
    "critical": 4,
    "high":     3,
    "medium":   2,
    "low":      1,
    "info":     0,
}

# Minimum confidence thresholds for auto-block, depending on how many
# independent signals agree (agent recommendation × severity).
BLOCK_THRESHOLDS = {
    # (agent_recommends_block, severity_rank >= HIGH)
    (True,  True):  4.5,   # both agree on a high/critical incident → lower bar
    (True,  False): 6.0,   # agent says block but severity is medium/low
    (False, True):  7.0,   # high/critical but agent doesn't recommend block
    (False, False): 7.5,   # neither signal strong — need solid evidence
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_hypotheses(raw: str) -> dict:
    """
    Accepts both valid JSON  '{"total": 3, "supported": 2}'
    and plain-text          'total: 3, supported: 2'.
    """
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
        logger.info("Hypotheses (JSON): %s", parsed)
        return parsed
    except json.JSONDecodeError:
        result = {}
        for part in raw.split(","):
            part = part.strip()
            if ":" in part:
                key, _, value = part.partition(":")
                result[key.strip()] = int(value.strip())
        if "total" not in result or "supported" not in result:
            raise ValueError(f"Cannot parse hypotheses: '{raw}'")
        logger.info("Hypotheses (fallback): %s", result)
        return result


def is_privileged_account(account: str) -> bool:
    account_lower = account.lower()
    return any(kw in account_lower for kw in PRIVILEGED_ACCOUNT_KEYWORDS)

# TODO: this is account disabling fucntion. Commented temporary

# def disable_user(account):
#     result = requests.post(MCP_BASE_URL, json={
#         "tool": "disable_user",
#         "function_args": {
#             "account_name": account
#         }
#     })
#     result.raise_for_status()
#     print(result)
# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def calculate_confidence_score(
    kql_results:          list,
    ipqs:                 dict | None,
    hypotheses:           dict,
    account:              str  = "",
    log_gap_detected:     bool = False,
    incident_severity:    str  = "medium",
    agent_recommends_block: bool = False,
) -> dict:
    """
    Returns a dict with:
      - confidence_score      (1.0 – 10.0)
      - breakdown             (per-component details)
      - raw_score
      - should_block          (bool  — decision, not a score input)
      - block_reason          (str   — human-readable explanation)
    """
    score     = 0.0
    breakdown = {}

    # ── 1. KQL Evidence Quality (0 – 5 pts) ────────────────────────────────
    total_queries = len(kql_results)
    if total_queries > 0:
        queries_with_hits  = sum(1 for q in kql_results if q.get("row_count", 0) > 0)
        hypothesis_matches = sum(1 for q in kql_results if q.get("matched_hypothesis", False))
        hit_ratio          = queries_with_hits  / total_queries
        match_ratio        = hypothesis_matches / total_queries
        kql_score          = round((hit_ratio * 2.5) + (match_ratio * 2.5), 2)
    else:
        kql_score = 0.0

    # When known log gaps exist, don't punish the score below a floor —
    # absence of telemetry ≠ absence of threat.
    if log_gap_detected:
        kql_score = max(kql_score, 1.5)

    score += kql_score
    breakdown["kql_evidence"] = {
        "score":             kql_score,
        "max":               5.0,
        "log_gap_detected":  log_gap_detected,
        "note": (
            "KQL score floored at 1.5 due to documented log gaps."
            if log_gap_detected and kql_score == 1.5
            else None
        ),
    }

    # ── 2. IPQS IP Reputation (0 – 2 pts) ──────────────────────────────────
    if ipqs is None:
        ipqs_score = 0.0
    else:
        fraud_score = ipqs.get("fraud_score", 0)
        is_tor      = ipqs.get("tor",   False)
        is_proxy    = ipqs.get("proxy", False)

        if is_tor or fraud_score >= 85:
            ipqs_score = 2.0
        elif is_proxy or fraud_score >= 60:
            ipqs_score = 1.5
        elif fraud_score >= 30:
            ipqs_score = 1.0
        else:
            ipqs_score = 0.5

    score += ipqs_score
    breakdown["ipqs_reputation"] = {"score": ipqs_score, "max": 2.0}

    # ── 3. Hypothesis Corroboration (0 – 2 pts) ────────────────────────────
    total_hyp     = hypotheses.get("total",     0)
    supported_hyp = hypotheses.get("supported", 0)
    hyp_score     = round((supported_hyp / total_hyp) * 2.0, 2) if total_hyp > 0 else 0.0

    score += hyp_score
    breakdown["hypothesis_corroboration"] = {"score": hyp_score, "max": 2.0}

    # ── 4. Grounding Score (0 – 1 pt) ──────────────────────────────────────
    grounding_pts = 0.95
    score        += grounding_pts
    breakdown["grounding"] = {"score": grounding_pts, "max": 1.0}

    # ── 5. Blast Radius / Account Sensitivity (0 – 1.5 pts) ────────────────
    # Captures privilege level of the compromised account — a Directory Sync
    # or admin account being compromised is far more dangerous than a regular
    # user, but that was not previously reflected in the score.
    privileged  = is_privileged_account(account)
    blast_score = 1.5 if privileged else 0.5
    score      += blast_score
    breakdown["blast_radius"] = {
        "score":        blast_score,
        "max":          1.5,
        "is_privileged": privileged,
        "account":       account or "(not provided)",
    }

    # ── Final score ─────────────────────────────────────────────────────────
    final_score = round(max(1.0, min(10.0, score)), 1)

    # ── Block Decision (separate from score, uses score as one input) ───────
    # The agent's recommendation acts as a threshold modifier rather than a
    # score inflator — avoids circular dependency while still honouring the
    # agent's reasoning.
    sev_rank       = SEVERITY_RANK.get(incident_severity.lower(), 0)
    high_or_above  = sev_rank >= SEVERITY_RANK["high"]
    threshold_key  = (agent_recommends_block, high_or_above)
    block_threshold = BLOCK_THRESHOLDS[threshold_key]
    should_block   = final_score >= block_threshold

    if should_block:
        block_reason = (
            f"Confidence score {final_score} meets or exceeds the block threshold "
            f"of {block_threshold} "
            f"(agent_recommends_block={agent_recommends_block}, "
            f"severity={incident_severity})."
        )
    else:
        block_reason = (
            f"Confidence score {final_score} is below the block threshold "
            f"of {block_threshold} "
            f"(agent_recommends_block={agent_recommends_block}, "
            f"severity={incident_severity}). Manual review recommended."
        )

    # sending  a request to disable the user
    # if should_block:
    #     disable_user(account)

    logger.info(
        "Block decision: should_block=%s, score=%.1f, threshold=%.1f, reason=%s",
        should_block, final_score, block_threshold, block_reason,
    )


    return {
        "confidence_score": final_score,
        "breakdown":        breakdown,
        "raw_score":        round(score, 2),
        "should_block":     should_block,
        "block_threshold":  block_threshold,
        "block_reason":     block_reason,
    }


# ---------------------------------------------------------------------------
# Lambda entry-point
# ---------------------------------------------------------------------------

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    action_group    = event.get("actionGroup",    "")
    api_path        = event.get("apiPath",        "")
    http_method     = event.get("httpMethod",     "POST")
    message_version = event.get("messageVersion", "1.0")

    try:
        parameters = event["requestBody"]["content"]["application/json"]["properties"]
        params     = {p["name"]: p["value"] for p in parameters}

        logger.info("Received params: %s", params)

        # ── Required params ─────────────────────────────────────────────────
        kql_results = json.loads(params["kql_results"])
        hypotheses  = parse_hypotheses(params["hypotheses"])

        # ── Optional IPQS ───────────────────────────────────────────────────
        ipqs_raw = params.get("ipqs", "null").strip()
        try:
            ipqs = json.loads(ipqs_raw)
        except json.JSONDecodeError:
            ipqs = None

        # ── New optional params (safe defaults keep old callers working) ────
        account                = params.get("account",                 "")
        log_gap_detected       = str(params.get("log_gap_detected",   "false")).lower() == "true"
        incident_severity      = params.get("incident_severity",       "medium")
        agent_recommends_block = str(params.get("agent_recommends_block", "false")).lower() == "true"

        result = calculate_confidence_score(
            kql_results           = kql_results,
            ipqs                  = ipqs,
            hypotheses            = hypotheses,
            account               = account,
            log_gap_detected      = log_gap_detected,
            incident_severity     = incident_severity,
            agent_recommends_block= agent_recommends_block,
        )

        logger.info("Confidence result: %s", result)

        return {
            "messageVersion": message_version,
            "response": {
                "actionGroup":    action_group,
                "apiPath":        api_path,
                "httpMethod":     http_method,
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(result)
                    }
                },
            },
        }

    except (KeyError, ValueError) as e:
        logger.error("Bad input: %s", str(e))
        return {
            "messageVersion": message_version,
            "response": {
                "actionGroup":    action_group,
                "apiPath":        api_path,
                "httpMethod":     http_method,
                "httpStatusCode": 400,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({"error": f"Bad input: {str(e)}"})
                    }
                },
            },
        }

    except Exception as e:
        logger.error("Handler error: %s", str(e))
        return {
            "messageVersion": message_version,
            "response": {
                "actionGroup":    action_group,
                "apiPath":        api_path,
                "httpMethod":     http_method,
                "httpStatusCode": 500,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps({"error": str(e)})
                    }
                },
            },
        }
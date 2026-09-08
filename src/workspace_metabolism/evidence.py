"""Read a bounded wm journal snapshot; emit counts, never raw business fields."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024
ACTIONS = {"audit", "govern", "clean", "rollback", "purge", "slim"}


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("invalid timestamp")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


def observe_followup(report: dict, path: Path) -> dict:
    """Associate a check in time only; never infer scope, causality or recovery."""
    result = {"status": "unavailable", "scope_match_verified": False,
              "business_recovery_verified": False, "source_sha256": None}
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            result["status"] = "over_budget"
            return result
        result["source_sha256"] = hashlib.sha256(data).hexdigest()
        observation = json.loads(data)
        if not isinstance(observation, dict) or type(observation.get("ok")) is not bool:
            raise ValueError("unsupported observation")
        checked = timestamp(observation.get("checked_at"))
        result.update(status="observation_only", checked_at=checked.isoformat(),
                      reported_ok=observation["ok"], relation="unknown")
        if report["evidence_status"] == "chain_consistent" and report.get("latest_record_at"):
            latest = timestamp(report["latest_record_at"])
            result["relation"] = "after_latest_record" if checked > latest else "not_after_latest_record"
        return result
    except OSError:
        return result
    except (ValueError, TypeError, RecursionError):
        result["status"] = "invalid"
        return result


def summarize(path: Path) -> dict:
    result = {
        "schema": "wm.case_evidence.v1",
        "evidence_status": "missing",
        "source_sha256": None,
        "entries": 0,
        "actions": {},
        "operation_observations": {},
        "business_recovery_verified": False,
        "coverage_verified": False,
        "supervision_minutes": None,
        "token_cost": None,
        "net_storage_savings_bytes": None,
        "independent_cases": None,
        "limitations": [
            "Journal entries are operations, not independent cases or completed tasks.",
            "Absent failure records do not prove absence of failures.",
            "Hash consistency does not authenticate the source or prove downstream recovery.",
        ],
    }
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
    except FileNotFoundError:
        return result
    except OSError:
        result["evidence_status"] = "unreadable"
        return result
    if len(data) > MAX_BYTES:
        result["evidence_status"] = "over_budget"
        return result
    result["source_sha256"] = hashlib.sha256(data).hexdigest()
    result["source_bytes"] = len(data)
    previous = "GENESIS"
    times = []
    invalid_times = 0
    counts, outcomes = Counter(), Counter()
    try:
        for line in data.decode("utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            if not isinstance(entry, dict):
                raise ValueError("entry must be object")
            if not counts and not {"seq", "hash", "prev_hash", "action"}.intersection(entry):
                result["evidence_status"] = "unsupported_format"
                return result
            seq = entry.get("seq")
            canonical = json.dumps(
                {k: v for k, v in entry.items() if k != "hash"},
                ensure_ascii=False, sort_keys=True,
            )
            digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if (type(seq) is not int or seq != sum(counts.values()) + 1
                    or entry.get("prev_hash") != previous or entry.get("hash") != digest):
                raise ValueError("invalid chain or sequence")
            previous = digest
            try:
                times.append(timestamp(entry.get("ts")))
            except ValueError:
                invalid_times += 1
            action = entry.get("action")
            action = action if isinstance(action, str) and action in ACTIONS else "other"
            counts[action] += 1
            if action == "govern":
                decision = entry.get("decision")
                outcome = "permission_denied" if decision == "deny" else "permission_recorded"
            elif action == "slim":
                status = entry.get("status")
                outcome = {"ok": "execution_reported_ok", "dry_run": "preview",
                           "error": "failure_reported", "failed": "failure_reported"}.get(
                               status if isinstance(status, str) else "", "unknown_outcome")
            else:
                outcome = "operation_recorded"
            outcomes[outcome] += 1
    except (UnicodeError, ValueError, TypeError, RecursionError):
        result["evidence_status"] = "invalid"
        # Never present a valid prefix as a complete or trustworthy observation.
        return result
    result.update(
        evidence_status="chain_consistent" if counts else "empty",
        entries=sum(counts.values()), actions=dict(sorted(counts.items())),
        operation_observations=dict(sorted(outcomes.items())),
        first_record_at=min(times).isoformat() if times and not invalid_times else None,
        latest_record_at=max(times).isoformat() if times and not invalid_times else None,
        invalid_timestamps=invalid_times,
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", type=Path)
    parser.add_argument("--observation", type=Path,
                        help="Read a check with checked_at (timezone required) and boolean ok; temporal association only")
    args = parser.parse_args()
    report = summarize(args.journal)
    if args.observation:
        report["followup"] = observe_followup(report, args.observation)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    valid = report["evidence_status"] == "chain_consistent"
    if args.observation:
        valid = valid and report["followup"]["status"] == "observation_only"
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())

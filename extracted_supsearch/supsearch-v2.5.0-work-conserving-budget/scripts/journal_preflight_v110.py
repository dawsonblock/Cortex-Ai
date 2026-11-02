#!/usr/bin/env python3
"""Strict local consistency check of the native Supsearch concept promotion log.

Not independent execution evidence. The journal and library may be forged together.
Run before attempting native learning or replay and use external task custody.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EVENTS = {"start", "promotion_intent", "promotion_committed", "candidate_trial",
          "train_attempt", "no_promotion", "dev_baseline_work", "round_work", "final_test_paired", "final_test", "session_completed"}


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _integer(v):
    return type(v) is int and v >= 0


def audit(ledger: Path, library: Path) -> dict:
    if ledger.is_symlink() or not ledger.is_file() or ledger.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("unsafe, absent or oversized journal")
    raw = ledger.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError("truncated journal line")
    lines = raw.decode("utf-8").splitlines()
    if not lines:
        raise ValueError("empty journal")
    pending = None
    latest = None
    session_count = None
    final = False
    paired = False
    names = set()
    commits = 0
    initial_baseline = None
    promoted = []
    session_active = False
    requires_completion = False
    for number, line in enumerate(lines, 1):
        if not line or len(line.encode()) > 16384:
            raise ValueError(f"line {number}: missing or oversized record")
        obj = json.loads(line, object_pairs_hook=_unique_pairs,
                         parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"invalid JSON constant {x}")))
        if type(obj) is not dict or type(obj.get("event")) is not str or obj["event"] not in EVENTS:
            raise ValueError(f"line {number}: invalid event")
        event = obj["event"]
        if event == "start":
            if pending is not None or not _integer(obj.get("initial_concepts")):
                raise ValueError("invalid session start")
            if session_active and requires_completion:
                raise ValueError("previous schema-v7 session unfinished")
            schema = obj.get("schema_version", 6)
            if not _integer(schema):
                raise ValueError("invalid schema version")
            if latest is not None and latest[3] != obj["initial_concepts"]:
                raise ValueError("session baseline differs from last commit")
            if initial_baseline is None:
                initial_baseline = obj["initial_concepts"]
            elif initial_baseline + len(promoted) != obj["initial_concepts"]:
                raise ValueError("journal concept-count continuity violation")
            session_active = True
            requires_completion = schema >= 7
            session_count = obj["initial_concepts"]
            final, paired = False, False
        elif event == "promotion_intent":
            name, term, arity = obj.get("name"), obj.get("term"), obj.get("arity")
            if (not session_active or session_count is None or final or pending is not None or not isinstance(name, str)
                or not name or name in names or not isinstance(term, str) or not term
                or not _integer(arity) or not 1 <= arity <= 5):
                raise ValueError("nested, late, or invalid intent")
            pending = name, term, arity
        elif event == "promotion_committed":
            if (pending is None or session_count is None or obj.get("name") != pending[0]
                or not _integer(obj.get("concept_count"))
                or obj["concept_count"] != session_count + 1):
                raise ValueError("orphan, mismatched or invalid commit")
            session_count += 1
            latest = (*pending, session_count)
            promoted.append(pending)
            names.add(pending[0]); commits += 1
            pending = None
        elif event in ("candidate_trial", "train_attempt", "no_promotion", "dev_baseline_work", "round_work"):
            if not session_active or session_count is None or final or pending is not None:
                raise ValueError("training event outside learning phase")
        elif event == "final_test_paired":
            if not session_active or session_count is None or paired or pending is not None:
                raise ValueError("misplaced paired final evaluation")
            paired = final = True
        elif event == "final_test":
            if not session_active or not final or pending is not None:
                raise ValueError("final row before paired result")
        elif event == "session_completed":
            if not session_active or not requires_completion or pending is not None:
                raise ValueError("orphan or duplicate session completion")
            if not _integer(obj.get("concept_count")) or obj["concept_count"] != session_count:
                raise ValueError("completion concept count mismatch")
            session_active = False
            requires_completion = False
    if pending is not None:
        raise ValueError("unreconciled native promotion intent")
    if session_active and requires_completion:
        raise ValueError("unfinished schema-v7 learning session")
    if initial_baseline is None:
        raise ValueError("journal has no start event")
    if library.is_symlink() or not library.is_file() or library.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("unsafe, absent or oversized concept library")
    concepts = []
    for row in library.read_text(encoding="utf-8").splitlines():
        if not row or row.startswith("#"):
            continue
        pieces = row.split("\t", 2)
        if len(pieces) != 3:
            raise ValueError("invalid concept library row")
        concepts.append((pieces[0], pieces[2], int(pieces[1])))
    expected = initial_baseline + len(promoted)
    if expected != len(concepts):
        raise ValueError("concept count disagrees with journal")
    if concepts[initial_baseline:] != promoted:
        raise ValueError("historical committed concept differs from library suffix")
    return {"status": "local_consistency_only", "commits": commits,
            "concept_count": len(concepts), "events": len(lines),
            "complete_session": not session_active,
            "baseline_not_attested": initial_baseline > 0,
            "warning": "neither cryptographic authenticity nor autonomous learning is established"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ledger", type=Path)
    p.add_argument("library", type=Path)
    a = p.parse_args()
    print(json.dumps(audit(a.ledger, a.library), sort_keys=True))


if __name__ == "__main__":
    main()

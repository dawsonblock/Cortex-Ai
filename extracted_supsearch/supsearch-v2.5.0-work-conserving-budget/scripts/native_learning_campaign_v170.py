#!/usr/bin/env python3
"""Run native v1.6 campaign and require v1.7 schema-8 cost reconciliation.

All v1.6 protections still apply; this adds evidence from the actual Rust
learning journal. Local execution is not independent source/binary attestation.
Python script doubles remain expressly non-native test fixtures.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
from native_learning_campaign_v160 import execute
from learning_work_audit_v170 import audit, amortization


def run(ns):
    report=execute(ns)
    learning_receipts=audit(ns.out_dir/'learn'/'journal.jsonl')
    outcome=amortization(learning_receipts,
        report['work_accounting']['final_built_all_baseline'],
        report['work_accounting']['final_built_all_learned'],1)
    result={'schema':'native-learning-campaign-v170',
        'qualification_scope':report['qualification_scope'],
        'rust_source_build_verified':False,
        'independent_holdout':False,
        'fully_amortized':False,
        'native_source_execution_verified':False,
        'learning_evidence':'unqualified_local_receipts' if report['native_binary_format_detected'] else 'test_double_only',
        'v160_report_sha256':__import__('hashlib').sha256((ns.out_dir/'report.json').read_bytes()).hexdigest(),
        'promotion_count':report['lineage']['native_mined_promotion_count_reported'],
        'paired_screen_passed':report['paired_screen_passed'],
        'measured_search_work':learning_receipts,
        'amortization':outcome}
    (ns.out_dir/'report-v170.json').write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('binary','learn-tasks','final-tasks','baseline-library','out-dir'):
        p.add_argument('--'+name,required=True,type=Path)
    for name in ('train','dev','final'):p.add_argument('--'+name,required=True)
    p.add_argument('--rounds',type=int,default=3)
    p.add_argument('--budget',type=float,default=1.)
    p.add_argument('--max-size',type=int,default=13)
    p.add_argument('--max-built',type=int,default=30000)
    p.add_argument('--fuel',type=int,default=20000)
    p.add_argument('--timeout',type=float,default=120.)
    p.add_argument('--min-gain',type=float,default=.1)
    p.add_argument('--max-regression',type=float,default=.15)
    p.add_argument('--allow-script-test-double',action='store_true')
    ns=p.parse_args(argv)
    try: result=run(ns)
    except (ValueError, OSError, UnicodeError, subprocess.SubprocessError) as e:
        p.exit(2,'v1.7 campaign unqualified: '+str(e)+'\n')
    print(json.dumps({'qualification_scope':result['qualification_scope'],
        'measured_search_built':result['measured_search_work']['accounted_search_expansions_lower_bound'],
        'net_savings_upper_bound':result['amortization']['net_search_expansion_savings_upper_bound']}))
    return 0

if __name__=='__main__':raise SystemExit(main())

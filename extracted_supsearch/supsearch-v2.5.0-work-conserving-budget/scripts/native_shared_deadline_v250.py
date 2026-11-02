#!/usr/bin/env python3
"""Run the bundled real Rust nonempty-concept probe with v2.5 shared deadline.

Native execution is required; the resulting receipt is NOT an unseen-task
transfer benchmark. A separately controlled final holdout remains necessary.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from native_reserved_fallback_v240 import run_native_probe
from shared_deadline_audit_v250 import audit


def run(binary: Path, source: Path, output: Path, timeout: int=90) -> dict:
    probe = run_native_probe(binary,source,output,timeout=timeout)
    time_report = audit(output/'native_probe.jsonl')
    if time_report['shared_time_budget'] is not True:
        raise ValueError('native probe did not enable v2.5 shared time budget')
    combined={'scope':'real native nonempty-library fallback smoke only',
              'native_probe':probe,'time_receipt_audit':time_report}
    (output/'v250_native_qualification.json').write_text(json.dumps(combined,indent=2,sort_keys=True)+'\n')
    return combined


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',type=Path,required=True)
    p.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--timeout',type=int,default=90)
    args=p.parse_args()
    try:
        print(json.dumps(run(args.binary,args.source,args.out,args.timeout),indent=2))
        return 0
    except (ValueError,OSError,RuntimeError) as e:
        print('v2.5 native deadline probe FAILED: '+str(e),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""WI-05: usr_rag 리플레이 사례로 datasets/replay_split.json 을 생성한다."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from utils.ga_search.replay import build_replay_split  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usr-rag-dir", default=str(REPO / "datasets" / "usr_rag"))
    parser.add_argument("--out", default=str(REPO / "datasets" / "replay_split.json"))
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--search-count", type=int, default=None)
    args = parser.parse_args()
    payload = build_replay_split(
        args.usr_rag_dir, args.out, seed=args.seed, search_count=args.search_count
    )
    print(f"written: {args.out}")
    print(f"unique cases: {payload['source']['unique_cases']}")
    print(f"search/holdout: {len(payload['search'])}/{len(payload['holdout'])}")
    if payload["source"]["skipped"]:
        print(f"skipped (gt 파싱 불가): {payload['source']['skipped']}")


if __name__ == "__main__":
    main()

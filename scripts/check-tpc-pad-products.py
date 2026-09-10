#!/usr/bin/env python3

import argparse

from podio import root_io


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--minimum-hits", type=int, default=1)
    args = parser.parse_args()

    frames = list(root_io.Reader(args.file).get("events"))
    if len(frames) != 1:
        raise RuntimeError(f"expected one event, found {len(frames)}")
    hits = frames[0].get("tpcPadsTpcPadHits")
    if len(hits) < args.minimum_hits:
        raise RuntimeError(
            f"expected at least {args.minimum_hits} TPC pad hits, found {len(hits)}"
        )
    for hit in hits:
        cell = hit.getCellID()
        pad = cell & 0xFF
        row = (cell >> 8) & 0x1F
        sector = (cell >> 13) & 0xF
        endcap = (cell >> 17) & 0x1
        if not (1 <= pad <= 144 and 1 <= row <= 16 and 1 <= sector <= 12):
            raise RuntimeError(f"invalid TPC pad cell ID: {cell}")
        if hit.getEDep() < 0 or endcap not in (0, 1):
            raise RuntimeError("invalid TPC pad-hit payload")
    print(f"TPC pad mapping closure passed: {len(hits)} mapped hits")


if __name__ == "__main__":
    main()

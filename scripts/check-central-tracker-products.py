#!/usr/bin/env python3

import argparse
from collections import Counter
from math import hypot

from podio import root_io


REGIONS_MM = {
    "VD": (50.0, 117.0),
    "ID": (117.0, 281.0),
    "TPC": (281.0, 1230.0),
    "OD": (1900.0, 2100.0),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--min-vd-hits", type=int, default=100)
    parser.add_argument("--min-id-hits", type=int, default=5)
    parser.add_argument("--min-tpc-hits", type=int, default=100)
    parser.add_argument("--min-od-hits", type=int, default=10)
    args = parser.parse_args()

    frames = list(root_io.Reader(args.file).get("events"))
    if len(frames) != 1:
        raise RuntimeError(f"expected one simulation event, found {len(frames)}")

    counts = Counter()
    unclassified = []
    for hit in frames[0].get("simSimTrackerHits"):
        position = hit.getPosition()
        radius = hypot(position.x, position.y)
        for name, (minimum, maximum) in REGIONS_MM.items():
            if minimum <= radius < maximum:
                counts[name] += 1
                break
        else:
            unclassified.append(radius)

    minimums = {
        "VD": args.min_vd_hits,
        "ID": args.min_id_hits,
        "TPC": args.min_tpc_hits,
        "OD": args.min_od_hits,
    }
    failures = {
        name: (counts[name], minimum)
        for name, minimum in minimums.items()
        if counts[name] < minimum
    }
    if failures or unclassified:
        raise RuntimeError(
            "central-tracker subsystem coverage failed: "
            f"counts={dict(counts)}, minimums={minimums}, "
            f"unclassified_radii_mm={unclassified[:10]}"
        )

    print(
        "Central-tracker transport closure passed: "
        + ", ".join(f"{name}={counts[name]}" for name in REGIONS_MM)
    )


if __name__ == "__main__":
    main()

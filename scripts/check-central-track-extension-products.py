#!/usr/bin/env python3

import argparse
from collections import Counter

from podio import root_io


ID_SIDE_BIT = 1 << 39
OD_SIDE_BIT = 1 << 31


def track_payload(track):
    return (
        track.getType(),
        track.getChi2(),
        track.getNdf(),
        track.getNholes(),
        tuple(
            (
                state.location,
                state.D0,
                state.phi,
                state.omega,
                state.Z0,
                state.tanLambda,
                state.time,
            )
            for state in track.getTrackStates()
        ),
        tuple(int(hit.getCellID()) for hit in track.getTrackerHits()),
    )


def payload(path, minimum_vd, minimum_id, minimum_tpc, minimum_od):
    frames = list(root_io.Reader(path).get("events"))
    if len(frames) != 1:
        raise RuntimeError(f"expected one event in {path}, found {len(frames)}")
    frame = frames[0]
    seeds = frame.get("centralTracksCentralTracks")
    tracks = frame.get("extendedCentralTracksExtendedCentralTracks")
    if len(tracks) != len(seeds) or not tracks:
        raise RuntimeError(
            f"track extension changed candidate count: {len(seeds)} -> {len(tracks)}"
        )

    result = []
    claimed = set()
    minimums = {1: minimum_vd, 2: minimum_id, 3: minimum_tpc, 4: minimum_od}
    for index, (seed, track) in enumerate(zip(seeds, tracks)):
        seed_payload = track_payload(seed)
        extended_payload = track_payload(track)
        if extended_payload[:5] != seed_payload[:5]:
            raise RuntimeError(f"extended track {index} changed the seed fit")
        seed_hits = seed_payload[5]
        hit_ids = extended_payload[5]
        if hit_ids[:len(seed_hits)] != seed_hits:
            raise RuntimeError(f"extended track {index} did not preserve TPC hits")

        counts = Counter({3: len(seed_hits)})
        counts.update(cell_id >> 56 for cell_id in hit_ids[len(seed_hits):])
        shortfall = {
            subsystem: (counts[subsystem], minimum)
            for subsystem, minimum in minimums.items()
            if counts[subsystem] < minimum
        }
        if shortfall:
            raise RuntimeError(
                f"extended track {index} has insufficient detector support: "
                f"counts={dict(counts)}, shortfall={shortfall}"
            )

        physical_id = {
            1: lambda cell_id: cell_id,
            2: lambda cell_id: cell_id & ~ID_SIDE_BIT,
            4: lambda cell_id: cell_id & ~OD_SIDE_BIT,
        }
        local = set()
        for cell_id in hit_ids[len(seed_hits):]:
            subsystem = cell_id >> 56
            if subsystem not in physical_id:
                raise RuntimeError(
                    f"extended track {index} acquired unknown hit {cell_id:#x}"
                )
            channel = (subsystem, physical_id[subsystem](cell_id))
            if channel in local:
                raise RuntimeError(
                    f"extended track {index} retained both drift hypotheses"
                )
            if channel in claimed:
                raise RuntimeError(
                    f"physical detector hit was shared by two tracks: {channel}"
                )
            local.add(channel)
            claimed.add(channel)
        result.append((extended_payload, tuple(sorted(counts.items()))))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--reference")
    parser.add_argument("--minimum-vd", type=int, default=1)
    parser.add_argument("--minimum-id", type=int, default=1)
    parser.add_argument("--minimum-tpc", type=int, default=20)
    parser.add_argument("--minimum-od", type=int, default=1)
    args = parser.parse_args()
    minimums = (
        args.minimum_vd,
        args.minimum_id,
        args.minimum_tpc,
        args.minimum_od,
    )
    result = payload(args.file, *minimums)
    if args.reference and result != payload(args.reference, *minimums):
        raise RuntimeError("central track extension is not deterministic")
    counts = result[0][1]
    print(f"Central track extension closure passed: {dict(counts)}")


if __name__ == "__main__":
    main()

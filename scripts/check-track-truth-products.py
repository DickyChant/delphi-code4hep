#!/usr/bin/env python3

import argparse
import math
from collections import defaultdict

from podio import root_io


def object_key(handle):
    object_id = handle.getObjectID()
    return (object_id.collectionID, object_id.index)


def payload(path, minimum_dominant_weight, expected_pdg):
    frames = list(root_io.Reader(path).get("events"))
    if len(frames) != 1:
        raise RuntimeError(f"expected one event in {path}, found {len(frames)}")
    frame = frames[0]
    tracks = frame.get("refittedCentralTracksRefittedCentralTracks")
    links = frame.get("trackTruthTrackMCParticleLinks")
    by_track = defaultdict(list)
    for link in links:
        track = link.getFrom()
        particle = link.getTo()
        if not track.isAvailable() or not particle.isAvailable():
            raise RuntimeError("track truth contains an unresolved relation")
        weight = link.getWeight()
        if not math.isfinite(weight) or weight < 0 or weight > 1:
            raise RuntimeError(f"track truth has invalid weight {weight}")
        by_track[object_key(track)].append((particle, weight))

    result = []
    for track in tracks:
        key = object_key(track)
        contributions = by_track.get(key, [])
        if not contributions:
            raise RuntimeError(f"track {key} has no truth attribution")
        total = sum(weight for _, weight in contributions)
        if abs(total - 1.0) > 1e-6:
            raise RuntimeError(f"track {key} truth weights sum to {total}")
        dominant, dominant_weight = max(
            contributions, key=lambda contribution: contribution[1]
        )
        if dominant_weight < minimum_dominant_weight:
            raise RuntimeError(
                f"track {key} dominant truth weight is only {dominant_weight}"
            )
        if expected_pdg and dominant.getPDG() != expected_pdg:
            raise RuntimeError(
                f"track {key} dominant PDG is {dominant.getPDG()}, "
                f"expected {expected_pdg}"
            )
        result.append(
            (
                key,
                tuple(
                    sorted(
                        (
                            object_key(particle),
                            particle.getPDG(),
                            weight,
                        )
                        for particle, weight in contributions
                    )
                ),
            )
        )
    if len(by_track) != len(tracks):
        raise RuntimeError("track truth refers to a foreign track")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--reference")
    parser.add_argument("--minimum-dominant-weight", type=float, default=0.95)
    parser.add_argument("--expected-pdg", type=int, default=13)
    args = parser.parse_args()
    result = payload(
        args.file, args.minimum_dominant_weight, args.expected_pdg
    )
    if args.reference and result != payload(
        args.reference, args.minimum_dominant_weight, args.expected_pdg
    ):
        raise RuntimeError("track truth attribution is not deterministic")
    dominant_weight = max(weight for _, _, weight in result[0][1])
    print(
        f"Track-truth closure passed: {len(result)} tracks, "
        f"dominant weight={dominant_weight:.6g}"
    )


if __name__ == "__main__":
    main()

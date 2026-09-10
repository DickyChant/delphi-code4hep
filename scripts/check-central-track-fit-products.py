#!/usr/bin/env python3

import argparse
import math

from podio import root_io


def payload(path, minimum_tracks, field_tesla, expected_pt_gev, pt_tolerance,
            expected_tan_lambda, tan_lambda_tolerance):
    frames = list(root_io.Reader(path).get("events"))
    if len(frames) != 1:
        raise RuntimeError(f"expected one event in {path}, found {len(frames)}")
    tracks = frames[0].get("centralTracksCentralTracks")
    if len(tracks) < minimum_tracks:
        raise RuntimeError(
            f"expected at least {minimum_tracks} central tracks, found {len(tracks)}"
        )
    result = []
    for track in tracks:
        states = list(track.getTrackStates())
        if len(states) != 1 or states[0].location != 1:
            raise RuntimeError("central seed does not have one AtIP state")
        state = states[0]
        parameters = (
            state.D0,
            state.phi,
            state.omega,
            state.Z0,
            state.tanLambda,
            state.time,
        )
        if not all(math.isfinite(value) for value in parameters):
            raise RuntimeError("central seed has a non-finite helix parameter")
        if state.omega == 0 or abs(state.D0) > 1e-6 or abs(state.Z0) > 1000:
            raise RuntimeError(f"central seed is not IP-compatible: {parameters}")
        pt_gev = 2.99792458e-4 * abs(field_tesla / state.omega)
        if abs(pt_gev - expected_pt_gev) > pt_tolerance * expected_pt_gev:
            raise RuntimeError(
                f"central seed pT {pt_gev} GeV is outside the closure window"
            )
        if abs(state.tanLambda - expected_tan_lambda) > tan_lambda_tolerance:
            raise RuntimeError(
                "central seed longitudinal slope is outside the closure window"
            )
        hits = list(track.getTrackerHits())
        rows = {(int(hit.getCellID()) >> 8) & 0x1F for hit in hits}
        if len(rows) < 8 or len(hits) < len(rows):
            raise RuntimeError("central seed has insufficient TPC row support")
        if track.getNdf() != 2 * len(rows) - 5 or track.getChi2() < 0:
            raise RuntimeError("central seed fit quality is inconsistent")
        if track.getType() != 1:
            raise RuntimeError("central seed is not marked IP-constrained")
        result.append(
            (
                track.getType(),
                track.getChi2(),
                track.getNdf(),
                track.getNholes(),
                parameters,
                tuple(int(hit.getCellID()) for hit in hits),
            )
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--minimum-tracks", type=int, default=1)
    parser.add_argument("--reference")
    parser.add_argument("--field-tesla", type=float, default=1.2312434)
    parser.add_argument("--expected-pt-gev", type=float, default=10.0)
    parser.add_argument("--pt-tolerance", type=float, default=0.30)
    parser.add_argument("--expected-tan-lambda", type=float, default=math.sinh(0.5))
    parser.add_argument("--tan-lambda-tolerance", type=float, default=0.05)
    args = parser.parse_args()
    validation = (
        args.field_tesla,
        args.expected_pt_gev,
        args.pt_tolerance,
        args.expected_tan_lambda,
        args.tan_lambda_tolerance,
    )
    result = payload(args.file, args.minimum_tracks, *validation)
    if args.reference and result != payload(args.reference, 1, *validation):
        raise RuntimeError("central helix fit is not deterministic")
    print(f"Central helix seed closure passed: {len(result)} tracks")


if __name__ == "__main__":
    main()

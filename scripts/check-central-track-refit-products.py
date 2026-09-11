#!/usr/bin/env python3

import argparse
import math

from podio import root_io


def state_payload(state):
    return (
        state.location,
        state.D0,
        state.phi,
        state.omega,
        state.Z0,
        state.tanLambda,
        state.time,
    )


def payload(path, field_tesla, expected_pt_gev, pt_tolerance,
            expected_tan_lambda, tan_lambda_tolerance):
    frames = list(root_io.Reader(path).get("events"))
    if len(frames) != 1:
        raise RuntimeError(f"expected one event in {path}, found {len(frames)}")
    frame = frames[0]
    seeds = frame.get("centralTracksCentralTracks")
    extended = frame.get("extendedCentralTracksExtendedCentralTracks")
    refitted = frame.get("refittedCentralTracksRefittedCentralTracks")
    if len(refitted) != len(extended) or len(refitted) != len(seeds) or not refitted:
        raise RuntimeError(
            "global refit changed the central-track candidate count"
        )

    result = []
    for index, (seed, source, track) in enumerate(zip(seeds, extended, refitted)):
        source_hits = tuple(int(hit.getCellID()) for hit in source.getTrackerHits())
        fitted_hits = tuple(int(hit.getCellID()) for hit in track.getTrackerHits())
        if fitted_hits != source_hits:
            raise RuntimeError(f"global refit changed track {index} hit ownership")
        states = list(track.getTrackStates())
        if len(states) != 1 or states[0].location != 1:
            raise RuntimeError(f"refitted track {index} lacks one AtIP state")
        state = states[0]
        parameters = state_payload(state)
        if not all(math.isfinite(value) for value in parameters):
            raise RuntimeError(f"refitted track {index} has non-finite parameters")
        if state.omega == 0 or abs(state.D0) > 1e-6:
            raise RuntimeError(f"refitted track {index} lost its IP constraint")
        pt_gev = 2.99792458e-4 * abs(field_tesla / state.omega)
        if abs(pt_gev - expected_pt_gev) > pt_tolerance * expected_pt_gev:
            raise RuntimeError(
                f"refitted track {index} pT {pt_gev} GeV misses closure"
            )
        if abs(state.tanLambda - expected_tan_lambda) > tan_lambda_tolerance:
            raise RuntimeError(
                f"refitted track {index} longitudinal slope misses closure"
            )
        seed_state = list(seed.getTrackStates())[0]
        seed_pt = 2.99792458e-4 * abs(field_tesla / seed_state.omega)
        if abs(pt_gev - expected_pt_gev) >= abs(seed_pt - expected_pt_gev):
            raise RuntimeError(
                f"global refit did not improve pT closure: {seed_pt} -> {pt_gev}"
            )
        if not math.isfinite(track.getChi2()) or track.getChi2() < 0 or track.getNdf() <= 0:
            raise RuntimeError(f"refitted track {index} has invalid fit quality")
        result.append(
            (
                track.getType(),
                track.getChi2(),
                track.getNdf(),
                track.getNholes(),
                parameters,
                fitted_hits,
            )
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--reference")
    parser.add_argument("--field-tesla", type=float, default=1.2312434)
    parser.add_argument("--expected-pt-gev", type=float, default=10.0)
    parser.add_argument("--pt-tolerance", type=float, default=0.20)
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
    result = payload(args.file, *validation)
    if args.reference and result != payload(args.reference, *validation):
        raise RuntimeError("central track global refit is not deterministic")
    state = result[0][4]
    pt_gev = 2.99792458e-4 * abs(args.field_tesla / state[3])
    print(
        f"Central track global-refit closure passed: "
        f"{len(result)} tracks, pT={pt_gev:.6g} GeV"
    )


if __name__ == "__main__":
    main()

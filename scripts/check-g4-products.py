#!/usr/bin/env python3

import argparse
from math import isclose

from podio import root_io


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--expected-field", type=float, default=0.1)
    parser.add_argument("--allow-empty-hits", action="store_true")
    parser.add_argument("--allow-empty-tracker-hits", action="store_true")
    parser.add_argument("--allow-empty-calorimeter-hits", action="store_true")
    parser.add_argument("--min-tracker-hits", type=int, default=1)
    parser.add_argument("--expected-primary-pdg", type=int)
    args = parser.parse_args()

    frames = list(root_io.Reader(args.file).get("events"))
    if len(frames) != 1:
        raise RuntimeError(f"expected one simulation event, found {len(frames)}")

    tracker_hits = frames[0].get("simSimTrackerHits")
    calorimeter_hits = frames[0].get("simSimCalorimeterHits")
    tracker_energy = sum(hit.getEDep() for hit in tracker_hits)
    tracker_path = sum(hit.getPathLength() for hit in tracker_hits)
    related_particles = [hit.getParticle() for hit in tracker_hits]
    missing_truth = sum(
        not particle.isAvailable() for particle in related_particles
    )
    wrong_truth = sum(
        particle.isAvailable()
        and args.expected_primary_pdg is not None
        and particle.getPDG() != args.expected_primary_pdg
        for particle in related_particles
    )
    calorimeter_energy = sum(hit.getEnergy() for hit in calorimeter_hits)
    magnetic_field = frames[0].get_parameter(
        "sim_detector_magneticFieldTesla"
    )

    if not (args.allow_empty_hits or args.allow_empty_tracker_hits) and (
        len(tracker_hits) < args.min_tracker_hits
        or tracker_energy <= 0
        or tracker_path <= 0
    ):
        raise RuntimeError(
            "simulation did not produce physical tracker-hit content"
        )
    if missing_truth or wrong_truth:
        expected = (
            ""
            if args.expected_primary_pdg is None
            else f"; expected primary PDG {args.expected_primary_pdg}"
        )
        raise RuntimeError(
            "simulation tracker-hit truth provenance is incomplete or wrong: "
            f"{missing_truth} missing relations, {wrong_truth} wrong relations"
            f"{expected}"
        )
    if not (args.allow_empty_hits or args.allow_empty_calorimeter_hits) and (
        len(calorimeter_hits) == 0 or calorimeter_energy <= 0
    ):
        raise RuntimeError(
            "simulation did not produce physical calorimeter-hit content"
        )
    if not isclose(
        magnetic_field, args.expected_field, rel_tol=0.0, abs_tol=1.0e-12
    ):
        raise RuntimeError(
            "simulation magnetic-field provenance is missing or wrong: "
            f"{magnetic_field}"
        )

    print(
        "Geant4 product closure passed: "
        f"{len(tracker_hits)} tracker hits, "
        f"{len(calorimeter_hits)} calorimeter hits, "
        f"{len(tracker_hits) - missing_truth} truth relations, "
        f"Bz={magnetic_field} T"
    )


if __name__ == "__main__":
    main()

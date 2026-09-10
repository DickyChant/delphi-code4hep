#!/usr/bin/env python3

import sys
from math import isclose

from podio import root_io


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} FILE.edm4hep.root")

    frames = list(root_io.Reader(sys.argv[1]).get("events"))
    if len(frames) != 1:
        raise RuntimeError(f"expected one simulation event, found {len(frames)}")

    tracker_hits = frames[0].get("simSimTrackerHits")
    calorimeter_hits = frames[0].get("simSimCalorimeterHits")
    tracker_energy = sum(hit.getEDep() for hit in tracker_hits)
    tracker_path = sum(hit.getPathLength() for hit in tracker_hits)
    calorimeter_energy = sum(hit.getEnergy() for hit in calorimeter_hits)
    magnetic_field = frames[0].get_parameter(
        "sim_detector_magneticFieldTesla"
    )

    if len(tracker_hits) == 0 or tracker_energy <= 0 or tracker_path <= 0:
        raise RuntimeError(
            "simulation did not produce physical tracker-hit content"
        )
    if len(calorimeter_hits) == 0 or calorimeter_energy <= 0:
        raise RuntimeError(
            "simulation did not produce physical calorimeter-hit content"
        )
    if not isclose(magnetic_field, 0.1, rel_tol=0.0, abs_tol=1.0e-12):
        raise RuntimeError(
            "simulation magnetic-field provenance is missing or wrong: "
            f"{magnetic_field}"
        )

    print(
        "Geant4 product closure passed: "
        f"{len(tracker_hits)} tracker hits, "
        f"{len(calorimeter_hits)} calorimeter hits, "
        f"Bz={magnetic_field} T"
    )


if __name__ == "__main__":
    main()

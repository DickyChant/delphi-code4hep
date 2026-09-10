#!/usr/bin/env python3

import argparse
import math

from podio import root_io


def payload(path):
    frames = list(root_io.Reader(path).get("events"))
    if len(frames) != 1:
        raise RuntimeError(f"expected one event in {path}, found {len(frames)}")
    digis = frames[0].get("tpcDigisTpcDigis")
    result = []
    for digi in digis:
        cell = digi.getCellID()
        pad = cell & 0xFF
        row = (cell >> 8) & 0x1F
        sector = (cell >> 13) & 0xF
        samples = tuple(digi.getAmplitude())
        if not (1 <= pad <= 144 and 1 <= row <= 16 and 1 <= sector <= 12):
            raise RuntimeError(f"invalid TPC digi cell ID: {cell}")
        if not math.isfinite(digi.getTime()) or not math.isclose(
            digi.getInterval(), 73.82, rel_tol=0, abs_tol=1e-3
        ):
            raise RuntimeError("invalid TPC digi timing")
        if not samples or any(value < 0 or value > 255 for value in samples):
            raise RuntimeError("invalid TPC FADC payload")
        if not any(value >= 20 for value in samples):
            raise RuntimeError("zero-suppressed TPC cluster has no threshold sample")
        result.append((cell, digi.getTime(), digi.getInterval(), samples))
    hits = frames[0].get("tpcHitsTpcHits")
    if len(hits) != len(digis):
        raise RuntimeError(
            f"TPC waveform/hit count mismatch: {len(digis)} != {len(hits)}"
        )
    hit_result = []
    waveform_cells = {entry[0] for entry in result}
    for hit in hits:
        raw_position = hit.getPosition()
        position = (raw_position[0], raw_position[1], raw_position[2])
        radius = math.hypot(position[0], position[1])
        if not (300 < radius < 1200 and abs(position[2]) <= 1450):
            raise RuntimeError(f"invalid reconstructed TPC position: {position}")
        if hit.getCellID() not in waveform_cells:
            raise RuntimeError("reconstructed TPC hit has no waveform")
        if not math.isfinite(hit.getTime()):
            raise RuntimeError("invalid reconstructed TPC hit time")
        covariance = hit.getCovMatrix()
        hit_result.append(
            (
                hit.getCellID(),
                hit.getTime(),
                position,
                tuple(covariance[index] for index in range(6)),
            )
        )
    return result, hit_result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--minimum-digis", type=int, default=1)
    parser.add_argument("--reference")
    args = parser.parse_args()

    digis, hits = payload(args.file)
    if len(digis) < args.minimum_digis:
        raise RuntimeError(
            f"expected at least {args.minimum_digis} TPC digis, found {len(digis)}"
        )
    if args.reference and (digis, hits) != payload(args.reference):
        raise RuntimeError(
            "TPC digitization/reconstruction is not reproducible for the fixed seed"
        )
    print(
        f"TPC digitization closure passed: {len(digis)} waveforms, "
        f"{len(hits)} reconstructed hits"
    )


if __name__ == "__main__":
    main()

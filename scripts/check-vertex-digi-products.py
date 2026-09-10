#!/usr/bin/env python3

import argparse
import math

from podio import root_io


def validated_payload(path, minimum_digis):
    frames = list(root_io.Reader(path).get("events"))
    if len(frames) != 1:
        raise RuntimeError(
            f"expected one event in {path}, found {len(frames)}"
        )
    frame = frames[0]
    digis = frame.get("vertexDigisVertexDigis")
    if len(digis) < minimum_digis:
        raise RuntimeError(
            f"expected at least {minimum_digis} VD digis, found {len(digis)}"
        )

    payload = []
    for digi in digis:
        cell = int(digi.getCellID())
        subsystem = cell >> 56
        sensor = (cell >> 32) & 0x00FFFFFF
        side = (cell >> 31) & 1
        strip = cell & 0x7FF
        adc = tuple(digi.getAdcCounts())
        if subsystem != 1 or not (1 <= sensor <= 288):
            raise RuntimeError(f"invalid VD sensor cell ID: {cell}")
        if side not in (0, 1) or not (1 <= strip <= 1280):
            raise RuntimeError(f"invalid VD strip cell ID: {cell}")
        if len(adc) != 1 or not (1 <= adc[0] <= 0x1FFF):
            raise RuntimeError(f"invalid VD quarter-ADC payload: {adc}")
        if not (0 <= digi.getQuality() <= 255):
            raise RuntimeError("invalid VD packed noise calibration")
        if not math.isfinite(digi.getTime()) or digi.getCharge() <= 0:
            raise RuntimeError("invalid VD charge or timing")
        if digi.getInterval() != 0:
            raise RuntimeError("integrated VD digit unexpectedly has an interval")
        payload.append((cell, digi.getTime(), digi.getCharge(), adc[0]))

    hits = frame.get("vertexHitsVertexHits")
    if len(hits) != len(digis):
        raise RuntimeError(
            f"VD digit/hit count mismatch: {len(digis)} != {len(hits)}"
        )
    digit_cells = {entry[0] for entry in payload}
    hit_payload = []
    for hit in hits:
        position = hit.getPosition()
        radius = math.hypot(position[0], position[1])
        if not (50 < radius < 120) or abs(position[2]) > 130:
            raise RuntimeError(f"invalid reconstructed VD position: {position}")
        if hit.getDu() <= 0 or hit.getDv() <= hit.getDu():
            raise RuntimeError("invalid reconstructed VD measurement errors")
        if hit.getCellID() not in digit_cells:
            raise RuntimeError("reconstructed VD hit has no digit")
        hit_payload.append(
            (
                int(hit.getCellID()),
                hit.getTime(),
                (position[0], position[1], position[2]),
                (hit.getU()[0], hit.getU()[1]),
                (hit.getV()[0], hit.getV()[1]),
                hit.getDu(),
                hit.getDv(),
            )
        )

    links = frame.get("vertexHitsVertexHitSimTrackerHitLinks")
    truth_by_hit = {}
    truth_payload = []
    for link in links:
        hit = link.getFrom()
        sim_hit = link.getTo()
        weight = link.getWeight()
        if not hit.isAvailable() or not sim_hit.isAvailable():
            raise RuntimeError("unresolved VD reconstructed-hit truth link")
        if not sim_hit.getParticle().isAvailable():
            raise RuntimeError("VD digit truth points to an unlabelled simulated hit")
        if not math.isfinite(weight) or weight <= 0 or weight > 1:
            raise RuntimeError(f"invalid VD truth-link weight: {weight}")
        index = hit.getObjectID().index
        truth_by_hit[index] = truth_by_hit.get(index, 0.0) + weight
        truth_payload.append((index, sim_hit.getObjectID().index, weight))

    if set(truth_by_hit) != set(range(len(hits))):
        raise RuntimeError("VD truth links do not cover every reconstructed hit")
    for index, weight in truth_by_hit.items():
        if not math.isclose(weight, 1.0, rel_tol=0, abs_tol=1e-5):
            raise RuntimeError(
                f"VD truth weights for hit {index} sum to {weight}"
            )

    return payload, hit_payload, truth_payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--minimum-digis", type=int, default=1)
    parser.add_argument("--reference")
    args = parser.parse_args()

    payload = validated_payload(args.file, args.minimum_digis)
    if args.reference and payload != validated_payload(args.reference, 1):
        raise RuntimeError(
            "VD digitization/reconstruction is not reproducible for the fixed seed"
        )
    print(
        f"VD digitization closure passed: {len(payload[0])} digits, "
        f"{len(payload[1])} reconstructed hits, {len(payload[2])} truth links"
    )


if __name__ == "__main__":
    main()

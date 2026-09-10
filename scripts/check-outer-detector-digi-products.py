#!/usr/bin/env python3

import argparse
import math

from podio import root_io


SUBSYSTEM = 4
SIDE_BIT = 1 << 31
CHANNEL_MASK = 0xFFFF_FFFF_0000_0000
HIT_MASK = CHANNEL_MASK | SIDE_BIT
FIRST_COLUMN = (2, 3, 2, 1, 0)
LAST_COLUMN = (30, 31, 29, 29, 29)


def channel_address(cell):
    if cell >> 56 != SUBSYSTEM or cell & ~CHANNEL_MASK:
        raise RuntimeError(f"invalid OD channel cell ID: {cell}")
    plank = (cell >> 48) & 0xFF
    layer = (cell >> 40) & 0xFF
    column = (cell >> 32) & 0xFF
    if not (
        1 <= plank <= 24
        and 1 <= layer <= 5
        and FIRST_COLUMN[layer - 1] <= column <= LAST_COLUMN[layer - 1]
    ):
        raise RuntimeError(f"invalid OD physical address: {cell}")
    return plank, layer, column


def hit_address(cell):
    if cell >> 56 != SUBSYSTEM or cell & ~HIT_MASK:
        raise RuntimeError(f"invalid OD hit cell ID: {cell}")
    plank, layer, column = channel_address(cell & ~SIDE_BIT)
    return plank, layer, column, (cell >> 31) & 1


def validated_payload(path, minimum_digis):
    frames = list(root_io.Reader(path).get("events"))
    if len(frames) != 1:
        raise RuntimeError(f"expected one event in {path}, found {len(frames)}")
    frame = frames[0]
    digis = frame.get("outerDetectorDigisOuterDetectorDigis")
    if len(digis) < minimum_digis:
        raise RuntimeError(
            f"expected at least {minimum_digis} OD digis, found {len(digis)}"
        )

    digit_payload = []
    digit_channels = set()
    for digi in digis:
        cell = int(digi.getCellID())
        channel_address(cell)
        words = tuple(digi.getAdcCounts())
        if len(words) != 4 or any(word < 0 for word in words):
            raise RuntimeError(f"invalid OD physical-channel payload: {words}")
        if digi.getQuality() != 1 or digi.getCharge() != 0:
            raise RuntimeError("unexpected OD payload version or charge")
        if not math.isclose(digi.getInterval(), 0.001, abs_tol=1e-8):
            raise RuntimeError("invalid OD payload time unit")
        if not math.isfinite(digi.getTime()):
            raise RuntimeError("invalid OD raw leading time")
        z_cm = (words[1] - 300000) * 0.001
        angle = (words[2] - 4000000) * 0.000001
        if not (-227.251 <= z_cm <= 227.251) or abs(angle) >= math.pi:
            raise RuntimeError("invalid OD calibrated z or drift angle")
        digit_channels.add(cell)
        digit_payload.append((cell, digi.getTime(), digi.getInterval(), words))

    hits = frame.get("outerDetectorHitsOuterDetectorHits")
    if len(hits) != 2 * len(digis):
        raise RuntimeError("OD reconstruction did not emit both ambiguities")
    hit_payload = []
    reconstructed_channels = set()
    for hit in hits:
        cell = int(hit.getCellID())
        plank, layer, column, side = hit_address(cell)
        channel = cell & ~SIDE_BIT
        if channel not in digit_channels:
            raise RuntimeError("OD hit has no physical-channel digit")
        if hit.getType() != side or hit.getQuality() != 0:
            raise RuntimeError("OD hit ambiguity metadata is inconsistent")
        position = hit.getPosition()
        xyz = (position[0], position[1], position[2])
        radius = math.hypot(xyz[0], xyz[1])
        if not (1900 <= radius <= 2150 and abs(xyz[2]) <= 2272.6):
            raise RuntimeError(f"invalid reconstructed OD position: {xyz}")
        if not math.isclose(hit.getDu(), 0.1, abs_tol=1e-6):
            raise RuntimeError("invalid OD transverse uncertainty")
        if not math.isclose(hit.getDv(), 54.9, abs_tol=1e-4):
            raise RuntimeError("invalid OD longitudinal uncertainty")
        reconstructed_channels.add(channel)
        hit_payload.append(
            (cell, plank, layer, column, side, hit.getTime(), xyz,
             (hit.getU()[0], hit.getU()[1]),
             (hit.getV()[0], hit.getV()[1]), hit.getDu(), hit.getDv())
        )
    if reconstructed_channels != digit_channels:
        raise RuntimeError("OD digits and reconstructed-hit channels differ")

    links = frame.get("outerDetectorHitsOuterDetectorHitSimTrackerHitLinks")
    truth_by_hit = {}
    truth_payload = []
    for link in links:
        hit = link.getFrom()
        sim_hit = link.getTo()
        if not hit.isAvailable() or not sim_hit.isAvailable():
            raise RuntimeError("unresolved OD reconstructed-hit truth link")
        if not sim_hit.getParticle().isAvailable():
            raise RuntimeError("OD truth points to an unlabelled simulated hit")
        index = hit.getObjectID().index
        truth_by_hit[index] = truth_by_hit.get(index, 0.0) + link.getWeight()
        truth_payload.append((index, sim_hit.getObjectID().index, link.getWeight()))
    if set(truth_by_hit) != set(range(len(hits))):
        raise RuntimeError("OD truth links do not cover every reconstructed hit")
    if any(not math.isclose(weight, 1.0, abs_tol=1e-5)
           for weight in truth_by_hit.values()):
        raise RuntimeError("OD truth weights do not sum to one")
    return digit_payload, hit_payload, truth_payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--minimum-digis", type=int, default=1)
    parser.add_argument("--reference")
    args = parser.parse_args()
    payload = validated_payload(args.file, args.minimum_digis)
    if args.reference and payload != validated_payload(args.reference, 1):
        raise RuntimeError("OD response is not reproducible for the fixed seed")
    print(
        f"OD response closure passed: {len(payload[0])} digits, "
        f"{len(payload[1])} ambiguity hypotheses, {len(payload[2])} truth links"
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import argparse
import math

from podio import root_io


SUBSYSTEM = 2
SIDE_BIT = 1 << 39
CHANNEL_MASK = 0xFFFF_FF00_0000_0000
HIT_MASK = 0xFFFF_FF80_0000_0000
TDC_INTERVAL_NS = 1000.0 / ((351.0 / 3.0) * 4.0)


def channel_address(cell):
    if cell >> 56 != SUBSYSTEM or cell & ~CHANNEL_MASK:
        raise RuntimeError(f"invalid ID jet channel cell ID: {cell}")
    sector = (cell >> 48) & 0xFF
    wire = (cell >> 40) & 0xFF
    if not (1 <= sector <= 24 and 1 <= wire <= 24):
        raise RuntimeError(f"invalid ID jet channel address: {cell}")
    return sector, wire


def hit_address(cell):
    if cell >> 56 != SUBSYSTEM or cell & ~HIT_MASK:
        raise RuntimeError(f"invalid ID jet hit cell ID: {cell}")
    sector = (cell >> 48) & 0xFF
    wire = (cell >> 40) & 0xFF
    side = (cell >> 39) & 1
    if not (1 <= sector <= 24 and 1 <= wire <= 24):
        raise RuntimeError(f"invalid ID jet hit address: {cell}")
    return sector, wire, side


def wrapped_angle(value):
    return (value + math.pi) % (2.0 * math.pi) - math.pi


def validated_payload(path, minimum_digis):
    frames = list(root_io.Reader(path).get("events"))
    if len(frames) != 1:
        raise RuntimeError(f"expected one event in {path}, found {len(frames)}")
    frame = frames[0]

    digis = frame.get("innerDetectorDigisInnerDetectorJetDigis")
    if len(digis) < minimum_digis:
        raise RuntimeError(
            f"expected at least {minimum_digis} ID jet digis, found {len(digis)}"
        )

    digit_payload = []
    digit_channels = set()
    for digi in digis:
        cell = int(digi.getCellID())
        channel_address(cell)
        adc = tuple(digi.getAdcCounts())
        if len(adc) != 1 or not (0 <= adc[0] <= 0x3FFF):
            raise RuntimeError(f"invalid ID 14-bit TDC payload: {adc}")
        if digi.getQuality() != 0 or digi.getCharge() != 0:
            raise RuntimeError("unexpected ID digit quality or charge")
        if not math.isfinite(digi.getTime()):
            raise RuntimeError("invalid ID digit time")
        if not math.isclose(
            digi.getInterval(), TDC_INTERVAL_NS, rel_tol=0, abs_tol=1e-5
        ):
            raise RuntimeError("invalid ID fine-TDC interval")
        digit_channels.add(cell)
        digit_payload.append(
            (
                cell,
                digi.getTime(),
                digi.getInterval(),
                digi.getQuality(),
                digi.getCharge(),
                adc[0],
            )
        )

    hits = frame.get("innerDetectorHitsInnerDetectorJetHits")
    hit_payload = []
    reconstructed_channels = set()
    for hit in hits:
        cell = int(hit.getCellID())
        sector, wire, side = hit_address(cell)
        channel = cell & ~SIDE_BIT
        if channel not in digit_channels:
            raise RuntimeError("reconstructed ID hit has no raw digit")
        if hit.getType() != side or hit.getQuality() != 0:
            raise RuntimeError("ID hit side or quality disagrees with its cell ID")
        position = hit.getPosition()
        xyz = (position[0], position[1], position[2])
        radius = math.hypot(xyz[0], xyz[1])
        if not (124.0 <= radius <= 218.0) or abs(xyz[2]) > 1e-8:
            raise RuntimeError(f"invalid reconstructed ID position: {xyz}")
        u = (hit.getU()[0], hit.getU()[1])
        v = (hit.getV()[0], hit.getV()[1])
        radial_phi = math.atan2(xyz[1], xyz[0])
        if not math.isclose(u[0], math.pi / 2.0, rel_tol=0, abs_tol=1e-6):
            raise RuntimeError("ID measured direction is not transverse")
        if abs(wrapped_angle(u[1] - radial_phi - math.pi / 2.0)) > 1e-6:
            raise RuntimeError("ID measured direction is not tangential")
        if abs(v[0]) > 1e-8 or abs(v[1]) > 1e-8:
            raise RuntimeError("ID unmeasured direction is not longitudinal")
        if not math.isclose(hit.getDu(), 0.1, rel_tol=0, abs_tol=1e-6):
            raise RuntimeError("invalid ID transverse measurement error")
        if not math.isclose(
            hit.getDv(), 800.0 / math.sqrt(12.0), rel_tol=0, abs_tol=1e-4
        ):
            raise RuntimeError("invalid ID longitudinal measurement error")
        if hit.getEDep() != 0 or hit.getEDepError() != 0:
            raise RuntimeError("ID drift hypothesis unexpectedly carries energy")
        if not math.isfinite(hit.getTime()):
            raise RuntimeError("invalid reconstructed ID drift time")
        reconstructed_channels.add(channel)
        hit_payload.append(
            (
                cell,
                sector,
                wire,
                side,
                hit.getTime(),
                xyz,
                u,
                v,
                hit.getDu(),
                hit.getDv(),
            )
        )

    if reconstructed_channels != digit_channels:
        missing = sorted(digit_channels - reconstructed_channels)
        raise RuntimeError(f"ID digits without reconstructed hypotheses: {missing}")

    links = frame.get(
        "innerDetectorHitsInnerDetectorHitSimTrackerHitLinks"
    )
    truth_by_hit = {}
    truth_payload = []
    for link in links:
        hit = link.getFrom()
        sim_hit = link.getTo()
        weight = link.getWeight()
        if not hit.isAvailable() or not sim_hit.isAvailable():
            raise RuntimeError("unresolved ID reconstructed-hit truth link")
        if not sim_hit.getParticle().isAvailable():
            raise RuntimeError("ID digit truth points to an unlabelled simulated hit")
        if not math.isfinite(weight) or weight <= 0 or weight > 1:
            raise RuntimeError(f"invalid ID truth-link weight: {weight}")
        index = hit.getObjectID().index
        truth_by_hit[index] = truth_by_hit.get(index, 0.0) + weight
        truth_payload.append((index, sim_hit.getObjectID().index, weight))

    if set(truth_by_hit) != set(range(len(hits))):
        raise RuntimeError("ID truth links do not cover every reconstructed hit")
    for index, weight in truth_by_hit.items():
        if not math.isclose(weight, 1.0, rel_tol=0, abs_tol=1e-5):
            raise RuntimeError(f"ID truth weights for hit {index} sum to {weight}")

    return digit_payload, hit_payload, truth_payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--minimum-digis", type=int, default=1)
    parser.add_argument("--reference")
    args = parser.parse_args()

    payload = validated_payload(args.file, args.minimum_digis)
    if args.reference and payload != validated_payload(args.reference, 1):
        raise RuntimeError(
            "ID digitization/reconstruction is not reproducible for the fixed seed"
        )
    print(
        f"ID jet digitization closure passed: {len(payload[0])} digits, "
        f"{len(payload[1])} ambiguity hypotheses, {len(payload[2])} truth links"
    )


if __name__ == "__main__":
    main()

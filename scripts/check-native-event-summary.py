#!/usr/bin/env python3

import sys

from podio import root_io


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} FILE.edm4hep.root")

    checked = 0
    reader = root_io.Reader(sys.argv[1])
    for event_index, frame in enumerate(reader.get("events")):
        charge_codes = [
            int(value)
            for value in frame.get("sDST_MAIN_Particles_ChargeCode")
        ]
        particles = frame.get("sDST_MAIN_Particles")
        if len(charge_codes) != particles.size():
            raise RuntimeError(
                f"event {event_index}: {len(charge_codes)} charge codes for "
                f"{particles.size()} particles"
            )

        expected_charged = sum(code != 0 for code in charge_codes)
        expected_neutral = sum(code == 0 for code in charge_codes)
        values = {
            "legacy charged": frame.get_parameter("sDST_EVT_nCharged"),
            "native charged": frame.get_parameter("native_EVT_nCharged"),
            "legacy neutral": frame.get_parameter("sDST_EVT_nNeutral"),
            "native neutral": frame.get_parameter("native_EVT_nNeutral"),
        }
        expected = {
            "legacy charged": expected_charged,
            "native charged": expected_charged,
            "legacy neutral": expected_neutral,
            "native neutral": expected_neutral,
        }
        if values != expected:
            raise RuntimeError(
                f"event {event_index}: particle-count closure failed: "
                f"got {values}, expected {expected}"
            )
        checked += 1

    if checked == 0:
        raise RuntimeError("input contains no event frames")
    print(f"native event-summary closure passed for {checked} event(s)")


if __name__ == "__main__":
    main()

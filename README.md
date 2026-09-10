# DELPHI Code4hep steering

This repository pins and builds the DELPHI DST to EDM4hep converter in the
[Code4hep](https://github.com/code4hep/Code4hep) workflow. Implementation stays
in its owning repositories; this repository records a known-compatible set and
the commands that join them.

## Current integration

| Component | Purpose |
| --- | --- |
| `DickyChant/code4hep-Code4hep` | Code4hep with native podio I/O utilities and optional DELPHI source |
| `DickyChant/delphi-edm4hep` | converter, `DelphiSource`, and SKELANA-free launcher |
| `DickyChant/code4hep-build` | Code4hep bootstrap with caller-supplied source hooks |

Exact revisions are in `versions.env`. They are commits rather than mutable
branch tips.

## Checkout and verify

```bash
./scripts/checkout.sh
./scripts/verify.sh
```

The default workspace is `sources/` under this checkout. Pass another directory
as the first argument to either command if desired.

## Full build

The full bootstrap is intentionally explicit because it compiles Code4hep and
its external dependencies:

```bash
./scripts/build.sh
```

The script sources `/cvmfs/delphi.cern.ch/setup.sh`, checks out the locked
revisions, and delegates dependency construction to Code4hep's own `setup.sh`.
Set `DELPHI_SETUP` to use another DELPHI setup script. Build products live next
to the three source checkouts under `sources/`.

The resulting converter executables and native `delphiRun` launcher are in
`sources/Code4hep/build_Code4hep/delphi_edm4hep/`. Code4hep's ordinary build is
unchanged when no converter source is supplied.

## Native conversion

`DelphiSource` runs the PHDST reader and conversion pipeline behind a Stitched
input source, then publishes each podio collection as a framework product. The
matching `PodioOutputModule` restores the original collection names and generic
frame parameters. A ready-to-use configuration is in
`steering/delphi_convert_cfg.py`:

```bash
export DELPHI_INPUT=/path/to/input.fadana
export DELPHI_OUTPUT=/path/to/output.root
export DELPHI_IS_REAL_DATA=false
export DELPHI_MAX_EVENTS=10
sources/Code4hep/build_Code4hep/delphi_edm4hep/delphiRun \
  steering/delphi_convert_cfg.py
```

The source is single-threaded at the legacy PHDST boundary. Set
`DELPHI_INPUT_MODE` to `nickname` or `pdl` when appropriate, and
`DELPHI_CONVERSION_PASS=fdst` plus path-separated
`DELPHI_INTERMEDIATE_FILES` for pass 2.

The steering also schedules `DelphiEventSummaryProducer`, the first derived
DELPHI calculation moved beyond the source boundary. It consumes the immutable
PA.MAIN charge-code collection and publishes `native_EVT_nCharged` and
`native_EVT_nNeutral` as normal Frame parameters. CI checks both values against
the legacy event summary on every fixture event.

The locked Code4hep revision also has a runnable Geant4 path. Its generator is
seeded without the unavailable CMSSW RNG service, `G4SimProducer` publishes
`SimTrackerHitCollection` and `SimCalorimeterHitCollection`, and CI validates
non-empty physical hit content with the bundled one-muon GDML example. The
magnetic field is explicit configuration and is persisted as
`sim_detector_magneticFieldTesla`.

The DELPHI side now has a dependency-free C++ parser for the authoritative
CARGO/DDAPP simulation snapshot. CI reads the pinned v94c snapshot and checks
its 11,265 records, including 7,703 geometry and 202 material records. The next
simulation slice is translating those parsed `SHAP`/`REFR`/`MATS`/`REPL`
directives into modern geometry and adding detector-specific digitizers; the
bundled GDML remains a framework test, not a DELPHI detector model.

## Scope

This integration removes the runtime SKELANA lifecycle from the native path.
`delphiRun` links no `libskelanaxx` and contains no `PSINI`/`PSBEG`. Dataset
version, magnetic field, beamspot, BTAG inputs, and the short-DST secondary
interaction repair are called directly by the conversion pipeline. The CI job
builds the real Code4hep/Stitched source, tests collection/metadata round trips,
registers `DelphiSource`, and audits the final launcher link.

The remaining legacy dependency is PHDST/DSTANA itself; removing that would be
a separate raw-bank reader rewrite, not a SKELANA refactor. Design and
validation evidence are documented in
`delphi-edm4hep/docs/no-skelana-migration.md`.

No pull request is created by any script in this repository.

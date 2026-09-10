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

The DELPHI side now has a dependency-free C++ parser and typed model for the
authoritative CARGO/DDAPP simulation snapshot. CI reads the pinned v94c
snapshot and requires complete decoding of 202 materials, 7,703 geometry
nodes, 6,220 shapes, 4,246 transforms, and 1,506 replacement paths. The next
simulation slice is now concrete: `delphi_geometry_export --beam-pipe` writes
the real 680 cm by 1,170 cm `/DELF.B` world plus all 106 source nodes in the
`/BEA*` hierarchy. It translates the subsystem's materials, nested cylindrical
and brick shapes, placements, and replacement-inherited mask children. CI
checks the exact expanded topology and transports one event through it at the
v94c 1.2312434 T central field. The same native renderer now adds all 81 TPC
nodes, translates its 36 `POL6` endplate sectors to closed tessellated solids,
and marks the gas volume tracker-sensitive. CI requires that authoritative
geometry to produce physical persistent tracker-hit content; calorimeter
geometry and detector digitizers are added incrementally. The same v94c CARGO
snapshot now defines the TPC readout boundary as well: 16 calibrated pad rows,
1,680 pads per sector, and all 12 sector transforms. A scheduled
`DelphiTpcPadMapperProducer` applies the legacy STAMPA pad-number convention to
Geant4 step positions and writes ordinary `TrackerHit3D` products. CI transports
one event through the DELPHI TPC, requires mapped pad hits with valid cell IDs,
and checks the authoritative 20,160-pad topology. This is geometrical channel
mapping. The framework-independent `TpcPadResponse` kernel also ports STAMPA's
deterministic induction onto five neighboring pads, including the v94c response
width, drift-distance, local-incidence, and Lorentz-angle terms. Primary
ionization, Landau fluctuations, diffusion in time, thresholds, and ADC
response remain the next TPC digitization layers. Native conditions decoding
already supplies those layers with the v94c high voltage, dE/dx and pad-gain
normalizations, both endcap drift velocities, and all packed sector gate
states directly from CARGO. It also expands the complete 20,160-channel packed
pad calibration into electronics channel, pedestal, two-range slope, gain
ratio, crossover, and status values. The native STDIPW response now adds
longitudinal diffusion, electronics shaping, the 73.82 ns clock, and the
13-sample asymmetric pulse window while accepting its random deviates
explicitly from the future scheduled digitizer.

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

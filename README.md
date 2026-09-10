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
`sim_detector_magneticFieldTesla`. Generator-primary identity is carried
through every Geant4 descendant, so each persistent `SimTrackerHit` has a
resolvable relation to its originating EDM4hep `MCParticle`; CI requires full
relation coverage and the expected primary PDG after ROOT readback.

The DELPHI side now has a dependency-free C++ parser and typed model for the
authoritative CARGO/DDAPP simulation snapshot. CI reads the pinned v94c
snapshot and requires complete decoding of 202 materials, 7,703 geometry
nodes, 6,220 shapes, 5,095 transforms, and 1,506 replacement paths. The next
simulation slice is now concrete: `delphi_geometry_export --beam-pipe` writes
the real 680 cm by 1,170 cm `/DELF.B` world plus all 106 source nodes in the
`/BEA*` hierarchy. It translates the subsystem's materials, nested cylindrical
and brick shapes, placements, and replacement-inherited mask children. CI
checks the exact expanded topology and transports one event through it at the
v94c 1.2312434 T central field. The same native renderer now adds all 81 TPC
nodes, translates its 36 `POL6` endplate sectors to closed tessellated solids,
and marks the two actual `ARM2` sensing volumes tracker-sensitive with the
legacy 0.4 cm wire-spacing step. CI requires that authoritative geometry to
produce physical persistent tracker-hit content; calorimeter
geometry and detector digitizers are added incrementally. The same v94c CARGO
snapshot now defines the TPC readout boundary as well: 16 calibrated pad rows,
1,680 pads per sector, and all 12 sector transforms. A scheduled
`DelphiTpcPadMapperProducer` applies the legacy STAMPA pad-number convention to
Geant4 step positions and writes ordinary `TrackerHit3D` products. CI transports
one event through the DELPHI TPC, requires mapped pad hits with valid cell IDs,
and checks the authoritative 20,160-pad topology. This is geometrical channel
mapping. The framework-independent `TpcPadResponse` kernel also ports STAMPA's
deterministic induction onto five neighboring pads, including the v94c response
width, drift-distance, local-incidence, and Lorentz-angle terms. Native wire
geometry now decodes all 192 sense wires per sector, their 0.4 cm pitch and
high-radius taper. The digitizer places Geant4 energy deposition on those
wires and ports STDEDX/STLAND's field-dependent adjacent-wire charge leakage
before pad induction. Geant4's fluctuated energy loss replaces the legacy
ETDEDX histogram sampler. Native conditions decoding
already supplies those layers with the v94c high voltage, dE/dx and pad-gain
normalizations, both endcap drift velocities, and all packed sector gate
states directly from CARGO. It also expands the complete 20,160-channel packed
pad calibration into electronics channel, pedestal, two-range slope, gain
ratio, crossover, and status values. The native STDIPW response now adds
longitudinal diffusion, electronics shaping, the 73.82 ns clock, and the
13-sample asymmetric pulse window while accepting its random deviates
explicitly from the future scheduled digitizer. The calibrated two-range FADC,
pedestal-noise decomposition, saturation, and legacy threshold window are now
native tested kernels as well. A scheduled `DelphiTpcDigitizerProducer`
aggregates the Geant4 steps per pad and time bin and writes the surviving
waveforms as EDM4hep `TimeSeries`. CI validates physical thresholded waveforms
and their DELPHI cell IDs, 73.82 ns clock, and 8-bit ADC range. A following
`DelphiTpcHitReconstructionProducer` converts each waveform peak back to a
calibrated pad-centre and drift-z `TrackerHit3D`, including channel quality and
position covariance. Charge-weighted simulated-hit provenance is carried
through an in-memory digitizer link and published at the reconstruction
boundary as the standard EDM4hep `TrackerHitSimTrackerHitLinkCollection`. CI
requires every reconstructed hit to have resolvable, unit-normalized truth
weights, and the repeated-run check compares waveforms, hits, and truth links
exactly.

The vertex detector is now transported from the same database rather than an
idealized cylinder. `delphi_geometry_export --vertex` decodes the 1,137-node
`/VD**` tree, including 508 `DUMY` assembly levels and the authoritative
12-value `MTRX` placements. All 288 `SI**` sensor volumes are tagged sensitive
with the native `STEPS=0.001 cm` limit. CI fixes the expanded topology and
requires a one-muon Geant4 event to produce persistent, truth-linked silicon
steps through those placed sensors.

The first VD response layer is also native. Release-matched VDSIM 4.6
conditions encode the v94c 24/24/24-module readout, odd/even inner P channels,
the closer two-pitch N zone, the outer N layouts, noise, thresholds and ADC
calibration. `VertexReadoutGeometry` binds them to all 288 semantic sensor IDs,
their P/N `MTRX` transforms and CARGO `USER` active lines. The snapshot audit
checks the full catalogue, all 319,488 v94c `SVELCH` electronics addresses,
and coordinate/cell-ID round trips. Strip charge sharing, raw digitization and
clustering remain the next VD slice.

The same renderer now completes the central-tracker transport boundary.
`--id` reconstructs the inner detector's DELPHI `FORB` cells, `--od`
reconstructs the outer detector's segmented hollow `POL4` layers, and
`--tracking` composes beam pipe, VD, ID, TPC, and OD into one detector. CI pins
the full 2,004-volume/2,559-placement topology and requires persistent,
truth-linked hits in all four tracking regions from one fixed transverse muon.
Each sensitive logical volume carries an explicit GDML `CellIDBase`; Code4hep
combines it with the physical copy number and persists that semantic ID instead
of exposing hit-collection ordering. CI requires the high byte to identify VD,
ID, TPC, or OD consistently with the transported hit position. A scheduled
`DelphiTrackerHitPartitionProducer` then publishes separate VD, ID, TPC, and OD
`SimTrackerHitCollection` products and CI checks that their full payload and MC
provenance survive the split.
This is not yet a claim of a complete native pipeline: only the TPC currently
has calibrated digitization and hit reconstruction. VD/ID/OD response,
tracking and vertex reconstruction, the non-tracking detectors, and the final
replacement of the PHDST/DSTANA input boundary remain.

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
`delphi-edm4hep/docs/no-skelana-migration.md`; the end-to-end replacement map
is in `delphi-edm4hep/docs/native-code4hep-pipeline.md`.

No pull request is created by any script in this repository.

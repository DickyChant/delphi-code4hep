# DELPHI Code4hep steering

This repository pins and builds the DELPHI DST to EDM4hep converter in the
[Code4hep](https://github.com/code4hep/Code4hep) workflow. Implementation stays
in its owning repositories; this repository records a known-compatible set and
the commands that join them.

## Current integration

| Component | Purpose |
| --- | --- |
| `DickyChant/code4hep-Code4hep` | Code4hep with optional `CODE4HEP_DELPHI_SOURCE_DIR` |
| `DickyChant/delphi-edm4hep` | converter made safe for `add_subdirectory` |
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

The resulting converter executables are in
`sources/Code4hep/build_Code4hep/delphi_edm4hep/`. Code4hep's ordinary build is
unchanged when no converter source is supplied.

## Scope

This integration builds the converter and its tests inside the Code4hep build.
The pinned DELPHI revision also contains the first direct event-service slice:
dataset version, magnetic field, beamspot, stored BTAG information, and event
summary values no longer need to be read from SKELANA COMMON blocks. Its design,
validation evidence, and remaining migration work are documented in
`delphi-edm4hep/docs/no-skelana-migration.md`.

This is not yet a claim that `libskelanaxx` can be removed. The converter still
uses `PSINI`/`PSBEG` and remaining SKELANA-backed reconstruction domains while
their ordering-sensitive behavior is split and validated. A later native
Code4hep `InputSource` can publish the resulting EDM4hep collections directly.

No pull request is created by any script in this repository.

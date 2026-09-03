#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
workspace=${1:-"${repo_root}/sources"}
delphi_setup=${DELPHI_SETUP:-/cvmfs/delphi.cern.ch/setup.sh}

"${repo_root}/scripts/checkout.sh" "${workspace}"
"${repo_root}/scripts/verify.sh" "${workspace}"

if [[ ! -r "${delphi_setup}" ]]; then
  echo "ERROR: DELPHI setup script is not readable: ${delphi_setup}" >&2
  exit 1
fi

# DELPHI must be first. Code4hep's bootstrap subsequently establishes CMSSW,
# Stitched, EDM4hep, podio, and ROOT.
# shellcheck disable=SC1090
set +u
source "${delphi_setup}"
set -u
export CODE4HEP_SOURCE_DIR="${workspace}/Code4hep"
export CODE4HEP_DELPHI_SOURCE_DIR="${workspace}/delphi-edm4hep/delphi_edm4hep"

cd "${workspace}/build"
./setup.sh

ctest --test-dir "${CODE4HEP_SOURCE_DIR}/build_Code4hep" --output-on-failure

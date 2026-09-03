#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=../versions.env
source "${repo_root}/versions.env"
workspace=${1:-"${repo_root}/sources"}
build_dir=${2:-"${repo_root}/build/embed-smoke"}

"${repo_root}/scripts/checkout.sh" "${workspace}"
"${repo_root}/scripts/verify.sh" "${workspace}"

set +u
source /cvmfs/delphi.cern.ch/setup.sh
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r "${KEY4HEP_TEST_RELEASE}"
set -u
unset CXXFLAGS CFLAGS LDFLAGS

cmake -S "${repo_root}/cmake/EmbedSmoke" -B "${build_dir}" \
  -DDELPHI_EDM4HEP_SOURCE_DIR="${workspace}/delphi-edm4hep/delphi_edm4hep"
cmake --build "${build_dir}" -j"${C4H_BUILD_CORES:-4}"
ctest --test-dir "${build_dir}" --output-on-failure

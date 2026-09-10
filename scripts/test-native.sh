#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=../versions.env
source "${repo_root}/versions.env"
workspace=${1:-"${repo_root}/sources"}
build_root=${2:-"${repo_root}/build/native-code4hep"}

"${repo_root}/scripts/checkout.sh" "${workspace}"
"${repo_root}/scripts/verify.sh" "${workspace}"

set +u
source /cvmfs/delphi.cern.ch/setup.sh
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r "${KEY4HEP_TEST_RELEASE}"
set -u
unset CXXFLAGS CFLAGS LDFLAGS

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "ERROR: required file is missing: $1" >&2
    exit 1
  fi
}

checkout_dependency() {
  local url=$1 ref=$2 commit=$3 destination=$4
  if [[ ! -d "${destination}/.git" ]]; then
    git clone --no-checkout --branch "${ref}" "${url}" "${destination}"
  fi
  if ! git -C "${destination}" cat-file -e "${commit}^{commit}" 2>/dev/null; then
    git -C "${destination}" fetch origin "${commit}"
  fi
  git -C "${destination}" checkout --detach "${commit}"
  local actual
  actual=$(git -C "${destination}" rev-parse HEAD)
  if [[ "${actual}" != "${commit}" ]]; then
    echo "ERROR: expected ${commit}, found ${actual} in ${destination}" >&2
    exit 1
  fi
}

mkdir -p "${build_root}"

md5_prefix=${C4H_MD5_PREFIX:-"${build_root}/c4h-md5-install"}
if [[ -z "${C4H_MD5_PREFIX:-}" ]]; then
  md5_source="${build_root}/c4h-md5-source"
  checkout_dependency "${C4H_MD5_URL}" "${C4H_MD5_REF}" \
    "${C4H_MD5_COMMIT}" "${md5_source}"
  cmake -S "${md5_source}" -B "${build_root}/c4h-md5-build" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="${md5_prefix}"
  cmake --build "${build_root}/c4h-md5-build" -j"${C4H_BUILD_CORES:-4}"
  cmake --install "${build_root}/c4h-md5-build"
fi
require_file "${md5_prefix}/lib64/cmake/c4h_md5/c4h_md5Config.cmake"

require_file "${STITCHED_TINYXML2_ROOT}/lib64/cmake/tinyxml2/tinyxml2Config.cmake"
require_file "${STITCHED_CPU_FEATURES_ROOT}/lib64/cmake/CpuFeatures/CpuFeaturesConfig.cmake"

stitched_prefix=${C4H_STITCHED_PREFIX:-"${build_root}/stitched-install"}
if [[ -z "${C4H_STITCHED_PREFIX:-}" ]]; then
  stitched_source="${build_root}/stitched-source"
  checkout_dependency "${STITCHED_URL}" "${STITCHED_REF}" \
    "${STITCHED_COMMIT}" "${stitched_source}"
  stitched_prefix_path="${md5_prefix};${STITCHED_TINYXML2_ROOT};${STITCHED_CPU_FEATURES_ROOT}"
  cmake -S "${stitched_source}" -B "${build_root}/stitched-build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="${stitched_prefix}" \
    -DCMAKE_PREFIX_PATH="${stitched_prefix_path}"
  cmake --build "${build_root}/stitched-build" -j"${C4H_BUILD_CORES:-4}"
  cmake --install "${build_root}/stitched-build"
fi
require_file "${stitched_prefix}/lib64/cmake/Stitched/StitchedConfig.cmake"
require_file "${stitched_prefix}/bin/stitched_env.sh"
require_file "${STITCHED_BOOST_ROOT}/lib/libboost_program_options.so"

# Plugin builds run Stitched executables to generate their Python configs, so
# the framework and Boost runtime paths must be active before building them.
set +u
# shellcheck disable=SC1090
source "${stitched_prefix}/bin/stitched_env.sh"
set -u
export LD_LIBRARY_PATH="${STITCHED_BOOST_ROOT}/lib:${LD_LIBRARY_PATH:-}"

# Pythia8 in the Key4hep stack has no CMake package.  Supply only the standard
# imported target expected by Code4hep, using pythia8-config as the authority.
pythia_prefix=$(pythia8-config --prefix)
pythia_library="${pythia_prefix}/lib/libpythia8.so"
if [[ ! -f "${pythia_library}" ]]; then
  pythia_library="${pythia_prefix}/lib64/libpythia8.so"
fi
require_file "${pythia_library}"
require_file "${pythia_prefix}/include/Pythia8/Pythia.h"
proxy_dir="${build_root}/cmake-proxies"
mkdir -p "${proxy_dir}"
sed \
  -e "s|@PYTHIA_LIBRARY@|${pythia_library}|g" \
  -e "s|@PYTHIA_INCLUDE@|${pythia_prefix}/include|g" \
  "${repo_root}/cmake/Pythia8Config.cmake.in" \
  > "${proxy_dir}/Pythia8Config.cmake"

code4hep_build="${build_root}/Code4hep-build"
code4hep_prefix_path="${proxy_dir};${stitched_prefix};${md5_prefix}"
cmake -S "${workspace}/Code4hep" -B "${code4hep_build}" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="${code4hep_prefix_path}" \
  -DStitched_DIR="${stitched_prefix}/lib64/cmake/Stitched" \
  -Dc4h_md5_DIR="${md5_prefix}/lib64/cmake/c4h_md5" \
  -DPythia8_DIR="${proxy_dir}" \
  -DCODE4HEP_DELPHI_SOURCE_DIR="${workspace}/delphi-edm4hep/delphi_edm4hep"

cmake --build "${code4hep_build}" -j"${C4H_BUILD_CORES:-4}" --target \
  IOUtilities \
  DataFormats \
  plugin_Code4hepDataFormatsPlugins \
  plugin_Code4hepIOPlugins \
  plugin_DelphiInputPlugins \
  delphi_cmsRun \
  bin_testCode4hepIOCatch2

plugin_dir="${code4hep_build}/lib"
export LD_LIBRARY_PATH="${plugin_dir}:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="${code4hep_build}/python:${PYTHONPATH:-}"

data_plugin="${plugin_dir}/edmpluginplugin_Code4hepDataFormatsPlugins.so"
io_plugin="${plugin_dir}/edmpluginplugin_Code4hepIOPlugins.so"
delphi_plugin="${plugin_dir}/edmpluginplugin_DelphiInputPlugins.so"
require_file "${data_plugin}"
require_file "${io_plugin}"
require_file "${delphi_plugin}"
edmPluginRefresh -p "${data_plugin}" "${io_plugin}" "${delphi_plugin}"
if ! grep -q 'DelphiSource' "${plugin_dir}/.edmplugincache"; then
  echo "ERROR: DelphiSource was not registered in the plugin cache" >&2
  exit 1
fi

"${code4hep_build}/Code4hep/IO/test/bin_testCode4hepIOCatch2"

launcher="${code4hep_build}/delphi_edm4hep/delphi_cmsRun"
require_file "${launcher}"
launcher_dependencies=$(ldd "${launcher}")
launcher_symbols=$(nm -D "${launcher}")
if grep -qi skelana <<< "${launcher_dependencies}"; then
  echo "ERROR: native launcher still links SKELANA" >&2
  exit 1
fi
if grep -Eq ' (psbeg_|psini_)$' <<< "${launcher_symbols}"; then
  echo "ERROR: native launcher still exports a SKELANA lifecycle entry point" >&2
  exit 1
fi
for symbol in phdst_ bpilot_ dstqid_ user00_ user01_ user02_ user99_; do
  if ! grep -Eq " ${symbol}$" <<< "${launcher_symbols}"; then
    echo "ERROR: native launcher is missing required legacy symbol ${symbol}" >&2
    exit 1
  fi
done

echo "Native DelphiSource build and SKELANA-free link audit passed"

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
  plugin_Code4hepGeneratorsPlugins \
  plugin_Code4hepG4ApplicationPlugins \
  plugin_Code4hepIOPlugins \
  plugin_DelphiInputPlugins \
  delphiRun \
  particle_counts_test \
  cargo_database_test \
  geometry_model_test \
  gdml_world_writer_test \
  gdml_beam_pipe_writer_test \
  tpc_digitization_conditions_test \
  tpc_pad_response_test \
  tpc_readout_geometry_test \
  delphi_geometry_audit \
  delphi_geometry_export \
  delphi_tpc_readout_audit \
  bin_testCode4hepG4SimProducerTP \
  bin_testCode4hepIOCatch2

plugin_dir="${code4hep_build}/lib"
export LD_LIBRARY_PATH="${plugin_dir}:${LD_LIBRARY_PATH:-}"
export PYTHONPATH="${code4hep_build}/python:${PYTHONPATH:-}"

data_plugin="${plugin_dir}/edmpluginplugin_Code4hepDataFormatsPlugins.so"
generator_plugin="${plugin_dir}/edmpluginplugin_Code4hepGeneratorsPlugins.so"
g4_plugin="${plugin_dir}/edmpluginplugin_Code4hepG4ApplicationPlugins.so"
io_plugin="${plugin_dir}/edmpluginplugin_Code4hepIOPlugins.so"
delphi_plugin="${plugin_dir}/edmpluginplugin_DelphiInputPlugins.so"
require_file "${data_plugin}"
require_file "${generator_plugin}"
require_file "${g4_plugin}"
require_file "${io_plugin}"
require_file "${delphi_plugin}"
edmPluginRefresh -p "${data_plugin}" "${generator_plugin}" "${g4_plugin}" \
  "${io_plugin}" "${delphi_plugin}"
if ! grep -q 'DelphiSource' "${plugin_dir}/.edmplugincache"; then
  echo "ERROR: DelphiSource was not registered in the plugin cache" >&2
  exit 1
fi
if ! grep -q 'delphi_edm4hep::DelphiEventSummaryProducer' \
    "${plugin_dir}/.edmplugincache"; then
  echo "ERROR: DelphiEventSummaryProducer was not registered in the plugin cache" >&2
  exit 1
fi
if ! grep -q 'delphi_edm4hep::DelphiTpcPadMapperProducer' \
    "${plugin_dir}/.edmplugincache"; then
  echo "ERROR: DelphiTpcPadMapperProducer was not registered" >&2
  exit 1
fi
for plugin in GenProducer G4SimProducer; do
  if ! grep -q "${plugin}" "${plugin_dir}/.edmplugincache"; then
    echo "ERROR: ${plugin} was not registered in the plugin cache" >&2
    exit 1
  fi
done

"${code4hep_build}/Code4hep/IO/test/bin_testCode4hepIOCatch2"
"${code4hep_build}/Code4hep/G4Application/test/bin_testCode4hepG4SimProducerTP"
"${code4hep_build}/delphi_edm4hep/tests/particle_counts_test"
"${code4hep_build}/delphi_edm4hep/tests/cargo_database_test"
"${code4hep_build}/delphi_edm4hep/tests/geometry_model_test"
"${code4hep_build}/delphi_edm4hep/tests/gdml_world_writer_test"
"${code4hep_build}/delphi_edm4hep/tests/gdml_beam_pipe_writer_test"
"${code4hep_build}/delphi_edm4hep/tests/tpc_digitization_conditions_test"
"${code4hep_build}/delphi_edm4hep/tests/tpc_pad_response_test"
"${code4hep_build}/delphi_edm4hep/tests/tpc_readout_geometry_test"

geometry_snapshot="${DELPHI_RELEASE_ROOT}/simana/v94c/dat/CERNSNAP2001_94DELSIM.ASC"
require_file "${geometry_snapshot}"
geometry_audit=$("${code4hep_build}/delphi_edm4hep/delphi_geometry_audit" \
  "${geometry_snapshot}")
for expected in \
  records=11265 \
  GEOM=7703 \
  MATC=202 \
  GEOM_with_SHAP=6000 \
  MATC_with_MATF=202 \
  typed_materials=202 \
  typed_geometry_nodes=7703 \
  typed_material_assignments=5424 \
  typed_shapes=6220 \
  typed_references=4246 \
  typed_replacements=1506; do
  if ! grep -qx "${expected}" <<< "${geometry_audit}"; then
    echo "ERROR: native geometry audit is missing '${expected}'" >&2
    exit 1
  fi
done
tpc_readout_audit=$(
  "${code4hep_build}/delphi_edm4hep/delphi_tpc_readout_audit" \
    "${geometry_snapshot}"
)
for expected in \
  rows=16 \
  pads_per_sector=1680 \
  total_pads=20160 \
  sectors=12 \
  first_row_radius_cm=36.5 \
  last_row_radius_cm=106.225 \
  drift_half_length_cm=145 \
  high_voltage_volt=25306 \
  minimum_ionizing_dedx=254.5 \
  mean_pad_amplitude=652.8 \
  drift_velocity_endcap0_cm_per_us=6.998 \
  drift_velocity_endcap1_cm_per_us=7.002 \
  closed_gates=12 \
  pad_calibrations=20160 \
  nonzero_pad_statuses=736 \
  minimum_gain_ratio=4.052 \
  maximum_gain_ratio=5.286 \
  centre_pad_mismatches=0 \
  stampa_response_mismatches=0; do
  if ! grep -qx "${expected}" <<< "${tpc_readout_audit}"; then
    echo "ERROR: native TPC readout audit is missing '${expected}'" >&2
    exit 1
  fi
done

# Keep the narrow world-only export covered for clients that do not yet want
# detector children.
delphi_world_gdml="${build_root}/delphi-v94c-world.gdml"
"${code4hep_build}/delphi_edm4hep/delphi_geometry_export" \
  "${geometry_snapshot}" "${delphi_world_gdml}"
require_file "${delphi_world_gdml}"
if ! grep -q 'rmax="680" z="1170"' "${delphi_world_gdml}"; then
  echo "ERROR: exported DELPHI world has the wrong primary bounds" >&2
  exit 1
fi

# Render the complete authoritative /BEA* subsystem. Exact topology counts
# guard the replacement expansion: MSK1 inherits MSK2's three insert children,
# producing 109 beam-pipe logical instances from 106 source nodes.
delphi_beam_pipe_gdml="${build_root}/delphi-v94c-beam-pipe.gdml"
"${code4hep_build}/delphi_edm4hep/delphi_geometry_export" --beam-pipe \
  "${geometry_snapshot}" "${delphi_beam_pipe_gdml}"
require_file "${delphi_beam_pipe_gdml}"
for tag_count in \
  '<material name=:10' \
  '<polycone name=:116' \
  '<box name=:1' \
  '<union name=:8' \
  '<volume name=:110' \
  '<physvol name=:109'; do
  tag=${tag_count%:*}
  expected_count=${tag_count##*:}
  actual_count=$(grep -c "${tag}" "${delphi_beam_pipe_gdml}")
  if [[ "${actual_count}" != "${expected_count}" ]]; then
    echo "ERROR: beam-pipe GDML has ${actual_count} '${tag}', expected ${expected_count}" >&2
    exit 1
  fi
done
if ! grep -q 'MSK1_placement_0_rotation.*x="-180".*z="-90"' \
    "${delphi_beam_pipe_gdml}"; then
  echo "ERROR: beam-pipe GDML did not preserve the DXMATR mask rotation" >&2
  exit 1
fi

# Add the complete TPC tree. Its POL6 sectors are native closed tessellated
# solids, and the TPC gas itself must be registered as tracker-sensitive.
delphi_tpc_gdml="${build_root}/delphi-v94c-tpc.gdml"
"${code4hep_build}/delphi_edm4hep/delphi_geometry_export" --tpc \
  "${geometry_snapshot}" "${delphi_tpc_gdml}"
require_file "${delphi_tpc_gdml}"
for tag_count in \
  '<material name=:26' \
  '<polycone name=:175' \
  '<box name=:1' \
  '<tessellated name=:36' \
  '<triangular vertex1=:720' \
  '<union name=:22' \
  '<volume name=:191' \
  '<physvol name=:190' \
  'auxtype="SensDet":1'; do
  tag=${tag_count%:*}
  expected_count=${tag_count##*:}
  actual_count=$(grep -c "${tag}" "${delphi_tpc_gdml}")
  if [[ "${actual_count}" != "${expected_count}" ]]; then
    echo "ERROR: TPC GDML has ${actual_count} '${tag}', expected ${expected_count}" >&2
    exit 1
  fi
done
if ! grep -q 'auxtype="StepLimit" auxvalue="1" auxunit="cm"' \
    "${delphi_tpc_gdml}"; then
  echo "ERROR: TPC GDML is missing the DELPHI one-centimetre step limit" >&2
  exit 1
fi

# The framework's simulation path must produce persistent EDM4hep hits, not
# merely process and discard a G4Event. Use the lightweight one-muon source.
g4_output="${build_root}/g4-smoke.edm4hep.root"
(
  cd "${workspace}/Code4hep"
  C4H_MAX_EVENTS=1 C4H_OUTPUT="${g4_output}" \
    cmsRun Code4hep/G4Application/python/hepmc3-sim_cfg.py \
      > "${build_root}/g4-smoke.log" 2>&1
)
require_file "${g4_output}"
python3 "${repo_root}/scripts/check-g4-products.py" "${g4_output}"

delphi_tpc_output="${build_root}/delphi-tpc-smoke.edm4hep.root"
(
  cd "${workspace}/Code4hep"
  C4H_MAX_EVENTS=1 \
    C4H_GDML="${delphi_tpc_gdml}" \
    C4H_FIELD_TESLA=1.2312434 \
    C4H_DELPHI_CARGO="${geometry_snapshot}" \
    C4H_OUTPUT="${delphi_tpc_output}" \
    cmsRun "${repo_root}/steering/delphi_tpc_sim_cfg.py" \
      > "${build_root}/delphi-tpc-smoke.log" 2>&1
)
require_file "${delphi_tpc_output}"
python3 "${repo_root}/scripts/check-g4-products.py" \
  --expected-field 1.2312434 --min-tracker-hits 2 \
  --allow-empty-calorimeter-hits \
  "${delphi_tpc_output}"
python3 "${repo_root}/scripts/check-tpc-pad-products.py" \
  --minimum-hits 1 "${delphi_tpc_output}"

launcher="${code4hep_build}/delphi_edm4hep/delphiRun"
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

# Exercise the user-facing launcher and checked-in configuration on one real
# simulated DELPHI event. Keep the working directory private because PHDST
# uses fixed scratch names such as PDLINPUT and fort.3.
fixture="${repo_root}/testdata/pythia8_94c2_one_event.fadana"
require_file "${fixture}"
runtime_dir="${build_root}/delphiRun-smoke"
mkdir -p "${runtime_dir}"
export DELPHI_INPUT="${fixture}"
export DELPHI_OUTPUT="${runtime_dir}/output.root"
export DELPHI_INPUT_MODE=file
export DELPHI_CONVERSION_PASS=sdst
export DELPHI_IS_REAL_DATA=false
export DELPHI_MAX_EVENTS=1
(
  cd "${runtime_dir}"
  "${launcher}" "${repo_root}/steering/delphi_convert_cfg.py" > run.log 2>&1
)
require_file "${DELPHI_OUTPUT}"
podio_dump=$(podio-dump "${DELPHI_OUTPUT}")
if ! grep -Eq '^events[[:space:]]+1[[:space:]]*$' <<< "${podio_dump}"; then
  echo "ERROR: delphiRun smoke output does not contain exactly one event" >&2
  exit 1
fi
if ! grep -q 'sDST_EVT_dstProcessingTag' <<< "${podio_dump}"; then
  echo "ERROR: delphiRun smoke output lost DELPHI frame metadata" >&2
  exit 1
fi
python3 "${repo_root}/scripts/check-native-event-summary.py" \
  "${DELPHI_OUTPUT}"
if ! grep -q 'delivered 1 events to the in-memory source' \
    "${runtime_dir}/run.log"; then
  echo "ERROR: delphiRun did not report one in-memory event" >&2
  exit 1
fi

echo "Native delphiRun conversion, DELPHI geometry parsing, Geant4 products, scheduled-module closure, and SKELANA-free link audit passed"

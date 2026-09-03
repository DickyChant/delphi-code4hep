#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=../versions.env
source "${repo_root}/versions.env"
workspace=${1:-"${repo_root}/sources"}

verify_locked() {
  local name=$1 expected=$2
  local destination="${workspace}/${name}"
  if [[ ! -d "${destination}/.git" ]]; then
    echo "ERROR: missing checkout ${destination}" >&2
    return 1
  fi
  local actual
  actual=$(git -C "${destination}" rev-parse HEAD)
  if [[ "${actual}" != "${expected}" ]]; then
    echo "ERROR: ${name}: expected ${expected}, found ${actual}" >&2
    return 1
  fi
  if [[ -n $(git -C "${destination}" status --porcelain --untracked-files=no) ]]; then
    echo "ERROR: ${name} has modified tracked files" >&2
    return 1
  fi
  printf '%-18s %s OK\n' "${name}" "${actual}"
}

verify_locked Code4hep "${CODE4HEP_COMMIT}"
verify_locked delphi-edm4hep "${DELPHI_EDM4HEP_COMMIT}"
verify_locked build "${CODE4HEP_BUILD_COMMIT}"

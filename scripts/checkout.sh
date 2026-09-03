#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=../versions.env
source "${repo_root}/versions.env"
workspace=${1:-"${repo_root}/sources"}
mkdir -p "${workspace}"

checkout_locked() {
  local name=$1 url=$2 ref=$3 commit=$4
  local destination="${workspace}/${name}"

  if [[ -e "${destination}" && ! -d "${destination}/.git" ]]; then
    echo "ERROR: ${destination} exists but is not a Git checkout" >&2
    return 1
  fi

  if [[ ! -d "${destination}/.git" ]]; then
    git clone --no-checkout --branch "${ref}" "${url}" "${destination}"
  else
    if [[ -n $(git -C "${destination}" status --porcelain --untracked-files=no) ]]; then
      echo "ERROR: refusing to replace tracked changes in ${destination}" >&2
      return 1
    fi
    git -C "${destination}" fetch origin "${ref}"
  fi

  if ! git -C "${destination}" cat-file -e "${commit}^{commit}" 2>/dev/null; then
    git -C "${destination}" fetch origin "${commit}"
  fi
  git -C "${destination}" checkout --detach "${commit}"
  printf '%-18s %s\n' "${name}" "$(git -C "${destination}" rev-parse HEAD)"
}

checkout_locked Code4hep "${CODE4HEP_URL}" "${CODE4HEP_REF}" "${CODE4HEP_COMMIT}"
checkout_locked delphi-edm4hep "${DELPHI_EDM4HEP_URL}" \
  "${DELPHI_EDM4HEP_REF}" "${DELPHI_EDM4HEP_COMMIT}"
checkout_locked build "${CODE4HEP_BUILD_URL}" "${CODE4HEP_BUILD_REF}" \
  "${CODE4HEP_BUILD_COMMIT}"

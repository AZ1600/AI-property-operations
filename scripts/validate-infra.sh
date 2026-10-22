#!/usr/bin/env bash
# Compile templates locally; never authenticate to Azure or deploy resources.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI is required. Install it, then install the Bicep CLI." >&2
  exit 127
fi

templates=()
while IFS= read -r -d '' template; do
  templates+=("$template")
done < <(find infra -type f -name '*.bicep' -print0)

if [[ ${#templates[@]} -eq 0 ]]; then
  echo "No Bicep templates found under infra/." >&2
  exit 1
fi

for template in "${templates[@]}"; do
  echo "Validating $template"
  az bicep build --file "$template" --stdout > /dev/null
done

echo "Validated ${#templates[@]} Bicep templates. No Azure resources were deployed."

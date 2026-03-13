#!/usr/bin/env sh
set -eu

REPO_ROOT="."
SCOPE="examples/basic"
FILE="examples/basic/pricing.py"
ANCHOR="billing.pricing.apply_discount"
REPLACEMENT="examples/basic/apply_discount.replacement.pyfrag"
PLAN="examples/basic/apply_discount.plan.json"
SKIP_INSTALL=0
SKIP_TESTS=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --repo-root)
      REPO_ROOT="$2"
      shift 2
      ;;
    --scope)
      SCOPE="$2"
      shift 2
      ;;
    --file)
      FILE="$2"
      shift 2
      ;;
    --anchor)
      ANCHOR="$2"
      shift 2
      ;;
    --replacement)
      REPLACEMENT="$2"
      shift 2
      ;;
    --plan)
      PLAN="$2"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --skip-tests)
      SKIP_TESTS=1
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

run_step() {
  label="$1"
  shift
  echo "==> $label"
  "$@"
}

cd "$REPO_ROOT"

if [ "$SKIP_INSTALL" -eq 0 ]; then
  run_step "Install editable package" python -m pip install -e .
fi

if [ "$SKIP_TESTS" -eq 0 ]; then
  run_step "Run test suite" python -m pytest -q
fi

run_step "CLI help" python -m grace.cli --help
run_step "Parse scope" python -m grace.cli parse "$SCOPE" --json
run_step "Validate scope" python -m grace.cli validate "$SCOPE" --json
run_step "Lint scope" python -m grace.cli lint "$SCOPE" --json
run_step "Build map" python -m grace.cli map "$SCOPE" --json
run_step "Dry-run patch" python -m grace.cli patch "$FILE" "$ANCHOR" "$REPLACEMENT" --dry-run --json
run_step "Dry-run apply-plan" python -m grace.cli apply-plan "$PLAN" --dry-run --json

echo "Dogfood run completed."

#!/usr/bin/env bash
set -euo pipefail

TARGET_ROOT=""
APPLY=0
REPOSITORY="https://github.com/xchen1012a-sketch/SpecForge.git"
SOURCE_ROOT=""

usage() {
  cat <<'USAGE'
SpecForge updater for macOS/Linux.

Usage:
  bash .ai-spec/scripts/update.sh [--target <project>] [--apply] [--repository <git-url>] [--source <local-template>]

Default is dry-run. Add --apply to sync the latest project-level rules.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      TARGET_ROOT="${2:-}"
      shift 2
      ;;
    --apply)
      APPLY=1
      shift
      ;;
    --repository)
      REPOSITORY="${2:-}"
      shift 2
      ;;
    --source)
      SOURCE_ROOT="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -z "$TARGET_ROOT" ]; then
  INSTALLED_SPEC_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  if [ "$(basename "$INSTALLED_SPEC_ROOT")" != ".ai-spec" ]; then
    echo "Missing --target when update.sh is not running from an installed .ai-spec/scripts directory." >&2
    exit 2
  fi
  TARGET_ROOT="$(cd "$INSTALLED_SPEC_ROOT/.." && pwd)"
else
  TARGET_ROOT="$(cd "$TARGET_ROOT" && pwd)"
fi

if [ ! -d "$TARGET_ROOT" ]; then
  echo "Target project does not exist: $TARGET_ROOT" >&2
  exit 2
fi

TEMP_SOURCE=""
cleanup() {
  if [ -n "$TEMP_SOURCE" ] && [ -d "$TEMP_SOURCE" ]; then
    case "$(basename "$TEMP_SOURCE")" in
      SpecForge-update-*) rm -rf "$TEMP_SOURCE" ;;
    esac
  fi
}
trap cleanup EXIT

if [ -z "$SOURCE_ROOT" ]; then
  if ! command -v git >/dev/null 2>&1; then
    echo "git is required to pull the latest SpecForge rules." >&2
    exit 2
  fi
  TEMP_SOURCE="$(mktemp -d "${TMPDIR:-/tmp}/SpecForge-update-XXXXXX")"
  git clone --depth 1 "$REPOSITORY" "$TEMP_SOURCE"
  SOURCE_ROOT="$TEMP_SOURCE"
else
  SOURCE_ROOT="$(cd "$SOURCE_ROOT" && pwd)"
fi

SYNC_SCRIPT="$SOURCE_ROOT/scripts/install.sh"
if [ ! -f "$SYNC_SCRIPT" ]; then
  echo "Latest sync script not found: $SYNC_SCRIPT" >&2
  exit 2
fi

ARGS=(--target "$TARGET_ROOT" --sync)
if [ "$APPLY" -eq 1 ]; then
  ARGS+=(--apply)
fi

bash "$SYNC_SCRIPT" "${ARGS[@]}"

if [ "$APPLY" -eq 1 ]; then
  echo "SpecForge rules updated. Project-owned state was preserved."
else
  echo "Dry-run complete. Re-run with --apply to update existing rules."
fi

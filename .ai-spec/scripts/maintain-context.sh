#!/usr/bin/env bash
set -euo pipefail

TARGET_ROOT=""
APPLY=0
FORCE=0
NOW="$(date +%Y-%m-%d)"

usage() {
  cat <<'USAGE'
SpecForge lazy context maintenance for macOS/Linux.

Usage:
  bash .ai-spec/scripts/maintain-context.sh [--target <project>] [--apply] [--force] [--now YYYY-MM-DD]

Default is dry-run. It only archives files explicitly marked as completed.
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
    --force)
      FORCE=1
      shift
      ;;
    --now)
      NOW="${2:-}"
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
    echo "Missing --target outside an installed .ai-spec/scripts directory." >&2
    exit 2
  fi
  TARGET_ROOT="$(cd "$INSTALLED_SPEC_ROOT/.." && pwd)"
else
  TARGET_ROOT="$(cd "$TARGET_ROOT" && pwd)"
fi

SPEC_ROOT="$TARGET_ROOT/.ai-spec"
QUICK_REF="$SPEC_ROOT/business/quick-ref.md"
PROFILE="$SPEC_ROOT/ai-spec.yaml"
if [ ! -f "$QUICK_REF" ] || [ ! -f "$PROFILE" ]; then
  echo "Context maintenance requires business/quick-ref.md and ai-spec.yaml." >&2
  exit 2
fi

line_count() {
  [ -f "$1" ] || { echo 0; return; }
  wc -l < "$1" | tr -d ' '
}

is_completed() {
  grep -Eiq '^\s*(-\s*)?(\*\*)?(status|完成状态)(\*\*)?\s*[:：]\s*completed\s*$' "$1"
}

add_days() {
  local days="$1"
  if date -d "$NOW + $days days" +%Y-%m-%d >/dev/null 2>&1; then
    date -d "$NOW + $days days" +%Y-%m-%d
  else
    date -j -f %Y-%m-%d "$NOW" -v+"${days}"d +%Y-%m-%d
  fi
}

if [ "$FORCE" -ne 1 ] && ! grep -Eq '^>\s*status:\s*GENERATED\s*$' "$QUICK_REF"; then
  echo "Maintenance skipped: quick-ref is not GENERATED."
  exit 0
fi

PROJECT_SIZE="$(grep -E '^\s{2}projectSize:\s*(tiny|small|medium|large|enterprise|auto)\b' "$PROFILE" | head -n 1 | sed -E 's/.*projectSize:\s*([^ #]+).*/\1/')"
PROJECT_SIZE="${PROJECT_SIZE:-auto}"
case "$PROJECT_SIZE" in
  tiny|small) INTERVAL_DAYS=30; BUSINESS_BUDGET=300; PROJECT_MAP_BUDGET=120 ;;
  medium) INTERVAL_DAYS=14; BUSINESS_BUDGET=500; PROJECT_MAP_BUDGET=180 ;;
  large) INTERVAL_DAYS=7; BUSINESS_BUDGET=800; PROJECT_MAP_BUDGET=250 ;;
  enterprise) INTERVAL_DAYS=7; BUSINESS_BUDGET=1200; PROJECT_MAP_BUDGET=350 ;;
  *) INTERVAL_DAYS=14; BUSINESS_BUDGET=300; PROJECT_MAP_BUDGET=120 ;;
esac

DUE="$(grep -E '^>\s*maintenanceDue:\s*(auto|[0-9]{4}-[0-9]{2}-[0-9]{2})\s*$' "$QUICK_REF" | head -n 1 | sed -E 's/^>\s*maintenanceDue:\s*//;s/\s*$//')"
IS_DUE=0
if [ "$FORCE" -eq 1 ] || [ -z "$DUE" ] || [ "$DUE" = "auto" ] || [[ "$DUE" < "$NOW" ]] || [ "$DUE" = "$NOW" ]; then
  IS_DUE=1
fi

ISSUES=()
[ "$(line_count "$QUICK_REF")" -le 40 ] || ISSUES+=("COMPACT_REQUIRED business/quick-ref.md lines=$(line_count "$QUICK_REF") budget=40")
[ "$(line_count "$TARGET_ROOT/docs/plans/current.md")" -le 80 ] || ISSUES+=("COMPACT_REQUIRED docs/plans/current.md lines=$(line_count "$TARGET_ROOT/docs/plans/current.md") budget=80")
[ "$(line_count "$SPEC_ROOT/business/business-rules.md")" -le "$BUSINESS_BUDGET" ] || ISSUES+=("COMPACT_REQUIRED business/business-rules.md lines=$(line_count "$SPEC_ROOT/business/business-rules.md") budget=$BUSINESS_BUDGET")
[ "$(line_count "$SPEC_ROOT/business/project-map.md")" -le "$PROJECT_MAP_BUDGET" ] || ISSUES+=("COMPACT_REQUIRED business/project-map.md lines=$(line_count "$SPEC_ROOT/business/project-map.md") budget=$PROJECT_MAP_BUDGET")

if [ "$IS_DUE" -ne 1 ] && [ "${#ISSUES[@]}" -eq 0 ]; then
  echo "Maintenance not due. projectSize=$PROJECT_SIZE due=$DUE"
  exit 0
fi

ACTIONS=()
add_archive_actions() {
  local type="$1"
  local root="$2"
  local archive="$3"
  [ -d "$root" ] || return
  while IFS= read -r file; do
    if is_completed "$file"; then
      ACTIONS+=("$type|$file|$archive/$(date +%Y-%m)/$(basename "$file")")
    fi
  done < <(find "$root" -maxdepth 1 -type f -name '*.md' | sort)
}

add_archive_actions session "$SPEC_ROOT/sessions" "$SPEC_ROOT/sessions/archive"
add_archive_actions handoff "$TARGET_ROOT/docs/handoffs" "$TARGET_ROOT/docs/handoffs/archive"
add_archive_actions phase "$TARGET_ROOT/docs/plans/phases" "$TARGET_ROOT/docs/plans/archive"

for issue in "${ISSUES[@]}"; do echo "$issue"; done
for action in "${ACTIONS[@]}"; do
  IFS='|' read -r type src dst <<< "$action"
  echo "ARCHIVE $type $src -> $dst"
done

if [ "$APPLY" -ne 1 ]; then
  echo "Maintenance dry-run complete. actions=${#ACTIONS[@]} issues=${#ISSUES[@]}"
  exit 0
fi

for action in "${ACTIONS[@]}"; do
  IFS='|' read -r _type src dst <<< "$action"
  mkdir -p "$(dirname "$dst")"
  if [ -e "$dst" ]; then
    base="${dst%.*}"
    ext="${dst##*.}"
    dst="${base}-$(date +%Y%m%d%H%M%S).${ext}"
  fi
  mv "$src" "$dst"
done

if [ "${#ISSUES[@]}" -gt 0 ]; then
  NEXT_DUE="$(add_days 1)"
else
  NEXT_DUE="$(add_days "$INTERVAL_DAYS")"
fi

TMP_FILE="$(mktemp)"
awk -v next="$NEXT_DUE" '
  /^>[[:space:]]*maintenanceDue:/ { print "> maintenanceDue: " next; done=1; next }
  { print }
  END { if (!done) exit 3 }
' "$QUICK_REF" > "$TMP_FILE"
mv "$TMP_FILE" "$QUICK_REF"

echo "Maintenance applied. archived=${#ACTIONS[@]} issues=${#ISSUES[@]} nextDue=$NEXT_DUE"

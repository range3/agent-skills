#!/bin/bash
# adr-index.sh — YAMLフロントマターだけをパースして一覧生成
# Usage:
#   bash adr-index.sh docs/decisions/
#   bash adr-index.sh docs/decisions/ accepted
#   bash adr-index.sh docs/decisions/ --markdown

DIR="${1:-.}"
FILTER_STATUS=""
MARKDOWN=false

shift || true
for arg in "$@"; do
  case "$arg" in
    --markdown) MARKDOWN=true ;;
    *) FILTER_STATUS="$arg" ;;
  esac
done

if $MARKDOWN; then
  echo "| file | status | date | decision |"
  echo "|------|--------|------|----------|"
else
  echo -e "file\tstatus\tdate\tdecision"
fi

for file in "$DIR"/[0-9][0-9][0-9][0-9]-*.md; do
  [ -f "$file" ] || continue
  frontmatter=$(sed -n '1{/^---$/!q}; 1,/^---$/{/^---$/!p}' "$file")
  status=$(echo "$frontmatter" | grep '^status:' | sed 's/^status:[[:space:]]*//' | tr -d '"' | tr -d "'")
  date=$(echo "$frontmatter" | grep '^date:' | sed 's/^date:[[:space:]]*//' | tr -d '"')
  decision=$(echo "$frontmatter" | grep '^decision:' | sed 's/^decision:[[:space:]]*//' | tr -d '"')
  if [ -n "$FILTER_STATUS" ] && [ "$status" != "$FILTER_STATUS" ]; then
    continue
  fi
  if $MARKDOWN; then
    echo "| $(basename "$file") | ${status} | ${date} | ${decision} |"
  else
    echo -e "$(basename "$file")\t${status}\t${date}\t${decision}"
  fi
done

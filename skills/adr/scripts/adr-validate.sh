#!/bin/bash
# adr-validate.sh — ADRフォーマットバリデーション
# Usage: bash adr-validate.sh <path-to-adr-file>

FILE="$1"
ERRORS=()

if [ -z "$FILE" ] || [ ! -f "$FILE" ]; then
  echo "ADR file not found: $FILE"; exit 0
fi

BASENAME=$(basename "$FILE")
if [[ "$BASENAME" == adr-template* ]] || [[ "$BASENAME" == "README.md" ]]; then
  exit 0
fi

if ! echo "$BASENAME" | grep -qE '^[0-9]{4}-[a-z0-9-]+\.md$'; then
  ERRORS+=("ファイル名が規則（NNNN-kebab-case.md）に従っていません: $BASENAME")
fi

if ! head -1 "$FILE" | grep -q '^---$'; then
  ERRORS+=("YAMLフロントマターが見つかりません")
else
  FM=$(sed -n '1{/^---$/!q}; 1,/^---$/{/^---$/!p}' "$FILE")

  STATUS=$(echo "$FM" | grep '^status:' | sed 's/^status:[[:space:]]*//' | tr -d '"' | tr -d "'")
  [ -z "$STATUS" ] && ERRORS+=("status がありません")
  echo "$STATUS" | grep -qE '^(proposed|accepted|deprecated|superseded)$' || \
    [ -z "$STATUS" ] || ERRORS+=("status が不正: '$STATUS'")

  echo "$FM" | grep -qE '^date:' || ERRORS+=("date がありません")

  DECISION=$(echo "$FM" | grep '^decision:' | sed 's/^decision:[[:space:]]*//' | tr -d '"')
  [ -z "$DECISION" ] && ERRORS+=("decision がありません")

  if [ "$STATUS" = "superseded" ]; then
    SUP=$(echo "$FM" | grep '^superseded-by:' | sed 's/^superseded-by:[[:space:]]*//' | tr -d '"')
    [ -z "$SUP" ] && ERRORS+=("superseded だが superseded-by が未設定")
  fi
fi

for s in "Context and Problem Statement" "Considered Options" "Decision Outcome"; do
  grep -qi "## $s" "$FILE" || ERRORS+=("必須セクション「$s」がありません")
done

if [ ${#ERRORS[@]} -eq 0 ]; then
  echo "PASS: $BASENAME"
else
  echo "FAIL: $BASENAME"
  for err in "${ERRORS[@]}"; do echo "   - $err"; done
  exit 1
fi

#!/bin/bash
# adr-post-validate.sh — PostToolUse hook: ADR編集後のバリデーション
# stdin: hook input JSON

INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# ADRファイル以外は無視
if [ -z "$FILE" ]; then exit 0; fi
if ! echo "$FILE" | grep -qE '^docs/decisions/[0-9]{4}-.*\.md$'; then exit 0; fi

# バリデーション実行
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULT=$("$SCRIPT_DIR/adr-validate.sh" "$FILE" 2>&1)

if [ $? -ne 0 ]; then
  echo "$RESULT" >&2
  exit 2  # exit 2 → stderr が Claude に表示される
fi

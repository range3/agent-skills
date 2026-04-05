#!/bin/bash
# adr-session-start.sh — SessionStart フックでADR一覧をコンテキストに注入
# Usage: Claude Code の SessionStart フックから自動実行される
#
# INDEX.md が存在すれば additionalContext として出力し、
# 存在しなければ何もしない（init前のプロジェクトでも安全）。

INDEX="${CLAUDE_PROJECT_DIR}/docs/decisions/INDEX.md"

if [ -f "$INDEX" ]; then
  CONTENT=$(cat "$INDEX")
  FOOTER="
必要に応じて関連ADRの本文も確認すること。"
  # JSON内の改行・特殊文字をエスケープ
  ESCAPED=$(printf '%s\n%s' "$CONTENT" "$FOOTER" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))')
  echo "{\"additionalContext\": ${ESCAPED}}"
fi

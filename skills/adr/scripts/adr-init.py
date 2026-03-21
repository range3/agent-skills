#!/usr/bin/env python3
"""adr-init.py — プロジェクトに MADR ベースの ADR 管理環境を構築する。

Usage:
    python3 <skill-dir>/scripts/adr-init.py [--project-root PATH]

冪等: 既存ファイルはスキップ、settings.json はマージ（追加のみ）。
"""

import argparse
import datetime
import glob
import json
import os
import sys

# ─── 埋め込みコンテンツ ───────────────────────────────────────────

README_MD = """\
# Architecture Decision Records

このディレクトリにはプロジェクトの設計判断を MADR 4.0.0 形式で記録しています。

## テンプレート

ADRテンプレートは ADR スキルの `references/adr-template.md` で管理。
テンプレート内の `<!-- This is an optional element. Feel free to remove. -->` がついたセクションは任意。重要度に応じて省略する。

## ステータスの意味

| ステータス | 意味 |
|---|---|
| proposed | 提案中。レビュー待ち |
| accepted | 承認済み。現在有効 |
| deprecated | 非推奨。もう適用しないが履歴として残す |
| superseded | 新しいADRで置換済み |
"""

BOOTSTRAP_ADR_TEMPLATE = """\
---
status: "accepted"
date: {date}
decision: "MADR 4.0.0で設計判断を記録する"
superseded-by: ""
---

# MADR 4.0.0 を設計判断の記録に採用する

## Context and Problem Statement

プロジェクトの設計判断が暗黙知として失われている。
新しいメンバーが「なぜこの技術を選んだのか」を理解できず、
同じ議論が繰り返されたり、過去の判断と矛盾する変更が行われている。

## Decision Drivers

- 開発者が慣れ親しんだMarkdownで書けること
- ソースコードと同じリポジトリで管理できること
- テンプレートが構造化されており、記入漏れを防げること
- コーディングエージェントが参照・解析しやすいこと

## Considered Options

1. MADR 4.0.0（Markdown Architectural Decision Records）
2. Nygard式ADR（オリジナルのシンプルなADR）
3. Y-Statement形式
4. 記録しない（現状維持）

## Decision Outcome

Chosen option: "MADR 4.0.0", because 構造化されたテンプレートにより
検討した選択肢のPros/Consが明示的に記録でき、チームメンバーや
コーディングエージェントが設計判断の文脈を正確に理解できるため。

### Confirmation

- `/adr レビュー` で定期的に整合性をチェック

## Pros and Cons of the Options

### MADR 4.0.0

- Good, because 選択肢のPros/Consが構造化されており人間にもコーディングエージェントにも解析しやすい
- Good, because 任意セクションマーカーにより判断の重要度に応じて詳細度を調整できる
- Neutral, because 公的な国際標準ではなくデファクトスタンダードである
- Bad, because Nygard式より記入するセクションが多い

### Nygard式ADR

- Good, because 非常にシンプルで書き始めのハードルが低い
- Bad, because 選択肢の比較評価セクションがなく判断根拠が不明確になりやすい

### Y-Statement形式

- Good, because 1文で判断を要約できる
- Bad, because ツールサポートが限定的

### 記録しない

- Good, because 追加作業が発生しない
- Bad, because 設計判断が失われ続ける

## Consequences

- Good, 設計判断の透明性が向上する
- Good, チームやコーディングエージェントが過去の判断を参照して一貫した意思決定を行える
- Bad, ADR作成に一定の作業時間が必要になる

## More Information

- [MADR 公式サイト](https://adr.github.io/madr/)
- [MADR GitHub リポジトリ](https://github.com/adr/madr)
"""

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _make_hook_entry(project_root: str) -> dict:
    """プロジェクトルートからの相対パスでフックコマンドを構築する。"""
    rel_path = os.path.relpath(
        os.path.join(_SCRIPT_DIR, "adr-post-validate.sh"), project_root
    )
    return {
        "matcher": "Edit|Write",
        "hooks": [
            {
                "type": "command",
                "command": f'bash "$CLAUDE_PROJECT_DIR"/{rel_path}',
                "timeout": 10,
            }
        ],
    }

CLAUDE_MD_ADR_SECTION_MARKER = "## 設計判断ルール（ADR）"

CLAUDE_MD_ADR_SECTION = """\
## 設計判断ルール（ADR）

このプロジェクトでは MADR 4.0.0（+ 独自フロントマター拡張）を用いて設計判断を記録する。
ADR の作成・管理は `/adr` スキルで行う。

設計判断（技術選定、構成変更、パターン採用など）が行われた場合は `/adr` スキルを使って ADR を残すこと。
"""

# ─── ヘルパー ─────────────────────────────────────────────────────


def _print_step(step: int, total: int, path: str) -> None:
    print(f"\n[{step}/{total}] {path}")


def _created(msg: str) -> None:
    print(f"  CREATED: {msg}")


def _skip(msg: str) -> None:
    print(f"  SKIP: {msg}")


def _updated(msg: str) -> None:
    print(f"  UPDATED: {msg}")


def _error(msg: str) -> None:
    print(f"  ERROR: {msg}", file=sys.stderr)


# ─── ステップ実装 ─────────────────────────────────────────────────


def step_create_dir(root: str) -> tuple[str, str]:
    """[1/5] docs/decisions/ ディレクトリ作成"""
    path = os.path.join(root, "docs", "decisions")
    _print_step(1, 5, "docs/decisions/")
    if os.path.isdir(path):
        _skip("already exists")
        return "skip", path
    os.makedirs(path, exist_ok=True)
    _created("docs/decisions/")
    return "created", path


def step_readme(decisions_dir: str) -> str:
    """[2/5] docs/decisions/README.md 生成"""
    path = os.path.join(decisions_dir, "README.md")
    _print_step(2, 5, "docs/decisions/README.md")
    if os.path.exists(path):
        _skip("already exists")
        return "skip"
    with open(path, "w", encoding="utf-8") as f:
        f.write(README_MD)
    _created("docs/decisions/README.md")
    return "created"


def step_bootstrap_adr(decisions_dir: str) -> str:
    """[3/5] docs/decisions/0001-use-madr-for-decision-records.md 生成"""
    _print_step(3, 5, "docs/decisions/0001-use-madr-for-decision-records.md")
    existing = glob.glob(os.path.join(decisions_dir, "0001-*.md"))
    if existing:
        _skip(f"0001 already exists: {os.path.basename(existing[0])}")
        return "skip"
    path = os.path.join(decisions_dir, "0001-use-madr-for-decision-records.md")
    today = datetime.date.today().isoformat()
    content = BOOTSTRAP_ADR_TEMPLATE.format(date=today)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    _created(f"0001-use-madr-for-decision-records.md (date: {today})")
    return "created"


def _has_adr_hook(hook_list: list) -> bool:
    """PostToolUse にADRバリデーションhookが既に存在するか"""
    for entry in hook_list:
        hooks = entry.get("hooks", [])
        for h in hooks:
            cmd = h.get("command", "")
            if "adr-post-validate.sh" in cmd or "adr-validate.sh" in cmd:
                return True
    return False


def step_settings_json(root: str) -> str:
    """[4/5] .claude/settings.json にフックをマージ"""
    claude_dir = os.path.join(root, ".claude")
    settings_path = os.path.join(claude_dir, "settings.json")
    _print_step(4, 5, ".claude/settings.json")

    os.makedirs(claude_dir, exist_ok=True)

    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except json.JSONDecodeError as e:
            _error(f"JSON parse error: {e}")
            return "error"
    else:
        settings = {}

    settings.setdefault("hooks", {})
    hooks = settings["hooks"]
    hooks.setdefault("PostToolUse", [])

    if not isinstance(hooks["PostToolUse"], list):
        _error("hooks.PostToolUse is not an array, skipping merge")
        return "error"

    if _has_adr_hook(hooks["PostToolUse"]):
        _skip("PostToolUse ADR hook already exists")
        return "skip"

    hooks["PostToolUse"].append(_make_hook_entry(root))
    _updated("Added PostToolUse ADR hook")

    with open(settings_path, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return "updated"


def step_claude_md(root: str) -> str:
    """[5/5] CLAUDE.md に ADR セクションを追記"""
    path = os.path.join(root, "CLAUDE.md")
    _print_step(5, 5, "CLAUDE.md")

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if CLAUDE_MD_ADR_SECTION_MARKER in content:
            _skip("ADR section already exists")
            return "skip"
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n" + CLAUDE_MD_ADR_SECTION)
        _updated("Appended ADR section")
        return "updated"
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write("# プロジェクト概要\n\n" + CLAUDE_MD_ADR_SECTION)
        _created("CLAUDE.md with ADR section")
        return "created"


# ─── メイン ───────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="ADR管理環境の初期設定")
    parser.add_argument(
        "--project-root",
        default=os.getcwd(),
        help="プロジェクトルート（デフォルト: カレントディレクトリ）",
    )
    args = parser.parse_args()
    root = os.path.abspath(args.project_root)

    if not os.path.isdir(root):
        print(f"ERROR: directory not found: {root}", file=sys.stderr)
        return 1

    print("=== ADR Init ===")
    print(f"Project root: {root}")

    results = {}

    result, decisions_dir = step_create_dir(root)
    results["docs/decisions/"] = result

    results["README.md"] = step_readme(decisions_dir)
    results["0001-*.md"] = step_bootstrap_adr(decisions_dir)
    results["settings.json"] = step_settings_json(root)
    results["CLAUDE.md"] = step_claude_md(root)

    created = sum(1 for v in results.values() if v == "created")
    updated = sum(1 for v in results.values() if v == "updated")
    skipped = sum(1 for v in results.values() if v == "skip")
    errors = sum(1 for v in results.values() if v == "error")

    print("\n=== Done ===")
    print(f"Created: {created}  Updated: {updated}  Skipped: {skipped}  Errors: {errors}")

    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

---
name: adr
description: >
  新しいライブラリの導入、フレームワークの変更、DB選定、API設計、
  インフラ構成変更など、技術的な選択を伴うタスクに着手する前に
  必ずこのスキルで既存の設計判断(ADR)を確認すること。
  「なぜ今の構成になっているか」の文脈を得ることで、
  矛盾する変更や重複した検討を防ぐ。
  設計判断を下した場合はこのスキルでADRを作成する。
  トリガー: ADR, 設計, 技術選定, なぜこの技術, アーキテクチャ, アーキ,
  どれを使うべき, 比較, 選定, 採用, 検討, 壁打ち, 導入, 移行, 置換,
  構成変更, DB, API設計, インフラ, CI/CD, テスト戦略,
  ライブラリ追加, フレームワーク
---

# ADR Management

MADR 4.0.0 に基づく設計判断の記録・管理スキル。

## スクリプト実行規約

`scripts/` 配下のパスは本スキルディレクトリからの相対パス。実行時はSKILL.mdの配置場所を基準にフルパスを構築すること。

## ファイル命名規則

`docs/decisions/NNNN-kebab-case-title.md`（番号は0001から連番）

## フロントマター仕様

```yaml
---
status: "proposed"              # proposed | accepted | deprecated | superseded
date: 2025-01-15                # YYYY-MM-DD
decision: "NextAuth.jsを採用"    # 決定内容の1行要約
superseded-by: ""                # 置換先ADR番号（superseded時のみ）
---
```

## コンテキスト節約ルール（最重要）

SessionStart フックにより `docs/decisions/INDEX.md` が自動でコンテキストに載る。

1. INDEX.md の `decision` 列で関連性を判定
2. 必要な ADR だけ本文を開く

手動で一覧を確認する場合:
```bash
bash scripts/adr-index.sh docs/decisions/
bash scripts/adr-index.sh docs/decisions/ accepted
```

## テンプレート

`references/adr-template.md` を使用。重要度が低い判断では任意セクション（`<!-- This is an optional element. Feel free to remove. -->` マーカー付き）を省略する。

## 記述ガイドライン

- decision: 本文を読まなくても何を決めたか分かる1行
  - 良い例: "NextAuth.jsを採用。Google/GitHub OAuth対応"
  - 悪い例: "認証について決めた"

## アクション

会話の文脈から適切なアクションを判断して実行する。
`/adr <自然言語の指示>` でも明示的に呼び出せる。

### init

`python3 scripts/adr-init.py` を実行し、結果を報告。初期設定完了後、プロジェクト固有のカスタマイズを促す。

### supersede

1. 新ADR作成（Context に旧ADRへの参照と変更理由、Considered Options に旧方針も含める）
2. 旧ADRの `status` → `superseded`、`superseded-by` に新ADR番号を記入
3. バリデーションとインデックス更新（後述）

### バリデーションとインデックス更新

ADR ファイルを作成・更新したら必ず以下を順に実行すること:

1. `scripts/adr-validate.sh <file>` でフォーマット検証。違反があればその場で修正
2. `bash scripts/adr-index.sh docs/decisions/ --markdown > docs/decisions/INDEX.md` でインデックス再生成

INDEX.md は SessionStart フックでコンテキストに注入されるため、常に最新に保つこと。

### 補足

- 新規作成・更新時は INDEX.md で関連ADRを特定し矛盾チェック
- 棄却した選択肢も Considered Options に含める

## ADR作成の判断基準

**作成する:** 技術選定、構成変更、パターン採用、代替案を比較した上での判断
**作成しない:** 既存ルールに従っただけ、バグ修正、探索中の仮判断
**迷ったら作成する**

## 並列開発ルール

ADRの作成・更新はメインセッションのみ。他エージェントは read-only 参照し、設計判断の必要性に気づいたらその場で報告する。

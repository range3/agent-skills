---
name: github-investigator
description: >
  GitHub上の特定トピックに関するIssue・PR・コードの議論を調査し、要約レポートを作成するスキル。ghコマンドを使用する
context: fork
allowed-tools:
  - Bash(gh *)
---

# GitHub Investigator Skill

GitHub上である事柄（機能名、バグ、コンポーネント名など）についてどのような議論がされているかを `gh` CLIで調査し、要約レポートを生成する。

## 前提条件

- `gh` CLI がインストール・認証済みであること
- 対象リポジトリへのアクセス権があること

## 調査フロー

### Step 1: 調査対象の確認

ユーザーから以下を確認する:

- **検索キーワード**: 調査したい事柄（例: `ECConnector`, `authentication`, `memory leak`）
- **対象リポジトリ**: 特定リポジトリ (`--repo owner/repo`) か、全リポジトリか
- **スコープ**: Issue のみ / PR のみ / 両方 / コード検索も含む（デフォルト: Issue + PR の両方）

### Step 2: 広く浅く検索（一覧取得）

まず全体像を把握する。以下のコマンドを実行し、件数と傾向をつかむ。

```bash
# Issue 検索
gh search issues "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated --order desc

# PR 検索
gh search prs "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated --order desc
```

### Step 3: 深く掘る（詳細取得）

Step 2 の結果から関連性の高い Issue/PR を選び、詳細を取得する。

```bash
# Issue 詳細
gh issue view NUMBER --repo OWNER/REPO \
  --json title,body,state,author,labels,comments,createdAt,closedAt,url

# PR 詳細（reviews にコードレビューの議論、files に影響範囲が含まれる）
gh pr view NUMBER --repo OWNER/REPO \
  --json title,body,state,author,labels,comments,reviews,files,commits,mergedAt,url

# PR の差分（必要に応じて。差分が大きい場合は files で概要を先に把握する）
gh pr diff NUMBER --repo OWNER/REPO
```

### Step 4: 関連情報の補完（必要に応じて）

```bash
# タイムライン取得（経緯を時系列で追う。クロスリファレンスやラベル変更が含まれる）
gh api repos/OWNER/REPO/issues/NUMBER/timeline --paginate

# コード検索（議論の前提となるコードの所在や使われ方を把握したいときに使う）
gh search code "KEYWORD" --repo OWNER/REPO --limit 10
```

コメントや本文中に `#123` や他リポジトリへの参照がある場合は、芋づる式に追跡する。特に「Closes #XX」「Related to #XX」「Depends on #XX」に注目。

### Step 5: レポート作成

調査結果を以下の構成でまとめる:

```markdown
# GitHub 調査レポート: [キーワード]

## 調査概要
- 対象リポジトリ: ...
- 検索キーワード: ...
- 調査日: ...
- 該当 Issue 数: X件 (open: X / closed: X)
- 該当 PR 数: X件 (open: X / merged: X / closed: X)

## エグゼクティブサマリー
[3〜5行で調査結果の要約。現状どうなっているか、主要な論点は何か]

## 主要な議論・論点
### 論点1: [タイトル]
- 関連: #123, #456
- 状態: [解決済み / 進行中 / 未着手]
- 要約: ...

### 論点2: [タイトル]
...

## タイムライン（重要なイベント）
- YYYY-MM-DD: [何が起きたか] (#123)
- ...

## 未解決の課題
- [ ] ...

## 関連リンク
- [Issue タイトル](URL) - 状態
- [PR タイトル](URL) - 状態
```

## コマンドリファレンス

| 目的 | コマンド |
|------|---------|
| Issue 一覧検索 | `gh search issues "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated` |
| PR 一覧検索 | `gh search prs "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated` |
| コード検索 | `gh search code "KEYWORD" --repo OWNER/REPO --limit 10` |
| Issue 詳細 | `gh issue view NUM --repo OWNER/REPO --json title,body,state,author,labels,comments,createdAt,closedAt,url` |
| PR 詳細 | `gh pr view NUM --repo OWNER/REPO --json title,body,state,author,labels,comments,reviews,files,commits,mergedAt,url` |
| PR 差分 | `gh pr diff NUM --repo OWNER/REPO` |
| タイムライン | `gh api repos/OWNER/REPO/issues/NUM/timeline --paginate` |
| ラベル絞込 | `gh search issues "KEYWORD label:bug" --repo OWNER/REPO` |
| 著者絞込 | `gh search issues "KEYWORD author:USERNAME" --repo OWNER/REPO` |

## Tips

- **レート制限**: GitHub Search API は認証済みで 30 req/min。大量検索時は間隔を空ける。
- **JSON + jq**: `gh issue view 123 --json comments --jq '.comments | length'` のように `jq` で加工できる。
- **大量コメントの扱い**: コメントが多い Issue/PR はまず件数を確認し、最新や長文のコメントを優先して読む。
- **クロスリファレンスの追跡**: 議論は複数の Issue/PR に分散しがち。本文やコメント中の `#数字` を見逃さない。

大量の情報を整理・構造化するため、ultrathink を有効にして深く考えること。

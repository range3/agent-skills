---
name: github-investigator
description: >
  GitHub上の特定トピックに関するIssue・PR・コードの議論を調査し、要約レポートを作成するスキル。
  ghコマンドを使用する。ユーザーがGitHubリポジトリでの議論の調査、Issue/PRの横断的な分析、
  特定の機能・バグ・コンポーネントに関する経緯の把握、GitHubでの意思決定の追跡を求めた場合に使用すること。
  「このリポジトリで○○についてどんな議論がある？」「○○の経緯を調べて」「関連するIssueやPRをまとめて」
  「○○はなぜこういう設計になった？」といったリクエストにも対応する。
  明示的にGitHubと言及していなくても、OSS の機能議論や設計経緯の調査であればこのスキルを使う。
allowed-tools:
  - Bash(gh *)
---

# GitHub Investigator Skill

GitHub上である事柄（機能名、バグ、コンポーネント名など）についてどのような議論がされているかを `gh` CLIで調査し、要約レポートを生成する。

## JSON処理のルール

`gh` の出力を加工する際は、`gh` に組み込まれた `--jq` フラグを使う。`| jq` へのパイプや `python3 -c "import json; ..."` へのパイプは使わない。`--jq` なら `jq` が未インストールの環境でも動作し、コマンドが1つで完結するため可読性も高い。

```bash
# 良い例: --jq フラグを使う
gh issue view 123 --repo OWNER/REPO --json comments --jq '.comments | length'
gh issue view 123 --repo OWNER/REPO --json title,state --jq '"\(.title) [\(.state)]"'

# 悪い例（やらないこと）
gh issue view 123 --repo OWNER/REPO --json comments | jq '.comments | length'
gh issue view 123 --repo OWNER/REPO --json comments | python3 -c "import json, sys; ..."
```

## 前提条件

- `gh` CLI がインストール・認証済みであること
- 調査開始前に `gh auth status` で認証状態を確認し、未認証ならユーザーに案内する
- 対象リポジトリへのアクセス権があること（アクセス拒否された場合はその旨を報告し、パブリックリポジトリかどうかの確認を促す）

## 調査フロー

### Step 1: 調査対象の特定

ユーザーの依頼文から以下を推測し、不明な点だけ確認する。毎回すべてを聞く必要はない。

- **検索キーワード**: 調査したい事柄（例: `ECConnector`, `authentication`, `memory leak`）
- **対象リポジトリ**: 特定リポジトリ (`--repo owner/repo`) か、全リポジトリか
- **スコープ**: Issue のみ / PR のみ / 両方（デフォルト: 両方）

デフォルト動作: リポジトリが文脈から明らかならそのまま使う。スコープは Issue + PR の両方で始める。キーワードは依頼文からそのまま抽出する。曖昧な場合のみ確認する。

### Step 2: 全体像の把握（広く浅く）

いきなり個別のIssueに潜ると、重要な議論を見落としたり、特定の視点に偏ったりしやすい。最初に件数と傾向をつかんでから深掘りに移ることで、調査の網羅性と効率が上がる。

```bash
# Issue 検索
gh search issues "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated --order desc

# PR 検索
gh search prs "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated --order desc
```

**結果が0件の場合**: キーワードが具体的すぎる可能性がある。類義語や上位概念に広げて再検索する（例: `ECConnector` → `connector`, `EC`）。それでも0件なら、そのトピックについてリポジトリ上で議論が行われていない旨を報告する。

**結果が多すぎる場合（50件超）**: ラベルや期間で絞り込む。`label:bug` や `created:>2024-01-01` などの修飾子を活用する。

ここで一覧を眺め、以下のパターンを探す:
- 繰り返し登場する論点やキーワード
- 同じ人物が複数のIssue/PRに関与しているか
- open/closed の比率（未解決の割合が高いか）

### Step 3: 深掘り（詳細取得）

Step 2 で関連性の高い Issue/PR を特定したら、詳細を取得する。議論の全容を把握するにはコメントまで読む必要があるが、すべてを読む必要はない。関連性の高いものから優先的に読み、通常は 5〜10件 程度の詳細取得で主要な論点はカバーできる。

```bash
# Issue 詳細
gh issue view NUMBER --repo OWNER/REPO \
  --json title,body,state,author,labels,comments,createdAt,closedAt,url

# PR 詳細（reviews にコードレビューの議論、files に影響範囲が含まれる）
gh pr view NUMBER --repo OWNER/REPO \
  --json title,body,state,author,labels,comments,reviews,files,commits,mergedAt,url
```

**コメントが大量にある場合（30件超）**: まずコメント数を確認（`--json comments --jq '.comments | length'`）し、すべてを処理しようとしない。最新の10件と、リアクションが多いコメントを優先して読む。古い議論は結論部分だけ拾えば十分なことが多い。

**PR の差分**: 差分が大きい場合は、まず `files` で影響範囲の概要を把握してから、必要なファイルだけ diff を確認する。

```bash
# 差分が必要な場合
gh pr diff NUMBER --repo OWNER/REPO
```

### Step 4: 関連情報の補完（必要に応じて）

議論の経緯を正確に追うために、タイムラインやコード検索が有用な場合がある。特に「なぜこの設計判断がなされたか」を追うときにはタイムラインが役立つ。

```bash
# タイムライン取得（経緯を時系列で追う。クロスリファレンスやラベル変更が含まれる）
gh api repos/OWNER/REPO/issues/NUMBER/timeline --paginate

# コード検索（議論の前提となるコードの所在や使われ方を把握したいときに使う）
gh search code "KEYWORD" --repo OWNER/REPO --limit 10
```

コメントや本文中に `#123` や他リポジトリへの参照がある場合は、関連性が高ければ追跡する。特に以下のパターンに注目:
- `Closes #XX` / `Fixes #XX` — 直接の解決関係
- `Related to #XX` — 関連する議論
- `Depends on #XX` / `Blocked by #XX` — 依存関係

ただし、すべての参照を追う必要はない。調査目的に直結するものだけを選ぶ。

### Step 5: レポート作成

調査結果の規模に応じて適切なフォーマットを選ぶ。少数のIssue/PRしかない場合に大仰なレポートを作ると冗長になり、逆に多数の議論がある場合に簡潔すぎると情報が失われる。

**小規模（該当5件以下）**: 簡潔にまとめる。エグゼクティブサマリーと関連リンクだけでも十分。

**中〜大規模（該当6件以上）**: 以下のテンプレートに沿って構造化する。

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

## エラー・トラブル対応

| 状況 | 対処 |
|------|------|
| `gh auth status` が未認証 | `gh auth login` の実行を案内する |
| リポジトリへのアクセス拒否 | リポジトリの公開設定や権限を確認するよう案内する |
| 検索結果が0件 | キーワードを広げて再検索（類義語・上位概念）。それでも0件なら報告 |
| レート制限エラー (HTTP 403/429) | 30秒〜1分待ってからリトライ。連続で発生する場合はユーザーに報告 |
| コメントが100件超 | 全件読まない。最新10件 + リアクション上位を優先 |
| diff が巨大（1000行超） | `files` で概要を先に把握し、関連ファイルだけ diff を見る |

## 補足

- この調査では多くの情報を統合する必要があるため、結論を急がず、収集した情報を体系的に整理してからレポートを作成すること


## GitHub Investigator コマンドリファレンス

### 基本コマンド一覧

| 目的 | コマンド |
|------|---------|
| Issue 一覧検索 | `gh search issues "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated` |
| PR 一覧検索 | `gh search prs "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated` |
| コード検索 | `gh search code "KEYWORD" --repo OWNER/REPO --limit 10` |
| Issue 詳細 | `gh issue view NUM --repo OWNER/REPO --json title,body,state,author,labels,comments,createdAt,closedAt,url` |
| PR 詳細 | `gh pr view NUM --repo OWNER/REPO --json title,body,state,author,labels,comments,reviews,files,commits,mergedAt,url` |
| PR 差分 | `gh pr diff NUM --repo OWNER/REPO` |
| タイムライン | `gh api repos/OWNER/REPO/issues/NUM/timeline --paginate` |

### 検索修飾子

検索を絞り込むための修飾子。`gh search issues` と `gh search prs` で使える。

| 修飾子 | 例 | 用途 |
|--------|-----|------|
| ラベル | `gh search issues "KEYWORD label:bug" --repo OWNER/REPO` | 特定ラベルに絞り込み |
| 著者 | `gh search issues "KEYWORD author:USERNAME" --repo OWNER/REPO` | 特定ユーザーの投稿に絞り込み |
| 状態 | `gh search issues "KEYWORD state:open" --repo OWNER/REPO` | open/closed で絞り込み |
| 作成日 | `gh search issues "KEYWORD created:>2024-01-01" --repo OWNER/REPO` | 特定期間に絞り込み |
| コメント数 | `gh search issues "KEYWORD comments:>10" --repo OWNER/REPO` | 議論が活発なものに絞り込み |

### jq 加工パターン

`gh` の `--jq` オプションで JSON 出力を加工できる。パイプで `jq` や `python3` に渡す必要はない。

```bash
# コメント数だけ取得
gh issue view 123 --repo OWNER/REPO --json comments --jq '.comments | length'

# コメントの著者一覧（重複排除）
gh issue view 123 --repo OWNER/REPO --json comments --jq '[.comments[].author.login] | unique'

# PR で変更されたファイル名の一覧
gh pr view 456 --repo OWNER/REPO --json files --jq '.files[].path'

# 変更行数が多い順にファイルを表示
gh pr view 456 --repo OWNER/REPO --json files --jq '.files | sort_by(.additions + .deletions) | reverse | .[:5] | .[] | "\(.path) (+\(.additions)/-\(.deletions))"'

# 最新5件のコメント本文だけ取得
gh issue view 123 --repo OWNER/REPO --json comments --jq '.comments | .[-5:] | .[].body'
```

### Tips

- **レート制限**: GitHub Search API は認証済みで 30 req/min。大量検索時は `sleep 2` 等で間隔を空ける。HTTP 403 や 429 が返ったら 30秒以上待ってからリトライする。
- **大量コメントの扱い**: コメントが多い Issue/PR はまず件数を確認し、最新のコメントやリアクションが多いコメントを優先して読む。全件読もうとしない。
- **クロスリファレンスの追跡**: 議論は複数の Issue/PR に分散しがち。本文やコメント中の `#数字` を見逃さないが、調査目的に直結するものだけを追う。
- **巨大な diff**: 1000行を超える diff は全体を読む前に `files` JSON で影響範囲を確認し、関連するファイルだけ diff を取得する。
- **GraphQL の活用**: 複雑な検索が必要な場合は `gh api graphql` も使える。ただし通常の調査では REST API（`gh search` / `gh issue view` 等）で十分。

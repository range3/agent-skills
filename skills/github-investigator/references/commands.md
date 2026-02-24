- **レート制限**: GitHub Search API は認証済みで 30 req/min。大量検索時は `sleep 2` 等で間隔を空ける。HTTP 403 や 429 が返ったら 30秒以上待ってからリトライする。
- **大量コメントの扱い**: コメントが多い Issue/PR はまず件数を確認し、最新のコメントやリアクションが多いコメントを優先して読む。全件読もうとしない。
- **クロスリファレンスの追跡**: 議論は複数の Issue/PR に分散しがち。本文やコメント中の `#数字` を見逃さないが、調査目的に直結するものだけを追う。
- **巨大な diff**: 1000行を超える diff は全体を読む前に `files` JSON で影響範囲を確認し、関連するファイルだけ diff を取得する。
- **GraphQL の活用**: 複雑な検索が必要な場合は `gh api graphql` も使える。ただし通常の調査では REST API（`gh search` / `gh issue view` 等）で十分。

# GitHub Investigator コマンドリファレンス

## 目次
- [GitHub Investigator コマンドリファレンス](#github-investigator-コマンドリファレンス)
  - [目次](#目次)
  - [基本コマンド一覧](#基本コマンド一覧)
  - [検索修飾子](#検索修飾子)
  - [jq 加工パターン](#jq-加工パターン)
  - [Tips](#tips)

## 基本コマンド一覧

| 目的 | コマンド |
|------|---------|
| Issue 一覧検索 | `gh search issues "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated` |
| PR 一覧検索 | `gh search prs "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated` |
| コード検索 | `gh search code "KEYWORD" --repo OWNER/REPO --limit 10` |
| Issue 詳細 | `gh issue view NUM --repo OWNER/REPO --json title,body,state,author,labels,comments,createdAt,closedAt,url` |
| PR 詳細 | `gh pr view NUM --repo OWNER/REPO --json title,body,state,author,labels,comments,reviews,files,commits,mergedAt,url` |
| PR 差分 | `gh pr diff NUM --repo OWNER/REPO` |
| タイムライン | `gh api repos/OWNER/REPO/issues/NUM/timeline --paginate` |

## 検索修飾子

検索を絞り込むための修飾子。`gh search issues` と `gh search prs` で使える。

| 修飾子 | 例 | 用途 |
|--------|-----|------|
| ラベル | `gh search issues "KEYWORD label:bug" --repo OWNER/REPO` | 特定ラベルに絞り込み |
| 著者 | `gh search issues "KEYWORD author:USERNAME" --repo OWNER/REPO` | 特定ユーザーの投稿に絞り込み |
| 状態 | `gh search issues "KEYWORD state:open" --repo OWNER/REPO` | open/closed で絞り込み |
| 作成日 | `gh search issues "KEYWORD created:>2024-01-01" --repo OWNER/REPO` | 特定期間に絞り込み |
| コメント数 | `gh search issues "KEYWORD comments:>10" --repo OWNER/REPO` | 議論が活発なものに絞り込み |

## jq 加工パターン

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

## Tips

- **レート制限**: GitHub Search API は認証済みで 30 req/min。大量検索時は `sleep 2` 等で間隔を空ける。HTTP 403 や 429 が返ったら 30秒以上待ってからリトライする。
- **大量コメントの扱い**: コメントが多い Issue/PR はまず件数を確認し、最新のコメントやリアクションが多いコメントを優先して読む。全件読もうとしない。
- **クロスリファレンスの追跡**: 議論は複数の Issue/PR に分散しがち。本文やコメント中の `#数字` を見逃さないが、調査目的に直結するものだけを追う。
- **巨大な diff**: 1000行を超える diff は全体を読む前に `files` JSON で影響範囲を確認し、関連するファイルだけ diff を取得する。
- **GraphQL の活用**: 複雑な検索が必要な場合は `gh api graphql` も使える。ただし通常の調査では REST API（`gh search` / `gh issue view` 等）で十分。

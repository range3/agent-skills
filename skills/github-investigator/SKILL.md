---
name: github-investigator
description: >
  GitHub上の特定トピックに関するIssue・PR・コードの議論を調査し、要約レポートを作成するスキル。
  ghコマンドを使用する。ユーザーがGitHubリポジトリでの議論の調査、Issue/PRの横断的な分析、
  特定の機能・バグ・コンポーネントに関する経緯の把握、GitHubでの意思決定の追跡を求めた場合に使用すること。
  「このリポジトリで○○についてどんな議論がある？」「○○の経緯を調べて」「関連するIssueやPRをまとめて」
  「○○はなぜこういう設計になった？」といったリクエストにも対応する。
  明示的にGitHubと言及していなくても、OSSの機能議論や設計経緯の調査であればこのスキルを使う。
  ただし、機能の使い方・APIリファレンス・一般的な解説など、ドキュメントやコードを直接読めば
  分かる質問にはこのスキルを使わない（このスキルは「議論の経緯」「設計判断の背景」の調査用）。
allowed-tools:
  - Bash(gh *)
  - Bash(jq *)
---

# GitHub Investigator Skill

GitHub上である事柄（機能名、バグ、コンポーネント名など）についてどのような議論がされているかを `gh` CLI で調査し、要約レポートを生成する。

## JSON処理のルール

`gh` の出力を加工する際は、必ず `gh` に組み込まれた `--jq` フラグを使う。`| jq` や `| python3 -c ...` などのパイプは原則として使わない。

**理由**: このスキルは `gh *` を中心とした permission allowlist で動作する前提のため、パイプを含むコマンドは permission prompt で止まる可能性がある。`Bash(jq *)` も frontmatter に入れているが、現時点では Claude Code のパイプ判定にバグが残っており確実に通る保証がない。`--jq` 一発で完結させれば `gh *` パターンにそのままマッチして安定動作する。

```bash
# 良い例: --jq フラグを使う
gh issue view 123 --repo OWNER/REPO --json comments --jq '.comments | length'
gh issue view 123 --repo OWNER/REPO --json title,state --jq '"\(.title) [\(.state)]"'

# 悪い例（やらないこと）
gh issue view 123 --repo OWNER/REPO --json comments | jq '.comments | length'
gh issue view 123 --repo OWNER/REPO --json comments | python3 -c "import json, sys; ..."
```

### 複雑な変換が必要な場合

`--jq` 一発では難しいと感じても、次の順で対処する。パイプには逃げない。

1. **jq 式を頑張る**: `--jq` には `def`（関数定義）、`reduce`、`group_by`、複数行式など jq のほぼ全機能が使える。複雑な変換も1つの式で書けることが多い（具体例は末尾の補足リファレンス参照）。
2. **gh を複数回呼ぶ**: 多段処理は、1段目の出力を見てから2段目の `gh` 呼び出しを組み立てる。中間結果は `RESULT=$(gh ... --jq '...')` でシェル変数に格納できる（`gh *` パターンに合致する形を保てる）。
3. **諦めて報告**: それでも困難な場合は、生 JSON の概要だけ要約し、「より詳細な加工が必要」とユーザーに伝える。

**注記**: このルールは `allowed-tools` で `gh` と `jq` のみを許可していることに依存する。将来 allowlist を変更する場合はこのセクションも見直すこと。

## 前提条件

- `gh` CLI がインストール・認証済みであること
- 調査開始前に `gh auth status` で認証状態を確認し、未認証ならユーザーに案内する
- 対象リポジトリへのアクセス権があること（アクセス拒否された場合はその旨を報告し、パブリックリポジトリかどうかの確認を促す）

## 調査フロー

### Step 1: 調査対象の特定

ユーザーの依頼文から以下を推測し、不明な点だけ確認する。毎回すべてを聞く必要はない。

- **検索キーワード**: 調査したい事柄（例: `ECConnector`, `authentication`, `memory leak`）
- **対象リポジトリ**: 下記の手順で特定する
- **スコープ**: Issue のみ / PR のみ / 両方（デフォルト: 両方）

#### リポジトリの特定

次の順で判断する。ほとんどのケースは 1〜3 のいずれかで解決する。

1. **明示されている場合**: GitHub URL（`https://github.com/owner/repo`）、`owner/repo` 形式、`org/repo` 形式が依頼文に含まれていれば、そのまま使う。
2. **著名な OSS の名前が出ている場合**: `nodejs`, `vllm`, `rust`, `kubernetes`, `react` など、名前からリポジトリ位置が一意に決まるものは自分の知識で解決する（例: `vllm` → `vllm-project/vllm`、`rust` → `rust-lang/rust`）。
3. **マイナーな名前 / 知識にない場合**: web 検索でリポジトリを特定してから調査に入る（例: 「LMCache を調べて」→ "LMCache GitHub" で検索 → `LMCache/LMCache` を特定 → 以降の `gh` コマンドはこのリポジトリを対象に実行）。
4. **どうしても特定できない、または複数候補があって判断できない場合**: ユーザーに確認する。ただしこれは稀なケースで、デフォルトは 1〜3 で進めること。

#### デフォルト動作

リポジトリと検索キーワードが揃ったら、スコープは Issue + PR の両方で始める。曖昧な場合のみユーザーに確認する。

### Step 2: 全体像の把握（広く浅く）

いきなり個別の Issue に潜ると、重要な議論を見落としたり、特定の視点に偏ったりしやすい。最初に件数と傾向をつかんでから深掘りに移ることで、調査の網羅性と効率が上がる。

```bash
# Issue 検索
gh search issues "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated --order desc

# PR 検索
gh search prs "KEYWORD" --repo OWNER/REPO --limit 30 --sort updated --order desc
```

**レート制限への配慮**: GitHub Search API は認証済みで 30 requests/min。1回の調査で複数キーワードを連続検索する場合や、Step 3 で多数の Issue/PR を詳細取得する場合は、`sleep 2` 等で間隔を空ける。エラーになってから対処するより事前に間隔を空けた方が結果的に速い。

**結果が0件の場合**: キーワードが具体的すぎる可能性がある。類義語や上位概念に広げて再検索する（例: `ECConnector` → `connector`, `EC`）。それでも0件なら、そのトピックについてリポジトリ上で議論が行われていない旨を報告する。

**結果が多すぎる場合（50件超）**: ラベルや期間で絞り込む。`label:bug` や `created:>2024-01-01` などの修飾子を活用する（修飾子一覧は末尾の補足リファレンス参照）。

ここで一覧を眺め、以下のパターンを探す:
- 繰り返し登場する論点やキーワード
- 同じ人物が複数の Issue/PR に関与しているか
- open/closed の比率（未解決の割合が高いか）
- **クローズされたがマージされなかった PR の有無**: 「何が却下されたか」は設計判断の理解に直結する。見落としやすいので意識的にチェックする

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

**コンテキスト節約**: 本文やコメントが非常に長い場合（例: 1万文字超）は `--jq '.body[0:3000]'` のように先頭を切り出して読み、必要なら追加で読む。JSON 全文をそのまま処理せず、必要な部分だけ取り出すこと（自分のコンテキストを圧迫しないため）。

**PR の差分**: 差分が大きい場合は、まず `files` で影響範囲の概要を把握してから、必要なファイルだけ diff を確認する。1000行を超える差分は全体を読む前に必ず `files` JSON で範囲を確認すること。

```bash
# 差分が必要な場合
gh pr diff NUMBER --repo OWNER/REPO
```

### Step 4: 関連情報の補完（必要に応じて）

議論の経緯を正確に追うために、タイムラインや関連リソースが有用な場合がある。特に「なぜこの設計判断がなされたか」を追うときは複数のソースを組み合わせる。

#### タイムラインで経緯を追う

```bash
# Issue / PR のタイムライン（クロスリファレンスやラベル変更が含まれる）
gh api repos/OWNER/REPO/issues/NUMBER/timeline --paginate
```

#### Issue にひもづく PR を取得（GraphQL）

`gh issue view --json` には linked PRs が含まれない。確実に取得するにはタイムライン経由か GraphQL を使う。GraphQL のほうがノイズが少ない:

```bash
gh api graphql -f query='
  query($owner:String!, $repo:String!, $num:Int!) {
    repository(owner:$owner, name:$repo) {
      issue(number:$num) {
        title
        url
        timelineItems(itemTypes:[CROSS_REFERENCED_EVENT, CONNECTED_EVENT], first:20) {
          nodes {
            __typename
            ... on CrossReferencedEvent {
              willCloseTarget
              source { ... on PullRequest { number title state url } }
            }
            ... on ConnectedEvent {
              subject { ... on PullRequest { number title state url } }
            }
          }
        }
      }
    }
  }' -f owner=OWNER -f repo=REPO -F num=NUMBER
```

**フィールドの読み方**:
- `__typename`: イベント種別。`CrossReferencedEvent` は PR/Issue 本文での `#123` 参照、`ConnectedEvent` は GitHub UI の「Development」サイドバーから手動で link した場合に発生する
- `willCloseTarget` (`CrossReferencedEvent` のみ): `true` なら `Closes #X` / `Fixes #X` のように Issue を閉じる宣言付きの参照、`false` は単なる言及。レポートで「直接の解決関係」と「単なる言及」を区別したい時に使う
- `-F num=NUMBER` は Int として渡す必要がある（`-f` だと文字列扱いになり `Int!` の型チェックでエラーになる）。逆に `owner` / `repo` のような文字列引数は `-f` のほうが安全（リポジトリ名が数字に見える場合に `-F` だと誤って数値変換される）

#### コードの所在を把握

```bash
# 議論の前提となるコードの場所や使われ方を把握したいときに使う
gh search code "KEYWORD" --repo OWNER/REPO --limit 10
```

#### Issue/PR 以外の議論場所

リポジトリによっては設計議論が Issue/PR ではなく別の場所で行われている。次のいずれかが有効な場合がある。

- **GitHub Discussions**: 設計議論をここで行う OSS が増えている（Rust、Vite、Astro など）。
  ```bash
  gh api repos/OWNER/REPO/discussions
  ```
- **コミットメッセージ**: 「なぜこの実装になったか」の最終的な記録はコミット側にあることが多い。
  ```bash
  gh search commits "KEYWORD" --repo OWNER/REPO --limit 10
  ```
- **リリースノート / CHANGELOG**: 機能の登場・廃止の時系列把握に有用。
  ```bash
  gh release list --repo OWNER/REPO --limit 20
  gh release view TAG --repo OWNER/REPO
  ```

#### クロスリファレンスの追跡

コメントや本文中の `#123` や他リポジトリへの参照は、関連性が高ければ追跡する。特に以下のパターンに注目:
- `Closes #XX` / `Fixes #XX` — 直接の解決関係
- `Related to #XX` — 関連する議論
- `Depends on #XX` / `Blocked by #XX` — 依存関係

ただし、すべての参照を追う必要はない。調査目的に直結するものだけを選ぶ。

### Step 5: レポート作成

調査結果の規模に応じて適切なフォーマットを選ぶ。少数の Issue/PR しかない場合に大仰なレポートを作ると冗長になり、逆に多数の議論がある場合に簡潔すぎると情報が失われる。判断の目安は「ユーザーが結果を頭に入れられる量か」。

**小規模（該当 5 件以下、またはユーザーが一覧を一目で把握できる量）**: 簡潔にまとめる。エグゼクティブサマリーと関連リンクだけでも十分。

**中〜大規模（該当 6 件以上）**: 以下のテンプレートに沿って構造化する。

```markdown
# GitHub 調査レポート: [キーワード]

## 調査概要
- 対象リポジトリ: ...
- 検索キーワード: ...
- 調査日: ...
- 該当 Issue 数: X件 (open: X / closed: X)
- 該当 PR 数: X件 (open: X / merged: X / closed-not-merged: X)

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

## 却下された案・代替案（あれば）
- closed-not-merged な PR や、議論の中で却下された方針

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
| レート制限エラー (HTTP 403/429) | GitHub Search API は認証済みで 30 req/min が上限。403/429 が返ったら 30 秒以上待ってからリトライ。連続で発生する場合はユーザーに報告 |
| コメントが100件超 | 全件読まない。最新10件 + リアクション上位を優先 |
| diff が巨大（1000行超） | `files` で概要を先に把握し、関連ファイルだけ diff を見る |

## 補足

この調査では多くの情報を統合する必要があるため、結論を急がず、収集した情報を体系的に整理してからレポートを作成すること。

---

## 補足リファレンス

本文のステップでは主要なコマンドをインラインで示している。ここでは本文に書ききれなかった補足情報をまとめる。

### 検索修飾子

`gh search issues` と `gh search prs` で使える絞り込み修飾子。

| 修飾子 | 例 | 用途 |
|--------|-----|------|
| ラベル | `gh search issues "KEYWORD label:bug" --repo OWNER/REPO` | 特定ラベルに絞り込み |
| 著者 | `gh search issues "KEYWORD author:USERNAME" --repo OWNER/REPO` | 特定ユーザーの投稿に絞り込み |
| 状態 | `gh search issues "KEYWORD state:open" --repo OWNER/REPO` | open/closed で絞り込み |
| 作成日 | `gh search issues "KEYWORD created:>2024-01-01" --repo OWNER/REPO` | 特定期間に絞り込み |
| コメント数 | `gh search issues "KEYWORD comments:>10" --repo OWNER/REPO` | 議論が活発なものに絞り込み |

### jq 加工パターン

`--jq` で使える典型的なフィルタ式。複雑な変換が必要な場合も、原則として `--jq` 一発で完結させる。

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

# 関数定義を含む複雑な変換（--jq でも def や reduce が使える）
gh pr view 456 --repo OWNER/REPO --json reviews --jq '
  def state_label: if . == "APPROVED" then "✓" elif . == "CHANGES_REQUESTED" then "✗" else "·" end;
  .reviews | group_by(.author.login) | map({user: .[0].author.login, last: .[-1].state | state_label})
'
```

### GraphQL を使う場合

通常の調査は REST API（`gh search` / `gh issue view` 等）で十分だが、Issue にひもづく PR の取得や、複数オブジェクトの関連を一度に取得したいケースは `gh api graphql` を使う（具体例は Step 4 を参照）。

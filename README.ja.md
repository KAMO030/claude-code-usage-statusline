# Claude Code 使用量ステータスライン

[简体中文](README.md) · [English](README.en.md) · **日本語**

[Claude Code](https://claude.com/claude-code) のターミナル下部に**常時表示**:モデル · コンテキスト使用量 · ターンごとのトークン · **プラン残量** · セッション料金。Python 標準ライブラリのみ、**依存ゼロ**(node/npm 不要)。

```
⚡Opus 4.8 | ctx 38.1k/200.0k 19%(剩81%) | ⬆38.1k ⬇3.8k | 5h剩93%↻4h 7d剩66% | $0.342
```

---

## 🚀 インストール(3 ステップ)

**ステップ 1 · スクリプトを配置**

```bash
# 方法 A:クローンしてコピー
git clone https://github.com/lonelymeko/claude-code-usage-statusline.git
cp claude-code-usage-statusline/statusline.py ~/.claude/statusline.py

# 方法 B:単一ファイルを直接ダウンロード
curl -fsSL https://raw.githubusercontent.com/lonelymeko/claude-code-usage-statusline/main/statusline.py -o ~/.claude/statusline.py

chmod +x ~/.claude/statusline.py
```

**ステップ 2 · `~/.claude/settings.json` に登録**

`statusLine` フィールドを追加(既存の内容があればマージ):

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/statusline.py",
    "padding": 0
  }
}
```

**ステップ 3 · リロード**

Claude Code を再起動するか、セッションで `/statusline` を実行してリロード。下部にバーが表示されます ✅

> **前提条件**:`python3` が `PATH` にあること、Claude Code にログイン済み(= `~/.claude/.credentials.json` が存在)。Claude Code `2.1.x` で動作確認。
> 初回レンダリング時、残量セグメントは約 1 秒かかる場合があります(バックグラウンド取得)。キャッシュを即時生成するには:`python3 ~/.claude/statusline.py --refresh`

---

## 表示内容

| セグメント | 意味 | データ元 |
|---|---|---|
| `⚡Opus 4.8` | 現在のモデル | statusLine の stdin |
| `ctx 38.1k/200.0k 19%(剩81%)` | **コンテキストウィンドウ** 使用/合計/使用%/残り%、使用率で緑→黄→赤 | 現セッションの transcript |
| `⬆38.1k ⬇3.8k` | 直近ターンの入力/出力トークン | 現セッションの transcript |
| `5h剩93%↻4h 7d剩66%` | **プラン残量** — 5 時間枠(リセットまでのカウントダウン付き)+ 7 日枠の残り。上限が近いと黄/赤 | `GET /api/oauth/usage` |
| `$0.342` | 現セッションの料金(USD) | statusLine の stdin |

> `剩`(残り)と `↻`(リセット)はコンパクトに表記しています。英語表記にしたい場合は `usage_segment()` を編集してください。

---

## 仕組み

### なぜ skill ではなく statusLine?
skill(`SKILL.md`)は Claude がオンデマンドで読み込むドキュメントで、ターミナルバーを**常時描画できず**、`/usage` のようなスラッシュコマンドも実行できません。Claude Code で常駐バーを描けるのは [`statusLine`](https://code.claude.com/docs/en/statusline) 設定だけ — レンダリングのたびに実行され、出力が画面下部に表示される shell コマンドです。本プロジェクトがその コマンドです。

### プラン残量はどこから?
Claude Code の `/usage` は認証付きエンドポイントからサブスクリプション使用量を取得します。このステータスラインも同じものを呼びます:

```
GET https://api.anthropic.com/api/oauth/usage
Authorization: Bearer <accessToken>      # ~/.claude/.credentials.json から取得
anthropic-beta: oauth-2025-04-20
anthropic-version: 2023-06-01
```

レスポンスには `five_hour` と `seven_day` が含まれ、それぞれ `utilization`(使用%)と `resets_at`(リセット時刻)を持ちます。残り = `100 - utilization`。

> **プライバシー**:スクリプトはマシン上の既存 OAuth トークンを使って `api.anthropic.com` にアクセスし、**自分自身**の使用量を取得するだけです。第三者へのデータ送信は一切ありません。全ロジックは約 150 行の [`statusline.py`](statusline.py) に収まっています。

### エンドポイントを叩きすぎない?
叩きません。ステータスラインは非常に高頻度でレンダリングされる(入力中は毎秒数回)ため:
- 残量結果は `~/.claude/usage-cache.json` に **60 秒 TTL** でキャッシュ;
- レンダリングは**キャッシュを読むだけ** — 即時・ブロックなし;
- 古くなったら**デタッチされたバックグラウンドプロセス**(`statusline.py --refresh`)が次回用に更新;
- トークン期限切れやネットワーク障害時は、直近のキャッシュを静かに保持(トークンは Claude Code 自身が更新)。

### コンテキスト/トークンの計算
現セッションの transcript(stdin の `transcript_path`)から直近メッセージの `usage` を解析:
```
コンテキスト使用 = input_tokens + cache_read_input_tokens + cache_creation_input_tokens
```
ウィンドウサイズは既定 `200000`、Claude Code が `exceeds_200k_tokens` を報告すると自動で `1000000` に切替。

---

## 設定

`statusline.py` 先頭の定数を編集:

| 定数 | 既定 | 効果 |
|---|---|---|
| `TTL` | `60` | プラン残量キャッシュの更新間隔(秒) |
| `LANG_OVERRIDE` | `""`(自動) | 表示言語、下記参照 |

### 🌐 言語

表示言語は**既定でシステムに追従**(`LC_ALL` → `LC_MESSAGES` → `LANG` を読む)、設定不要。対応:

| 値 | 言語 | 例 |
|---|---|---|
| `zh` | 简体中文 | `ctx …(剩81%) · 5h剩93% · 7d剩66%` |
| `en` | English(フォールバック) | `ctx …(81% left) · 5h 93% left · 7d 66% left` |
| `ja` | 日本語 | `ctx …(残81%) · 5h残93% · 7d残66%` |

> システム言語を認識できない場合は `en` にフォールバック。ローカライズされるのはラベル(残り/リセット)のみで、数値とモデル名はそのままです。

**言語を固定する**方法は 2 つ:

- スクリプト先頭の定数を編集:`LANG_OVERRIDE = "ja"`
- または `settings.json` のコマンドに環境変数を追加(最優先):
  ```json
  "command": "CC_STATUSLINE_LANG=en python3 ~/.claude/statusline.py"
  ```

優先順位:`CC_STATUSLINE_LANG` 環境変数 > `LANG_OVERRIDE` 定数 > システム言語 > `en`。

### その他

セグメントを減らしたい場合、`main()` 内の各 `parts.append(...)` は独立しているので不要な行を削除。プランを**残り%**ではなく**使用%**にするには、`usage_segment()` の `100 - utilization` を `utilization` に戻します。

## トラブルシューティング

- **初回に残量セグメントが出ない** — キャッシュ未生成のため。バックグラウンド更新完了後 1 秒以内に表示。即時生成:`python3 ~/.claude/statusline.py --refresh`。
- **残量セグメントが全く出ない** — `cat ~/.claude/usage-cache.json` を確認。空/不在なら上記 `--refresh` を実行し、`refresh_usage()` の `except: pass` を一時的に外してエラーを確認。
- **コンテキストウィンドウサイズが違う** — 1M トークン beta 使用時は、Claude Code の `exceeds_200k_tokens` フラグに自動追従します。

## ライセンス

[MIT](LICENSE)

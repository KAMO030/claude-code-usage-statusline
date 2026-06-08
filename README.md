# Claude Code Usage StatusLine

A zero-dependency status line for [Claude Code](https://claude.com/claude-code) that shows, right in your terminal, **at all times**:

```
⚡Opus 4.8 | ctx 38.1k/200.0k 19%(剩81%) | ⬆38.1k ⬇3.8k | 5h剩93%↻4h 7d剩66% | $0.342
```

| Segment | Meaning | Source |
|---|---|---|
| `⚡Opus 4.8` | Active model | statusLine stdin |
| `ctx 38.1k/200.0k 19%(剩81%)` | **Context window** used / total / used% / remaining%, color-coded | current session transcript |
| `⬆38.1k ⬇3.8k` | Input / output tokens of the last turn | current session transcript |
| `5h剩93%↻4h 7d剩66%` | **Plan quota remaining** — 5-hour window (with reset countdown) and 7-day window | `GET /api/oauth/usage` (the same endpoint `/usage` uses) |
| `$0.342` | Cost of the current session (USD) | statusLine stdin |

Colors shift green → yellow → red as a budget runs low, so you can see at a glance how much context and how much of your subscription quota is left.

> Pure Python 3, standard library only. No `node`, no `npm`, no external packages.

---

## Why a status line and not a "skill"?

A Skill (`SKILL.md`) is a document Claude loads on demand — it **cannot** persistently render the terminal bar, and it cannot run a slash command like `/usage`. The only mechanism in Claude Code that draws a live, always-on bar is the [`statusLine`](https://code.claude.com/docs/en/statusline) setting: a shell command Claude Code runs on every render and prints to the bottom of the screen. This project is that command.

## How the plan-quota part works

`/usage` inside Claude Code fetches your subscription utilization from an authenticated endpoint. This status line calls the same one:

```
GET https://api.anthropic.com/api/oauth/usage
Authorization: Bearer <accessToken>      # read from ~/.claude/.credentials.json
anthropic-beta: oauth-2025-04-20
anthropic-version: 2023-06-01
```

The response contains `five_hour` and `seven_day` objects, each with a `utilization` percentage and a `resets_at` timestamp. Remaining = `100 - utilization`.

Because a status line renders very frequently (multiple times per second while you type), it would be wasteful and slow to hit the network every time. So:

- The result is cached in `~/.claude/usage-cache.json` with a **60-second TTL**.
- Rendering only ever **reads the cache** — it is instant and never blocks.
- When the cache is stale, a **detached background process** (`statusline.py --refresh`) updates it for next time.
- If the token is expired or the network fails, the last-known cache is kept silently (Claude Code refreshes the OAuth token on its own).

> **Privacy:** the script only ever talks to `api.anthropic.com` using the OAuth token already on your machine, to fetch *your own* usage. Nothing is sent anywhere else. Read the ~150 lines of [`statusline.py`](statusline.py) — that's the whole thing.

## How the context / token part works

The script parses your current session transcript (`transcript_path`, provided on stdin) and reads the last message's `usage` block:

```
context used = input_tokens + cache_read_input_tokens + cache_creation_input_tokens
```

That sum is the real number of tokens occupying the context window. The window size defaults to `200000`, and switches to `1000000` automatically when Claude Code reports `exceeds_200k_tokens`.

---

## Install

**1. Get the script**

```bash
git clone https://github.com/lonelymeko/claude-code-usage-statusline.git
# or just download statusline.py
cp claude-code-usage-statusline/statusline.py ~/.claude/statusline.py
chmod +x ~/.claude/statusline.py
```

**2. Point Claude Code at it** — add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/statusline.py",
    "padding": 0
  }
}
```

**3. Reload** — restart Claude Code, or run `/statusline` to reload. The bar appears at the bottom.

> Requires `python3` on your `PATH` and a logged-in Claude Code (so `~/.claude/.credentials.json` exists). Tested on Claude Code `2.1.x`.

## Configuration

Edit the constants at the top of `statusline.py`:

| Constant | Default | Effect |
|---|---|---|
| `TTL` | `60` | Seconds before the plan-quota cache is refreshed |

Want to trim segments? Each piece is built independently in `main()` — delete the `parts.append(...)` line you don't want. To show **used%** instead of **remaining%** for the plan, change `100 - utilization` back to `utilization` in `usage_segment()`.

## Troubleshooting

- **No quota segment on first render** — the cache doesn't exist yet; it appears within a second once the background refresh finishes. Force it once with `python3 ~/.claude/statusline.py --refresh`.
- **Quota segment never appears** — check `cat ~/.claude/usage-cache.json`. If it's missing/empty, run the `--refresh` command above and read any error by temporarily removing the `except: pass` in `refresh_usage()`.
- **Wrong context window size** — if you use the 1M-token beta, the script follows Claude Code's `exceeds_200k_tokens` flag automatically.

## License

MIT — see [LICENSE](LICENSE).

---

### 中文说明

在 Claude Code 终端底部**常驻显示**:模型 · 上下文占用/剩余 · 本轮 token 上下行 · **套餐额度**(5 小时窗 + 7 天窗剩余，带重置倒计时) · 本次会话花费。纯 Python 标准库，零依赖。

- **为什么不是 skill?** skill 是按需加载的文档，无法常驻渲染终端，也无法执行 `/usage` 这类 slash 命令。能画常驻状态栏的只有 `statusLine`(settings.json 里的一条 shell 命令)。
- **额度怎么来的?** 调 `/usage` 同款接口 `GET /api/oauth/usage`，token 取自本机 `~/.claude/.credentials.json`，只查你自己的额度、不外传。
- **会不会刷爆接口?** 不会。额度结果缓存 `~/.claude/usage-cache.json`(60s TTL)，渲染只读缓存(瞬时不阻塞)，过期时后台异步刷新；token 过期则静默保留旧值。

安装见上方 Install 三步:拷贝脚本 → 在 `settings.json` 配 `statusLine` → 重启或 `/statusline` 重载。

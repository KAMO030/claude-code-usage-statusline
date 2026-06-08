# Claude Code Usage StatusLine

[简体中文](README.md) · **English** · [日本語](README.ja.md)

A zero-dependency status line for [Claude Code](https://claude.com/claude-code) that **always** shows, in your terminal: model · context usage · per-turn tokens · **plan quota** · session cost. Pure Python standard library — **no node, no npm**.

```
⚡Opus 4.8 | ctx 38.1k/200.0k 19%(剩81%) | ⬆ 38.1k  ⬇ 3.8k | 5h剩93%↻15:50 7d剩66%↻06-11 04:00 | $0.342
```

---

## 🚀 Install (3 steps)

**Step 1 · Place the script**

```bash
# Option A: clone and copy
git clone https://github.com/lonelymeko/claude-code-usage-statusline.git
cp claude-code-usage-statusline/statusline.py ~/.claude/statusline.py

# Option B: download the single file
curl -fsSL https://raw.githubusercontent.com/lonelymeko/claude-code-usage-statusline/main/statusline.py -o ~/.claude/statusline.py

chmod +x ~/.claude/statusline.py
```

**Step 2 · Wire it into `~/.claude/settings.json`**

Add the `statusLine` field (merge it in if the file already has content):

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/statusline.py",
    "padding": 0
  }
}
```

**Step 3 · Reload**

Restart Claude Code, or run `/statusline` in a session to reload. The bar appears at the bottom ✅

> **Requirements:** `python3` on your `PATH`; a logged-in Claude Code (so `~/.claude/.credentials.json` exists). Tested on Claude Code `2.1.x`.
> On the very first render the quota segment may take ~1s (background fetch). To populate the cache immediately: `python3 ~/.claude/statusline.py --refresh`

---

## What it shows

| Segment | Meaning | Source |
|---|---|---|
| `⚡Opus 4.8` | Active model | statusLine stdin |
| `ctx 38.1k/200.0k 19%(剩81%)` | **Context window** used / total / used% / remaining%, color-coded green→yellow→red | current session transcript |
| `⬆ 38.1k  ⬇ 3.8k` | Input / output tokens of the last turn | current session transcript |
| `5h剩93%↻15:50 7d剩66%↻06-11 04:00` | **Plan quota** — 5-hour and 7-day windows remaining, each with its reset time (`↻`); turns yellow/red near the limit | `GET /api/oauth/usage` |
| `$0.342` | Cost of the current session (USD) | statusLine stdin |

> The labels `剩` (remaining) and `↻` (reset) are kept compact; rename them in `usage_segment()` if you prefer English text.

---

## How it works

### Why a status line, not a "skill"?
A Skill (`SKILL.md`) is a document Claude loads on demand — it **cannot** persistently render the terminal bar, and it cannot run a slash command like `/usage`. The only mechanism in Claude Code that draws a live, always-on bar is the [`statusLine`](https://code.claude.com/docs/en/statusline) setting: a shell command Claude Code runs on every render and prints to the bottom of the screen. This project is that command.

### Where the plan quota comes from
`/usage` inside Claude Code fetches your subscription utilization from an authenticated endpoint. This status line calls the same one:

```
GET https://api.anthropic.com/api/oauth/usage
Authorization: Bearer <accessToken>      # read from ~/.claude/.credentials.json
anthropic-beta: oauth-2025-04-20
anthropic-version: 2023-06-01
```

The response contains `five_hour` and `seven_day`, each with a `utilization` percentage and a `resets_at` timestamp. Remaining = `100 - utilization`.

> **Privacy:** the script only talks to `api.anthropic.com` using the OAuth token already on your machine, to fetch *your own* usage. Nothing is sent to any third party. The whole thing is ~150 lines in [`statusline.py`](statusline.py).

### Won't it hammer the endpoint?
No. A status line renders very frequently (several times per second while you type), so:
- the result is cached in `~/.claude/usage-cache.json` with a **60-second TTL**;
- rendering only ever **reads the cache** — instant, never blocks;
- when stale, a **detached background process** (`statusline.py --refresh`) updates it for next time;
- if the token is expired or the network fails, the last-known cache is kept silently (Claude Code refreshes the OAuth token on its own).

### Context / token math
The script parses the last message's `usage` from the current session transcript (`transcript_path`, given on stdin):
```
context used = input_tokens + cache_read_input_tokens + cache_creation_input_tokens
```
The window size defaults to `200000` and switches to `1000000` automatically when Claude Code reports `exceeds_200k_tokens`.

---

## Configuration

Edit the constants at the top of `statusline.py`:

| Constant | Default | Effect |
|---|---|---|
| `TTL` | `60` | Seconds before the plan-quota cache is refreshed |
| `LANG_OVERRIDE` | `""` (auto) | Display language, see below |
| `RESET_STYLE` | `"clock"` | 5h/7d reset display: `clock` reset time (e.g. `↻15:50`; cross-day adds date `↻06-11 04:00`) / `countdown` (`↻3h`) / `both` (`↻15:50(3h)`) / `off` |

### 🌐 Language

The display language **follows your system by default** (reads `LC_ALL` → `LC_MESSAGES` → `LANG`); no setup needed. 10 languages supported:

| Value | Language | Example (remaining) |
|---|---|---|
| `zh` | 简体中文 | `(剩81%) · 5h剩93%` |
| `zh-TW` | 繁體中文 | `(剩81%) · 5h剩93%` |
| `en` | English (fallback) | `(81% left) · 5h 93% left` |
| `ja` | 日本語 | `(残81%) · 5h残93%` |
| `ko` | 한국어 | `(81% 남음) · 5h 93% 남음` |
| `es` | Español | `(81% rest.) · 5h 93% rest.` |
| `fr` | Français | `(81% rest.) · 5h 93% rest.` |
| `de` | Deutsch | `(81% übrig) · 5h 93% übrig` |
| `pt` | Português | `(81% rest.) · 5h 93% rest.` |
| `ru` | Русский | `(ост. 81%) · 5h ост. 93%` |

> Falls back to `en` when the system language isn't recognized; Traditional vs Simplified Chinese is picked via `zh_TW`/`zh_HK`/`Hant`. Only the labels (remaining/reset) are localized; numbers and the model name stay as-is.

**To force a language**, two ways:

- Edit the constant at the top of the script: `LANG_OVERRIDE = "ja"`
- Or add an env var in the `settings.json` command (highest priority):
  ```json
  "command": "CC_STATUSLINE_LANG=en python3 ~/.claude/statusline.py"
  ```

Priority: `CC_STATUSLINE_LANG` env var > `LANG_OVERRIDE` constant > system language > `en`.

### Other

Want fewer segments? Each piece is an independent `parts.append(...)` in `main()` — delete the line you don't want. To show **used%** instead of **remaining%** for the plan, change `100 - utilization` back to `utilization` in `usage_segment()`.

## Troubleshooting

- **No quota segment on first render** — the cache doesn't exist yet; it appears within a second once the background refresh finishes. Force it with `python3 ~/.claude/statusline.py --refresh`.
- **Quota segment never appears** — check `cat ~/.claude/usage-cache.json`. If missing/empty, run the `--refresh` command above and temporarily remove the `except: pass` in `refresh_usage()` to see the error.
- **Wrong context window size** — with the 1M-token beta, the script follows Claude Code's `exceeds_200k_tokens` flag automatically.

## License

[MIT](LICENSE)

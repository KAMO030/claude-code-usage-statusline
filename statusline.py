#!/usr/bin/env python3
"""Claude Code statusLine:实时显示 context 占用 / token 用量 / 套餐额度 / 会话花费。

- ctx / token:解析当前会话 transcript(本地、瞬时)。
- 套餐额度:读 ~/.claude/usage-cache.json;缓存超 TTL 时后台异步刷新
  (调用 /usage 同款接口 GET /api/oauth/usage),渲染永不阻塞。
用法:
  默认            渲染状态栏(读 stdin JSON)
  --refresh       后台模式:打接口写缓存(由脚本自己 fork 调用)
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
CRED = os.path.join(HOME, ".claude", ".credentials.json")
CACHE = os.path.join(HOME, ".claude", "usage-cache.json")
SELF = os.path.abspath(__file__)
TTL = 60  # 秒;额度缓存有效期

# ---------- 语言 ----------
# 显示语言。留空 "" = 自动读系统语言(LC_ALL/LC_MESSAGES/LANG)。
# 想强制:把它设为 "zh" / "en" / "ja",或设环境变量 CC_STATUSLINE_LANG。
LANG_OVERRIDE = ""

I18N = {
    "zh": {"ctx_rem": "(剩{rem:.0f}%)", "win": "{label}剩{rem:.0f}%", "soon": "即将"},
    "en": {"ctx_rem": "({rem:.0f}% left)", "win": "{label} {rem:.0f}% left", "soon": "soon"},
    "ja": {"ctx_rem": "(残{rem:.0f}%)", "win": "{label}残{rem:.0f}%", "soon": "間もなく"},
}

def detect_lang():
    v = os.environ.get("CC_STATUSLINE_LANG") or LANG_OVERRIDE
    if not v:
        for e in ("LC_ALL", "LC_MESSAGES", "LANG"):
            if os.environ.get(e):
                v = os.environ[e]
                break
    v = (v or "en").lower()
    if v.startswith("zh"):
        return "zh"
    if v.startswith("ja"):
        return "ja"
    return "en"

T = I18N[detect_lang()]

# ---------- ANSI ----------
def c(code, s):
    return f"\033[{code}m{s}\033[0m"

DIM, RED, GREEN, YELLOW, CYAN = "2", "31", "32", "33", "36"

def human(n):
    n = int(n)
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}k"
    return str(n)

def remain_color(rem):
    if rem <= 15:
        return RED
    if rem <= 40:
        return YELLOW
    return GREEN

# ---------- 额度:后台刷新 ----------
def refresh_usage():
    try:
        with open(CRED) as f:
            tok = json.load(f)["claudeAiOauth"]["accessToken"]
        req = urllib.request.Request(
            "https://api.anthropic.com/api/oauth/usage",
            headers={
                "Authorization": f"Bearer {tok}",
                "anthropic-beta": "oauth-2025-04-20",
                "anthropic-version": "2023-06-01",
                "User-Agent": "claude-cli/statusline",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.load(r)
        data["_fetched_at"] = time.time()
        tmp = CACHE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, CACHE)
    except Exception:
        # 失败(如 token 过期)就保留旧缓存,不报错
        pass

def maybe_spawn_refresh():
    fresh = False
    try:
        fresh = (time.time() - os.path.getmtime(CACHE)) < TTL
    except OSError:
        fresh = False
    if not fresh:
        try:
            subprocess.Popen(
                [sys.executable, SELF, "--refresh"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception:
            pass

def fmt_reset(iso):
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        delta = t - datetime.now(timezone.utc)
        mins = int(delta.total_seconds() // 60)
        if mins <= 0:
            return T["soon"]
        if mins < 60:
            return f"{mins}m"
        h = mins // 60
        if h < 24:
            return f"{h}h"
        return f"{h//24}d"
    except Exception:
        return ""

def usage_segment():
    maybe_spawn_refresh()
    try:
        with open(CACHE) as f:
            u = json.load(f)
    except Exception:
        return None  # 还没缓存(首次渲染),下次就有了
    out = []
    fh = u.get("five_hour") or {}
    sd = u.get("seven_day") or {}
    if fh.get("utilization") is not None:
        rem = 100 - fh["utilization"]
        rst = fmt_reset(fh.get("resets_at", ""))
        s = T["win"].format(label="5h", rem=rem)
        if rst:
            s += c(DIM, f"↻{rst}")
        out.append(c(remain_color(rem), s))
    if sd.get("utilization") is not None:
        rem = 100 - sd["utilization"]
        out.append(c(remain_color(rem), T["win"].format(label="7d", rem=rem)))
    return " ".join(out) if out else None

# ---------- context:解析 transcript ----------
def ctx_tokens(transcript):
    used = out = 0
    if transcript and os.path.exists(transcript):
        try:
            last = None
            with open(transcript, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        usage = (json.loads(line).get("message") or {}).get("usage")
                    except Exception:
                        continue
                    if usage:
                        last = usage
            if last:
                used = (last.get("input_tokens", 0) or 0) \
                     + (last.get("cache_read_input_tokens", 0) or 0) \
                     + (last.get("cache_creation_input_tokens", 0) or 0)
                out = last.get("output_tokens", 0) or 0
        except Exception:
            pass
    return used, out

# ---------- 主渲染 ----------
def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--refresh":
        refresh_usage()
        return

    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    model = (data.get("model") or {}).get("display_name") or "Claude"
    cost = (data.get("cost") or {}).get("total_cost_usd")
    ctx_max = 1_000_000 if data.get("exceeds_200k_tokens") else 200_000
    used, out = ctx_tokens(data.get("transcript_path") or "")

    pct = (used / ctx_max * 100) if ctx_max else 0
    rem = max(0, 100 - pct)
    ctx_col = RED if pct >= 85 else (YELLOW if pct >= 60 else GREEN)

    parts = [c(CYAN, f"⚡{model}")]
    parts.append(c(ctx_col, f"ctx {human(used)}/{human(ctx_max)} {pct:.0f}%") + c(DIM, T["ctx_rem"].format(rem=rem)))
    if used or out:
        parts.append(c(DIM, f"⬆{human(used)} ⬇{human(out)}"))
    seg = usage_segment()
    if seg:
        parts.append(seg)
    if cost is not None:
        parts.append(c(GREEN, f"${cost:.3f}"))

    print(c(DIM, " | ").join(parts))

if __name__ == "__main__":
    main()

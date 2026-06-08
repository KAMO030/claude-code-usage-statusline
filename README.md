# Claude Code 用量状态栏 · Usage StatusLine

**简体中文** · [English](README.en.md) · [日本語](README.ja.md)

在 [Claude Code](https://claude.com/claude-code) 终端底部**常驻显示**:模型 · 上下文占用 · 本轮 token · **套餐额度** · 会话花费。纯 Python 标准库,**零依赖**(无需 node/npm)。

```
⚡Opus 4.8 | ctx 38.1k/200.0k 19%(剩81%) | ⬆38.1k ⬇3.8k | 5h剩93%↻4h 7d剩66% | $0.342
```

---

## 🚀 安装(三步)

**第 1 步 · 放置脚本**

```bash
# 方式 A:克隆仓库后复制
git clone https://github.com/lonelymeko/claude-code-usage-statusline.git
cp claude-code-usage-statusline/statusline.py ~/.claude/statusline.py

# 方式 B:直接下载单文件
curl -fsSL https://raw.githubusercontent.com/lonelymeko/claude-code-usage-statusline/main/statusline.py -o ~/.claude/statusline.py

chmod +x ~/.claude/statusline.py
```

**第 2 步 · 在 `~/.claude/settings.json` 里挂上**

加入 `statusLine` 字段(若文件已有内容,只需把这段并进去):

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/statusline.py",
    "padding": 0
  }
}
```

**第 3 步 · 重载**

重启 Claude Code,或在会话里输入 `/statusline` 重载。底部状态栏立即出现 ✅

> **前置条件**:`python3` 在 PATH 中;已登录 Claude Code(即 `~/.claude/.credentials.json` 存在)。测试于 Claude Code `2.1.x`。
> 首次渲染时额度段可能要等 1 秒(后台拉取);想立刻生成缓存可手动跑一次:`python3 ~/.claude/statusline.py --refresh`

---

## 显示内容

| 段 | 含义 | 数据来源 |
|---|---|---|
| `⚡Opus 4.8` | 当前模型 | statusLine 输入 |
| `ctx 38.1k/200.0k 19%(剩81%)` | **上下文窗口** 已用/总量/已用%/剩余%,按占用率绿→黄→红 | 当前会话 transcript |
| `⬆38.1k ⬇3.8k` | 本轮输入/输出 token | 当前会话 transcript |
| `5h剩93%↻4h 7d剩66%` | **套餐额度** — 5 小时窗(带重置倒计时)+ 7 天窗剩余,临近上限变黄/红 | `GET /api/oauth/usage` |
| `$0.342` | 本次会话花费(美元) | statusLine 输入 |

---

## 原理

### 为什么是 statusLine,不是 skill?
skill(`SKILL.md`)是 Claude 按需加载的文档,**无法常驻渲染终端**,也无法执行 `/usage` 这类 slash 命令。Claude Code 里唯一能画常驻状态栏的是 [`statusLine`](https://code.claude.com/docs/en/statusline) 配置——一条每次渲染都会执行、输出打印到底部的 shell 命令。本项目就是这条命令。

### 套餐额度怎么来的?
Claude Code 的 `/usage` 从一个鉴权接口拉取订阅用量,本状态栏调的是同一个:

```
GET https://api.anthropic.com/api/oauth/usage
Authorization: Bearer <accessToken>      # 取自 ~/.claude/.credentials.json
anthropic-beta: oauth-2025-04-20
anthropic-version: 2023-06-01
```

返回含 `five_hour` 与 `seven_day`,各带 `utilization`(已用%)和 `resets_at`(重置时间)。剩余 = `100 - utilization`。

> **隐私**:脚本只用你本机已有的 OAuth token 访问 `api.anthropic.com` 查**你自己**的用量,不向任何第三方发送数据。全部逻辑就在约 150 行的 [`statusline.py`](statusline.py) 里。

### 会不会刷爆接口?
不会。状态栏渲染极其频繁(打字时每秒多次),所以:
- 额度结果缓存于 `~/.claude/usage-cache.json`,**60 秒 TTL**;
- 渲染**只读缓存**,瞬时返回、永不阻塞;
- 缓存过期时,**detach 的后台进程**(`statusline.py --refresh`)更新它供下次使用;
- token 过期或断网时,静默保留旧缓存(Claude Code 自己会刷新 token)。

### 上下文/token 怎么算?
解析当前会话 transcript(stdin 给的 `transcript_path`)最后一条消息的 `usage`:
```
上下文占用 = input_tokens + cache_read_input_tokens + cache_creation_input_tokens
```
窗口大小默认 `200000`,当 Claude Code 报告 `exceeds_200k_tokens` 时自动切到 `1000000`。

---

## 配置

改 `statusline.py` 顶部常量:

| 常量 | 默认 | 作用 |
|---|---|---|
| `TTL` | `60` | 额度缓存刷新间隔(秒) |

想精简段落?`main()` 里每段都是独立的 `parts.append(...)`,删掉不想要的那行即可。想把套餐**剩余%**改回**已用%**,把 `usage_segment()` 里的 `100 - utilization` 改回 `utilization`。

## 排障

- **首次没有额度段** — 缓存还没生成,后台刷新完成后 1 秒内出现。可手动:`python3 ~/.claude/statusline.py --refresh`。
- **额度段一直不出现** — 看 `cat ~/.claude/usage-cache.json`。若为空/缺失,跑上面的 `--refresh`,并临时去掉 `refresh_usage()` 里的 `except: pass` 看报错。
- **上下文窗口大小不对** — 用 1M token beta 时,脚本会跟随 Claude Code 的 `exceeds_200k_tokens` 标志自动切换。

## License

[MIT](LICENSE)

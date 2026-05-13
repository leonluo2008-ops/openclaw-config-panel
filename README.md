# openclaw-config-panel

OpenClaw 可视化配置面板 — 管理多 Bot 账号和 Agent 路由。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.x-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 功能

- 🤖 **Bot 账号管理** — 增删改查飞书 Bot，支持启用/禁用
- 🔗 **Agent 绑定路由** — 可视化配置 `agentId → accountId` 路由
- 🔄 **一键重启** — 修改配置后自动重启 Gateway 服务
- 💾 **配置备份** — 每次修改前自动备份到 `~/.openclaw/backups/config-panel/`
- 👁️ **配置概览** — 查看模型配置和 Agent 工作区列表

---

## 安装

### 方式一：一键安装

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/leonluo2008-ops/openclaw-config-panel/main/setup.sh)"
```

### 方式二：手动安装

```bash
# 1. 克隆仓库
git clone https://github.com/leonluo2008-ops/openclaw-config-panel.git ~/openclaw-config-panel
cd ~/openclaw-config-panel

# 2. 安装依赖
pip3 install flask jq

# 3. 启动服务
python3 app/server.py --port 18790
```

---

## 使用

```bash
# 启动服务（局域网可访问）
python3 app/server.py --port 18790

# 带 Basic Auth 认证（推荐）
python3 app/server.py --port 18790 --auth admin:123456
```

然后在局域网内打开 `http://<电脑IP>:18790`，例如 `http://192.168.1.100:18790`。

---

## 端口和反向代理

默认端口：`18790`

推荐通过 1Panel 或 Nginx 反向代理到域名，例如：

```
config.yourdomain.com -> 127.0.0.1:18790
```

---

## 配置说明

### Bot 账号配置

```json
{
  "channels": {
    "feishu": {
      "accounts": {
        "my-bot": {
          "appId": "cli_xxxxxxxxxxxxxx",
          "appSecret": "your-secret",
          "dmPolicy": "open",
          "groupPolicy": "closed",
          "enabled": true,
          "webhookPath": "/feishu/events"
        }
      },
      "bindings": [
        {
          "type": "route",
          "agentId": "my-agent",
          "match": {
            "channel": "feishu",
            "accountId": "my-bot"
          }
        }
      ]
    }
  }
}
```

### dmPolicy 选项

| 值 | 说明 |
|----|------|
| `open` | 任何人可以私聊 |
| `pairing` | 需要配对码（防骚扰） |

### groupPolicy 选项

| 值 | 说明 |
|----|------|
| `open` | 群内任何人都可以用 |
| `closed` | 需要在 `groupSenderAllowFrom` 中明确允许 |

---

## 命令行工具（可选）

如果不需要 Web UI，也可以用命令行工具管理：

```bash
# 列出所有 Bot
bash scripts/channel-config.sh list

# 添加 Bot
bash scripts/channel-config.sh add

# 查看 Bot 详情
bash scripts/channel-config.sh show my-bot

# 删除 Bot
bash scripts/channel-config.sh remove my-bot
```

---

## 安全性

- 默认只监听 `127.0.0.1:18790`，不暴露到公网
- 生产环境请务必通过反向代理 + HTTPS 访问
- 建议配置 Basic Auth 或 IP 白名单

---

## 截图

*(待添加)*

---

## License

MIT

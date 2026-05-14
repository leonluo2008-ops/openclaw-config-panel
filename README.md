# OpenClaw Config Panel

OpenClaw 可视化配置面板 — 管理多 Bot 账号、Agent 路由和模型配置。

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-2.x-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

---

## 功能

### 🤖 Bot 账号管理
- 增删改查飞书 Bot 账号
- 支持启用/禁用
- 配置 dmPolicy / groupPolicy / webhookPath

### 🔗 Agent 绑定路由
- 可视化配置 `agentId → accountId` 路由
- 一个 Agent 绑定到指定 Bot

### 🤖 模型配置管理
- **服务商 (Provider) 管理**：添加/编辑/删除模型服务商（如 minimax、zai、openai）
- **模型管理**：在每个 Provider 下添加/编辑/删除模型
  - 支持字段：`id`、`name`、`reasoning`、`input`、`contextWindow`、`maxTokens`、`cost`
- **默认模型选择**：设置 primary + fallbacks 备用模型

### 🔄 服务控制
- 一键重启 Gateway 服务
- 配置文件自动备份

### 👁️ 配置概览
- 查看所有模型配置
- 查看 Agent 工作区列表

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
pip3 install flask

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

### 模型配置结构

OpenClaw 模型配置分为三层：

#### 1. models.providers（服务商配置）
```json
{
  "models": {
    "mode": "merge",
    "providers": {
      "minimax": {
        "baseUrl": "https://api.minimaxi.com/anthropic",
        "api": "anthropic-messages",
        "apiKey": "${MINIMAX_API_KEY}",
        "models": [
          {
            "id": "MiniMax-M2.7",
            "name": "MiniMax M2.7",
            "reasoning": true,
            "input": ["text"],
            "contextWindow": 200000,
            "maxTokens": 8192,
            "cost": { "input": 0.3, "output": 1.2, "cacheRead": 0.06, "cacheWrite": 0.375 }
          }
        ]
      }
    }
  }
}
```

#### 2. agents.defaults.models（模型别名/白名单）
```json
{
  "agents": {
    "defaults": {
      "models": {
        "minimax/MiniMax-M2.7": { "alias": "minimax-m2.7" }
      }
    }
  }
}
```

#### 3. agents.defaults.model（默认模型选择）
```json
{
  "agents": {
    "defaults": {
      "model": {
        "primary": "minimax/MiniMax-M2.7",
        "fallbacks": ["zai/glm-5", "minimax-portal/MiniMax-M2.7"]
      }
    }
  }
}
```

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

## API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/bots` | 列出所有 Bot |
| POST | `/api/bots` | 添加 Bot |
| PUT | `/api/bots/<name>` | 更新 Bot |
| DELETE | `/api/bots/<name>` | 删除 Bot |
| POST | `/api/bots/<name>/enable` | 启用 Bot |
| POST | `/api/bots/<name>/disable` | 禁用 Bot |
| GET | `/api/bindings` | 列出所有绑定 |
| POST | `/api/bindings` | 添加绑定 |
| DELETE | `/api/bindings/<agentId>` | 移除绑定 |
| GET | `/api/models/providers` | 列出所有服务商 |
| POST | `/api/models/providers` | 添加服务商 |
| PUT | `/api/models/providers/<name>` | 更新服务商 |
| DELETE | `/api/models/providers/<name>` | 删除服务商 |
| POST | `/api/models/providers/<name>/models` | 添加模型 |
| PUT | `/api/models/providers/<name>/models/<id>` | 更新模型 |
| DELETE | `/api/models/providers/<name>/models/<id>` | 删除模型 |
| GET | `/api/models/agent` | 获取模型别名配置 |
| POST | `/api/models/agent` | 设置模型别名 |
| DELETE | `/api/models/agent/<ref>` | 移除模型别名 |
| GET | `/api/models/default` | 获取默认模型配置 |
| POST | `/api/models/default` | 设置默认模型 |
| DELETE | `/api/models/default` | 清除默认模型 |
| POST | `/api/service/restart` | 重启服务 |
| POST | `/api/backup` | 备份配置 |

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

## License

MIT

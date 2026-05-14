# 更新日志 (Changelog)

所有重要的项目开发进度、已完成功能和待办任务都会记录在这里。

---

## [开发中] v0.2.0 - 模型配置管理

**分支**: `feature/model-management`

### 已完成 ✅

#### 1. 模型配置可视化界面
- **Models Tab** — 新增独立的模型配置标签页
  - 左侧服务商列表 + 右侧详情面板
  - 默认模型选择区（primary + fallbacks）
  
#### 2. 服务商 (Provider) 管理
- 支持添加/编辑/删除服务商
- 支持字段：
  - `baseUrl` — API 基础地址
  - `apiKey` — API 密钥（脱敏显示）
  - `api` — API 类型（anthropic-messages / openai-completions / openai-responses）
  - `authHeader` — 是否使用 Authorization header

#### 3. 模型管理
- 在每个 Provider 下添加/编辑/删除模型
- 支持字段：
  - `id` — 模型 ID（如 MiniMax-M2.7）
  - `name` — 显示名称
  - `reasoning` — 是否支持推理
  - `input` — 输入类型（文本/图文）
  - `contextWindow` — 上下文窗口大小
  - `maxTokens` — 最大输出 token
  - `cost` — 成本配置（input/output/cacheRead/cacheWrite）

#### 4. 默认模型选择
- 下拉选择 primary 主模型
- 多选勾选 fallback 备用模型
- 保存到 `agents.defaults.model`

#### 5. API 路由完善
| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST/PUT/DELETE | `/api/models/providers` | 服务商 CRUD |
| POST/PUT/DELETE | `/api/models/providers/<name>/models` | 模型 CRUD |
| GET/POST/DELETE | `/api/models/agent` | 模型别名配置 |
| GET/POST/DELETE | `/api/models/default` | 默认模型配置 |

#### 6. 文档更新
- README.md 新增模型配置说明
- 新增 API 路由文档

### 待办 🔄

#### 高优先级
- [ ] **Provider 内的 apiKey 不支持更新为空** — 目前编辑时留空不会清除旧的 apiKey
- [ ] 模型输入类型选择 UI 优化 — 改为复选框而非 JSON 字符串输入

#### 中优先级
- [ ] 支持从 Provider 自动拉取模型列表（调用 API 获取可用模型）
- [ ] 模型 cost 字段的可视化编辑（目前折叠在 details 里）
- [ ] 添加"测试连接"按钮 — 验证 apiKey 是否有效

#### 低优先级
- [ ] 导入/导出配置功能
- [ ] 配置变更历史记录
- [ ] 深色/浅色主题切换

---

## v0.1.0 - 基础功能

**完成日期**: 2026-05-13

### 已完成 ✅

#### Bot 账号管理
- 列出所有 Bot 账号（卡片视图）
- 添加/编辑/删除 Bot
- 启用/禁用 Bot
- 显示 appId、脱敏 appSecret

#### Agent 绑定路由
- 列出所有绑定（表格视图）
- 添加新的 agent → accountId 绑定
- 移除绑定

#### 服务控制
- 服务状态检测（运行中/已停止）
- 一键重启 openclaw-gateway
- 配置文件备份（每次修改前自动备份）

#### 基础架构
- Flask Web 服务
- Basic Auth 认证
- 响应式深色主题 UI
- 自动备份机制

---

## 技术细节

### 项目结构
```
openclaw-config-panel/
├── app/
│   ├── server.py          # Flask API 路由
│   └── config_manager.py  # OpenClaw 配置读写
├── templates/
│   └── index.html         # 前端页面
├── static/
│   └── style.css          # 深色主题样式
├── scripts/
│   └── channel-config.sh  # 命令行工具（可选）
├── README.md
├── CHANGELOG.md
└── setup.sh               # 一键安装脚本
```

### 配置文件位置
- OpenClaw 配置: `~/.openclaw/openclaw.json`
- 备份目录: `~/.openclaw/backups/config-panel/`

### 端口
- 默认: `18790`
- 认证: `admin:123456`（可通过 --auth 修改）

---

## 贡献指南

1. 开发新功能从 `main` 分支创建新分支
2. 完成后提交 PR 到 `main`
3. 更新本日志记录进度

---

*最后更新: 2026-05-14*

#!/usr/bin/env python3
# config_manager.py - OpenClaw 配置读写模块
import json
import os
import subprocess
import shutil
from pathlib import Path

OPENCLAW_JSON = os.path.expanduser("~/.openclaw/openclaw.json")
BACKUP_DIR = os.path.expanduser("~/.openclaw/backups/config-panel")


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def backup_current():
    """备份当前 openclaw.json"""
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    import time
    backup_path = os.path.join(BACKUP_DIR, f"openclaw.json.backup-{int(time.time())}")
    shutil.copy2(OPENCLAW_JSON, backup_path)
    return backup_path


def get_openclaw_config():
    """读取当前 openclaw.json"""
    return load_json(OPENCLAW_JSON)


def save_openclaw_config(data):
    """保存 openclaw.json"""
    save_json(OPENCLAW_JSON, data)


def restart_service():
    """重启 openclaw-gateway 服务"""
    result = subprocess.run(
        ["systemctl", "--user", "restart", "openclaw-gateway"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def get_channel_config():
    """获取飞书 channel 配置"""
    config = get_openclaw_config()
    return config.get("channels", {}).get("feishu", {})


def list_bots():
    """列出所有 bot 账号"""
    channel = get_channel_config()
    accounts = channel.get("accounts", {})
    result = []
    for name, conf in accounts.items():
        result.append({
            "name": name,
            "appId": conf.get("appId", ""),
            "appSecret_masked": mask_secret(conf.get("appSecret", "")),
            "dmPolicy": conf.get("dmPolicy", "open"),
            "groupPolicy": conf.get("groupPolicy", "closed"),
            "enabled": conf.get("enabled", True),
            "webhookPath": conf.get("webhookPath", "/feishu/events"),
            "groupSenderAllowFrom": conf.get("groupSenderAllowFrom", []),
            "groups": conf.get("groups", {}),
        })
    return result


def get_bot(name, mask=True):
    """获取单个 bot 详情"""
    channel = get_channel_config()
    accounts = channel.get("accounts", {})
    if name not in accounts:
        return None
    conf = accounts[name]
    result = {
        "name": name,
        "appId": conf.get("appId", ""),
        "dmPolicy": conf.get("dmPolicy", "open"),
        "groupPolicy": conf.get("groupPolicy", "closed"),
        "enabled": conf.get("enabled", True),
        "webhookPath": conf.get("webhookPath", "/feishu/events"),
        "groupSenderAllowFrom": conf.get("groupSenderAllowFrom", []),
        "groups": conf.get("groups", {}),
    }
    if mask:
        result["appSecret_masked"] = mask_secret(conf.get("appSecret", ""))
    else:
        result["appSecret"] = conf.get("appSecret", "")
    return result


def add_bot(name, appId, appSecret, dmPolicy="open", groupPolicy="closed",
            webhookPath="/feishu/events", enabled=True):
    """添加新 bot"""
    config = get_openclaw_config()
    if "channels" not in config:
        config["channels"] = {}
    if "feishu" not in config["channels"]:
        config["channels"]["feishu"] = {}
    if "accounts" not in config["channels"]["feishu"]:
        config["channels"]["feishu"]["accounts"] = {}
    
    config["channels"]["feishu"]["accounts"][name] = {
        "appId": appId,
        "appSecret": appSecret,
        "dmPolicy": dmPolicy,
        "groupPolicy": groupPolicy,
        "enabled": enabled,
        "webhookPath": webhookPath,
    }
    
    save_openclaw_config(config)
    return True


def update_bot(name, **kwargs):
    """更新 bot 配置"""
    config = get_openclaw_config()
    accounts = config.get("channels", {}).get("feishu", {}).get("accounts", {})
    if name not in accounts:
        return False
    
    for key, value in kwargs.items():
        if value is not None:
            accounts[name][key] = value
    
    save_openclaw_config(config)
    return True


def delete_bot(name):
    """删除 bot"""
    config = get_openclaw_config()
    accounts = config.get("channels", {}).get("feishu", {}).get("accounts", {})
    if name not in accounts:
        return False
    
    del accounts[name]
    save_openclaw_config(config)
    return True


def get_bindings():
    """获取 agent 绑定路由"""
    config = get_openclaw_config()
    return config.get("channels", {}).get("feishu", {}).get("bindings", [])


def set_binding(agentId, accountId):
    """设置或更新 agent → accountId 绑定"""
    config = get_openclaw_config()
    bindings = config.setdefault("channels", {}).setdefault("feishu", {}).setdefault("bindings", [])
    
    # 查找是否已存在该 agent 的绑定
    found = False
    for b in bindings:
        if b.get("agentId") == agentId:
            b["match"] = {"channel": "feishu", "accountId": accountId}
            found = True
            break
    
    if not found:
        bindings.append({
            "type": "route",
            "agentId": agentId,
            "match": {"channel": "feishu", "accountId": accountId}
        })
    
    save_openclaw_config(config)
    return True


def remove_binding(agentId):
    """移除 agent 绑定"""
    config = get_openclaw_config()
    bindings = config.get("channels", {}).get("feishu", {}).get("bindings", [])
    bindings[:] = [b for b in bindings if b.get("agentId") != agentId]
    save_openclaw_config(config)
    return True


def get_agents():
    """获取所有 agent 列表（包含默认 main agent）"""
    config = get_openclaw_config()
    agents_config = config.get("agents", {})
    defaults = agents_config.get("defaults", {})
    agents_list = agents_config.get("list", [])
    
    default_workspace = defaults.get("workspace", "")
    default_model = defaults.get("model", {})
    default_models = defaults.get("models", {})
    
    result = {
        "defaults": {
            "workspace": default_workspace,
            "model": default_model,
            "models": default_models,
        },
        "list": []
    }
    
    # 默认 main agent（从 defaults 推导）
    list_ids = [a.get("id", a.get("name", "")) for a in agents_list]
    if "main" not in list_ids:
        result["list"].append({
            "id": "main",
            "name": "main (默认)",
            "workspace": default_workspace,
            "model": default_model.get("primary", ""),
            "isDefault": True,
        })
    
    for a in agents_list:
        result["list"].append({
            "id": a.get("id", a.get("name", "")),
            "name": a.get("name", a.get("id", "")),
            "workspace": a.get("workspace", ""),
            "model": a.get("model", {}).get("primary", "") if isinstance(a.get("model"), dict) else "",
            "isDefault": False,
        })
    
    return result


def create_agent(agent_id, name=None, workspace=None, model=None):
    """创建新 agent（写入 agents.list）"""
    config = get_openclaw_config()
    if "agents" not in config:
        config["agents"] = {}
    if "list" not in config["agents"]:
        config["agents"]["list"] = []
    
    # 检查 ID 是否已存在
    for a in config["agents"]["list"]:
        if a.get("id", a.get("name", "")) == agent_id:
            raise ValueError(f"Agent '{agent_id}' 已存在")
    if agent_id == "main":
        raise ValueError("'main' 是默认 Agent，不可创建同名 Agent")
    
    # 自动生成工作区路径：~/.openclaw/agents/<agent-id>/
    if not workspace:
        workspace = os.path.expanduser(f"~/.openclaw/agents/{agent_id}")
    
    agent_entry = {"id": agent_id}
    if name:
        agent_entry["name"] = name
    agent_entry["workspace"] = workspace
    if model:
        agent_entry["model"] = {"primary": model}
    
    config["agents"]["list"].append(agent_entry)
    save_openclaw_config(config)
    
    # 自动创建工作区目录并初始化核心文件
    os.makedirs(workspace, exist_ok=True)
    os.makedirs(os.path.join(workspace, "memory"), exist_ok=True)
    
    for filename in CORE_FILES:
        filepath = os.path.join(workspace, filename)
        if not os.path.exists(filepath):
            template = generate_template(filename, agent_id, name, model)
            if template:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(template)
    
    return True


def update_agent(agent_id, **kwargs):
    """更新 agent 配置"""
    if agent_id == "main":
        raise ValueError("默认 Agent (main) 的配置请通过 OpenClaw 原生方式修改")
    config = get_openclaw_config()
    agents_list = config.get("agents", {}).get("list", [])
    found = False
    for a in agents_list:
        if a.get("id", a.get("name", "")) == agent_id:
            for key, value in kwargs.items():
                if value is not None:
                    a[key] = value
            found = True
            break
    if not found:
        raise ValueError(f"Agent '{agent_id}' 不存在")
    save_openclaw_config(config)
    return True


def delete_agent(agent_id):
    """删除 agent"""
    if agent_id == "main":
        raise ValueError("默认 Agent (main) 不可删除")
    config = get_openclaw_config()
    agents_list = config.get("agents", {}).get("list", [])
    original_len = len(agents_list)
    config["agents"]["list"] = [a for a in agents_list if a.get("id", a.get("name", "")) != agent_id]
    if len(config["agents"]["list"]) == original_len:
        raise ValueError(f"Agent '{agent_id}' 不存在")
    save_openclaw_config(config)
    return True


CORE_FILES = {
    "AGENTS.md": {"required": True, "desc": "工作规范和行为规则"},
    "SOUL.md": {"required": False, "desc": "性格、语气、风格"},
    "IDENTITY.md": {"required": False, "desc": "身份信息（名字、emoji、头像）"},
    "USER.md": {"required": False, "desc": "关于使用者的信息"},
    "TOOLS.md": {"required": False, "desc": "工具使用笔记和环境配置"},
    "HEARTBEAT.md": {"required": False, "desc": "心跳检查清单"},
    "BOOTSTRAP.md": {"required": False, "desc": "初始化引导（首次运行后自动删除）"},
}


def generate_template(filename, agent_id, agent_name=None, model=None):
    """生成核心文件的模板内容"""
    display_name = agent_name or agent_id

    templates = {
        "AGENTS.md": f"""# AGENTS.md - {display_name} 的工作区

这是 {display_name} 的工作区。

## 工作规范

- 认真完成用户交办的任务
- 不确定的事情先问再做
- 重要的操作（删除、发送消息等）先确认
- 内部操作（读文件、搜索等）可以自由执行

## 记忆

- 重要决定和事件记录到 MEMORY.md
- 日常日志写到 memory/YYYY-MM-DD.md

## 红线

- 不泄露用户隐私
- 不执行未确认的危险操作
- trash > rm（可恢复优于不可恢复）
""",

        "SOUL.md": f"""# SOUL.md - {display_name} 的性格

## 核心特质

- 有用、直接、不废话
- 可以有自己的观点和偏好
- 先自己尝试解决，解决不了再问

## 风格

- 简洁明了，不啰嗦
- 该详细时详细，该简短时简短
- 不要过度客套，不要说废话

## 边界

- 隐私信息不外泄
- 外部操作（发邮件、发消息等）先确认
- 不确定就问
""",

        "IDENTITY.md": f"""# IDENTITY.md - {display_name}

- **Name:** {display_name}
- **ID:** {agent_id}
- **Creature:** AI 助手
- **Vibe:** 实用、直接、有个性
- **Emoji:** 🤖

---

创建时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d')}
""",

        "USER.md": """# USER.md - 关于使用者

- **Name:** （待填写）
- **Timezone:** （待填写）

## 备注

（在这里记录关于使用者的信息）
""",

        "TOOLS.md": """# TOOLS.md - 工具笔记

## 环境配置

（在这里记录环境相关的配置，如 SSH、摄像头、语音等）
""",

        "HEARTBEAT.md": """# Heartbeat

（在这里添加定期检查项）
""",

        "BOOTSTRAP.md": f"""# BOOTSTRAP.md

你是 **{display_name}**（ID: {agent_id}），一个 OpenClaw AI 助手。

## 初始化步骤

1. 阅读你的核心文件：SOUL.md、IDENTITY.md、AGENTS.md
2. 了解你的使用者：阅读 USER.md
3. 初始化完成后，删除这个文件

欢迎来到这个世界！ 🎉
""",
    }

    return templates.get(filename, "")


def get_agent_workspace(agent_id):
    """获取 agent 的工作区路径"""
    config = get_openclaw_config()
    defaults = config.get("agents", {}).get("defaults", {})

    if agent_id == "main":
        return defaults.get("workspace", os.path.expanduser("~/.openclaw/workspace"))

    agents_list = config.get("agents", {}).get("list", [])
    for a in agents_list:
        if a.get("id", a.get("name", "")) == agent_id:
            return a.get("workspace", defaults.get("workspace", ""))

    return None


def list_core_files(agent_id):
    """列出 agent 工作区中的核心文件及其内容"""
    workspace = get_agent_workspace(agent_id)
    if not workspace:
        return None

    result = []
    for filename, meta in CORE_FILES.items():
        filepath = os.path.join(workspace, filename)
        exists = os.path.isfile(filepath)
        content = ""
        if exists:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                content = ""
        result.append({
            "filename": filename,
            "desc": meta["desc"],
            "required": meta["required"],
            "exists": exists,
            "content": content,
        })
    return result


def get_core_file(agent_id, filename):
    """读取单个核心文件"""
    if filename not in CORE_FILES:
        return None
    workspace = get_agent_workspace(agent_id)
    if not workspace:
        return None
    filepath = os.path.join(workspace, filename)
    if not os.path.isfile(filepath):
        return ""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def save_core_file(agent_id, filename, content):
    """保存单个核心文件"""
    if filename not in CORE_FILES:
        raise ValueError(f"不支持的核心文件: {filename}")
    workspace = get_agent_workspace(agent_id)
    if not workspace:
        raise ValueError(f"Agent '{agent_id}' 的工作区不存在")
    os.makedirs(workspace, exist_ok=True)
    filepath = os.path.join(workspace, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


def get_models():
    """获取模型配置"""
    config = get_openclaw_config()
    return config.get("models", {})


def mask_secret(secret):
    """脱敏显示"""
    if not secret or len(secret) < 8:
        return secret
    return f"{secret[:4]}...{secret[-4:]}"


def service_status():
    """获取服务状态"""
    result = subprocess.run(
        ["systemctl", "--user", "is-active", "openclaw-gateway"],
        capture_output=True, text=True
    )
    return result.stdout.strip() == "active"

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


OPENCLAW_EXTENSIONS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..",
    ".npm-global", "lib", "node_modules", "openclaw", "dist", "extensions"
)


def _resolve_extensions_dir():
    """解析 OpenClaw 扩展目录路径"""
    # 尝试从 which openclaw 推导
    try:
        result = subprocess.run(["which", "openclaw"], capture_output=True, text=True)
        if result.returncode == 0:
            openclaw_bin = result.stdout.strip()
            # /home/luo/.npm-global/bin/openclaw -> /home/luo/.npm-global/lib/node_modules/openclaw/dist/extensions
            ext_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(openclaw_bin))),
                "lib", "node_modules", "openclaw", "dist", "extensions"
            )
            if os.path.isdir(ext_dir):
                return ext_dir
    except:
        pass
    # fallback
    if os.path.isdir(OPENCLAW_EXTENSIONS_DIR):
        return OPENCLAW_EXTENSIONS_DIR
    return None


def get_available_providers():
    """获取 OpenClaw 原生所有可用的 LLM provider"""
    ext_dir = _resolve_extensions_dir()
    if not ext_dir:
        return []

    # 已知 LLM provider ID 列表
    llm_ids = {
        "openai", "anthropic", "google", "deepseek", "zai", "minimax", "mistral",
        "groq", "together", "fireworks", "openrouter", "ollama", "lmstudio",
        "qwen", "moonshot", "nvidia", "cerebras", "deepinfra", "chutes",
        "xai", "volcengine", "byteplus", "stepfun", "arcee", "venice",
        "vllm", "sglang", "litellm", "huggingface", "github-copilot",
        "microsoft-foundry", "copilot-proxy", "kimi-coding", "tencent",
        "xiaomi", "qianfan", "anthropic-vertex", "amazon-bedrock", "gradium",
        "vydra", "alibaba",
    }

    # 读取当前已配置的 provider
    config = get_openclaw_config()
    configured = set(config.get("models", {}).get("providers", {}).keys())

    results = []
    for d in sorted(os.listdir(ext_dir)):
        pfile = os.path.join(ext_dir, d, "openclaw.plugin.json")
        if not os.path.isfile(pfile):
            continue
        try:
            data = json.load(open(pfile))
            providers = data.get("providers", [])
            if not isinstance(providers, list) or not providers:
                continue
            if not isinstance(providers[0], str):
                continue
            # 只显示 LLM provider
            if not any(pid in llm_ids for pid in providers):
                continue

            # 读取 host 信息
            endpoints = data.get("providerEndpoints", [])
            default_host = ""
            for ep in endpoints:
                hosts = ep.get("hosts", [])
                if hosts:
                    default_host = hosts[0]
                    break

            is_configured = any(pid in configured for pid in providers)

            results.append({
                "id": d,
                "providerIds": providers,
                "defaultHost": default_host,
                "isConfigured": is_configured,
            })
        except:
            pass

    return results


def get_provider_schema():
    """获取 provider 配置的 schema 信息（关键字段）"""
    return {
        "baseUrl": {"type": "string", "required": True, "desc": "Provider API 地址"},
        "apiKey": {"type": "string", "required": False, "desc": "API Key（可选，部分 provider 通过环境变量认证）"},
        "api": {"type": "select", "required": True, "desc": "API 类型", "options": [
            "openai-completions", "anthropic-messages", "google-gemini",
        ]},
    }


def add_provider(provider_id, base_url, api_key="", api="openai-completions", models=None):
    """添加 provider 配置"""
    config = get_openclaw_config()
    if "models" not in config:
        config["models"] = {}
    if "providers" not in config["models"]:
        config["models"]["providers"] = {}

    entry = {
        "baseUrl": base_url,
        "api": api,
    }
    if api_key:
        entry["apiKey"] = api_key
    if models:
        entry["models"] = models

    config["models"]["providers"][provider_id] = entry
    save_openclaw_config(config)
    return True


def update_provider(provider_id, **kwargs):
    """更新 provider 配置"""
    config = get_openclaw_config()
    providers = config.get("models", {}).get("providers", {})
    if provider_id not in providers:
        raise ValueError(f"Provider '{provider_id}' 未配置")
    for key, value in kwargs.items():
        if value is not None:
            providers[provider_id][key] = value
    save_openclaw_config(config)
    return True


def remove_provider(provider_id):
    """删除 provider 配置"""
    config = get_openclaw_config()
    providers = config.get("models", {}).get("providers", {})
    if provider_id not in providers:
        raise ValueError(f"Provider '{provider_id}' 未配置")
    # 检查是否有关联模型在使用
    defaults = config.get("agents", {}).get("defaults", {})
    default_model = defaults.get("model", {}).get("primary", "")
    if default_model.startswith(f"{provider_id}/"):
        raise ValueError(f"默认模型 '{default_model}' 正在使用此 provider，请先切换")
    del providers[provider_id]
    save_openclaw_config(config)
    return True


def get_all_skills():
    """扫描所有 skill 源并返回统一列表"""
    config = get_openclaw_config()
    skills_config = config.get("skills", {})
    entries = skills_config.get("entries", {})
    allow_bundled = skills_config.get("allowBundled", None)  # None = 全部允许
    default_skills = config.get("agents", {}).get("defaults", {}).get("skills", None)
    
    # 读取每个 agent 的 skills
    agent_skills = {}
    for a in config.get("agents", {}).get("list", []):
        aid = a.get("id", a.get("name", ""))
        s = a.get("skills", None)
        if s is not None:
            agent_skills[aid] = s
    
    all_skills = {}
    
    # 1. Bundled skills
    bundled_dir = os.path.join(
        os.path.dirname(subprocess.run(["which", "openclaw"], capture_output=True, text=True).stdout.strip()),
        "..", "lib", "node_modules", "openclaw", "skills"
    ) if os.path.exists("/usr/local/bin/openclaw") else "/home/luo/.npm-global/lib/node_modules/openclaw/skills"
    if os.path.isdir(bundled_dir):
        for d in sorted(os.listdir(bundled_dir)):
            sm = os.path.join(bundled_dir, d, "SKILL.md")
            if os.path.isfile(sm):
                name, desc = _parse_skill_meta(sm)
                all_skills[d] = {
                    "id": d,
                    "name": name or d,
                    "description": desc or "",
                    "source": "bundled",
                }
    
    # 2. Extension skills
    ext_base = "/home/luo/.npm-global/lib/node_modules/openclaw/dist/extensions"
    # 尝试动态解析
    try:
        r = subprocess.run(["which", "openclaw"], capture_output=True, text=True)
        if r.returncode == 0:
            ext_base = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(r.stdout.strip()))),
                "lib", "node_modules", "openclaw", "dist", "extensions"
            )
    except:
        pass
    if os.path.isdir(ext_base):
        for edir in sorted(os.listdir(ext_base)):
            skills_dir = os.path.join(ext_base, edir, "skills")
            if not os.path.isdir(skills_dir):
                continue
            for sd in sorted(os.listdir(skills_dir)):
                sm = os.path.join(skills_dir, sd, "SKILL.md")
                if os.path.isfile(sm) and sd not in all_skills:
                    name, desc = _parse_skill_meta(sm)
                    all_skills[sd] = {
                        "id": sd,
                        "name": name or sd,
                        "description": desc or "",
                        "source": "extension",
                    }
    
    # 3. User skills
    user_dir = os.path.expanduser("~/.openclaw/plugin-skills")
    if os.path.isdir(user_dir):
        for d in sorted(os.listdir(user_dir)):
            sm = os.path.join(user_dir, d, "SKILL.md")
            if os.path.isfile(sm) and d not in all_skills:
                name, desc = _parse_skill_meta(sm)
                all_skills[d] = {
                    "id": d,
                    "name": name or d,
                    "description": desc or "",
                    "source": "user",
                }
    
    # 附加状态信息
    result = []
    for sid, s in sorted(all_skills.items()):
        entry = entries.get(sid, {})
        # 状态逻辑：
        # entries 中 enabled:true → 明确启用（绿色）
        # entries 中 enabled:false → 明确禁用（红色）
        # entries 中无记录 + allowBundled 未设 → 默认可用（灰色/黄色）
        # entries 中无记录 + allowBundled 有值且包含 → 允许（黄色）
        # entries 中无记录 + allowBundled 有值且不包含 → 不允许（红色）
        has_entry = sid in entries
        if has_entry:
            s["enabled"] = entry.get("enabled", True) is not False
            s["state"] = "enabled" if s["enabled"] else "disabled"
        else:
            if allow_bundled is not None:
                if sid in allow_bundled:
                    s["enabled"] = True
                    s["state"] = "allowed"  # 在 allowlist 中但未显式启用
                else:
                    s["enabled"] = False
                    s["state"] = "disabled"
            else:
                s["enabled"] = True
                s["state"] = "available"  # 默认可用，但不是用户主动开启
        s["inDefault"] = default_skills is None or sid in default_skills
        s["agentAssignments"] = {}
        for aid, skills in agent_skills.items():
            s["agentAssignments"][aid] = sid in skills
        result.append(s)
    
    return {
        "skills": result,
        "defaultSkills": default_skills or [],
        "defaultSkillsUnset": default_skills is None,
        "agentSkillsOverrides": agent_skills,
    }


def _parse_skill_meta(path):
    """从 SKILL.md 提取 name 和 description"""
    try:
        with open(path, 'r') as f:
            content = f.read(2000)
        if content.startswith('---'):
            end = content.find('---', 3)
            if end > 0:
                fm = content[3:end].strip()
                name = ""
                desc = ""
                in_desc = False
                desc_lines = []
                for line in fm.split('\n'):
                    if in_desc:
                        if line and not line[0].isalpha() and line[0] != ' ':
                            in_desc = False
                        else:
                            desc_lines.append(line.strip())
                            continue
                    if line.startswith('name:'):
                        name = line.split(':',1)[1].strip().strip('"').strip("'")
                    elif line.startswith('description:'):
                        desc = line.split(':',1)[1].strip().strip('"').strip("'")
                        if desc.startswith('|'):
                            in_desc = True
                            continue
                        if not desc:
                            in_desc = True
                if desc_lines and not desc:
                    desc = ' '.join(desc_lines).strip()
                return name, desc
    except:
        pass
    return "", ""


def set_skill_enabled(skill_id, enabled):
    """启用/禁用 skill。
    enabled=True → 写入 entries.{skill_id}.enabled: true（明确启用）
    enabled=False → 写入 entries.{skill_id}.enabled: false（明确禁用）
    如果 entries 里只有 enabled 字段且为 true，等同于恢复默认，直接删除条目
    """
    config = get_openclaw_config()
    skills_sec = config.setdefault("skills", {})
    entries = skills_sec.setdefault("entries", {})
    if enabled:
        # 明确启用：写入 enabled:true
        if skill_id in entries:
            entries[skill_id]["enabled"] = True
        else:
            entries[skill_id] = {"enabled": True}
    else:
        # 明确禁用：写入 enabled:false
        if skill_id in entries:
            entries[skill_id]["enabled"] = False
        else:
            entries[skill_id] = {"enabled": False}
    save_openclaw_config(config)
    return True


def set_default_skills(skill_ids):
    """设置默认 skills allowlist"""
    config = get_openclaw_config()
    defaults = config.setdefault("agents", {}).setdefault("defaults", {})
    if skill_ids is None or len(skill_ids) == 0:
        # 移除限制，全部可用
        if "skills" in defaults:
            del defaults["skills"]
    else:
        defaults["skills"] = skill_ids
    save_openclaw_config(config)
    return True


def set_agent_skills(agent_id, skill_ids):
    """设置 agent 的 skills 覆盖"""
    if agent_id == "main":
        return set_default_skills(skill_ids)
    config = get_openclaw_config()
    agents_list = config.get("agents", {}).get("list", [])
    found = False
    for a in agents_list:
        if a.get("id", a.get("name", "")) == agent_id:
            if skill_ids is None or len(skill_ids) == 0:
                a.pop("skills", None)
            else:
                a["skills"] = skill_ids
            found = True
            break
    if not found:
        raise ValueError(f"Agent '{agent_id}' 不存在")
    save_openclaw_config(config)
    return True


def get_models():
    """获取完整模型配置（用于配置概览展示）"""
    config = get_openclaw_config()
    return config.get("models", {})


def get_model_config():
    """获取模型配置的完整视图（providers + allowlist + default）"""
    config = get_openclaw_config()
    models_root = config.get("models", {})
    defaults = config.get("agents", {}).get("defaults", {})

    # 构建提供商列表
    providers = []
    for pid, pconf in models_root.get("providers", {}).items():
        provider_models = []
        for m in pconf.get("models", []):
            full_id = f"{pid}/{m.get('id', '')}"
            provider_models.append({
                "id": m.get("id", ""),
                "fullId": full_id,
                "name": m.get("name", m.get("id", "")),
                "reasoning": m.get("reasoning", False),
                "input": m.get("input", ["text"]),
                "cost": m.get("cost", {}),
                "contextWindow": m.get("contextWindow"),
                "maxTokens": m.get("maxTokens"),
            })
        providers.append({
            "id": pid,
            "baseUrl": pconf.get("baseUrl", ""),
            "api": pconf.get("api", ""),
            "models": provider_models,
        })

    # 构建 allowlist
    allowlist = []
    for model_id, mconf in defaults.get("models", {}).items():
        # 从 providers 找模型名称
        model_name = ""
        for p in providers:
            for m in p["models"]:
                if m["fullId"] == model_id:
                    model_name = m["name"]
                    break
        allowlist.append({
            "id": model_id,
            "name": model_name,
            "alias": mconf.get("alias", ""),
        })

    # 默认模型
    default_model = defaults.get("model", {}).get("primary", "")

    # 每个 agent 的模型
    agent_models = []
    agents_list = config.get("agents", {}).get("list", [])
    for a in agents_list:
        aid = a.get("id", a.get("name", ""))
        am = a.get("model", {}).get("primary", "") if isinstance(a.get("model"), dict) else ""
        if am:
            agent_models.append({"agentId": aid, "model": am})

    return {
        "defaultModel": default_model,
        "allowlist": allowlist,
        "providers": providers,
        "agentModels": agent_models,
        "mode": models_root.get("mode", "merge"),
    }


def set_default_model(model_id):
    """设置默认模型"""
    config = get_openclaw_config()
    if "agents" not in config:
        config["agents"] = {}
    if "defaults" not in config["agents"]:
        config["agents"]["defaults"] = {}
    if "model" not in config["agents"]["defaults"]:
        config["agents"]["defaults"]["model"] = {}
    config["agents"]["defaults"]["model"]["primary"] = model_id
    save_openclaw_config(config)
    return True


def set_model_alias(model_id, alias):
    """设置模型别名"""
    config = get_openclaw_config()
    models_map = config.setdefault("agents", {}).setdefault("defaults", {}).setdefault("models", {})
    if model_id not in models_map:
        models_map[model_id] = {}
    if alias:
        models_map[model_id]["alias"] = alias
    elif "alias" in models_map[model_id]:
        del models_map[model_id]["alias"]
    save_openclaw_config(config)
    return True


def add_to_allowlist(model_id, alias=""):
    """添加模型到 allowlist"""
    config = get_openclaw_config()
    models_map = config.setdefault("agents", {}).setdefault("defaults", {}).setdefault("models", {})
    entry = {}
    if alias:
        entry["alias"] = alias
    models_map[model_id] = entry
    save_openclaw_config(config)
    return True


def remove_from_allowlist(model_id):
    """从 allowlist 移除模型"""
    config = get_openclaw_config()
    models_map = config.get("agents", {}).get("defaults", {}).get("models", {})
    if model_id not in models_map:
        raise ValueError(f"模型 '{model_id}' 不在 allowlist 中")
    # 不允许移除当前默认模型
    default_model = config.get("agents", {}).get("defaults", {}).get("model", {}).get("primary", "")
    if model_id == default_model:
        raise ValueError("不能移除当前默认模型，请先切换默认模型")
    del models_map[model_id]
    save_openclaw_config(config)
    return True


def set_agent_model(agent_id, model_id):
    """设置 agent 的模型"""
    if agent_id == "main":
        return set_default_model(model_id)
    config = get_openclaw_config()
    agents_list = config.get("agents", {}).get("list", [])
    found = False
    for a in agents_list:
        if a.get("id", a.get("name", "")) == agent_id:
            a["model"] = {"primary": model_id}
            found = True
            break
    if not found:
        raise ValueError(f"Agent '{agent_id}' 不存在")
    save_openclaw_config(config)
    return True


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

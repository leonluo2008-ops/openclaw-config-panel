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


def get_bot(name):
    """获取单个 bot 详情"""
    channel = get_channel_config()
    accounts = channel.get("accounts", {})
    if name not in accounts:
        return None
    conf = accounts[name]
    return {
        "name": name,
        "appId": conf.get("appId", ""),
        "appSecret": conf.get("appSecret", ""),
        "dmPolicy": conf.get("dmPolicy", "open"),
        "groupPolicy": conf.get("groupPolicy", "closed"),
        "enabled": conf.get("enabled", True),
        "webhookPath": conf.get("webhookPath", "/feishu/events"),
        "groupSenderAllowFrom": conf.get("groupSenderAllowFrom", []),
        "groups": conf.get("groups", {}),
    }


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
    """获取所有 agent 列表"""
    config = get_openclaw_config()
    agents_config = config.get("agents", {})
    defaults = agents_config.get("defaults", {})
    agents_list = agents_config.get("list", [])
    
    result = {
        "defaults": {
            "workspace": defaults.get("workspace", ""),
            "model": defaults.get("model", {}),
        },
        "list": []
    }
    
    for a in agents_list:
        result["list"].append({
            "id": a.get("id", a.get("name", "")),
            "name": a.get("name", a.get("id", "")),
            "workspace": a.get("workspace", ""),
        })
    
    return result


# =============================================================================
# Model Provider Management (models.providers)
# =============================================================================

def get_model_providers():
    """获取所有模型 Provider 配置"""
    config = get_openclaw_config()
    providers = config.get("models", {}).get("providers", {})
    return providers


def get_model_provider(name):
    """获取单个 Provider 配置"""
    providers = get_model_providers()
    return providers.get(name)


def save_model_providers(providers):
    """保存 providers 到 models.providers"""
    config = get_openclaw_config()
    if "models" not in config:
        config["models"] = {}
    config["models"]["providers"] = providers
    save_openclaw_config(config)


def add_model_provider(name, baseUrl, apiKey="", api="anthropic-messages",
                       authHeader=False, models=None):
    """
    添加新的模型 Provider
    
    Args:
        name: Provider 名称 (如 minimax, zai, openai)
        baseUrl: API 基础地址
        apiKey: API 密钥 (可选)
        api: API 类型 - anthropic-messages / openai-completions / openai-responses
        authHeader: 是否使用 Authorization header
        models: 模型列表 (可选)
    """
    config = get_openclaw_config()
    if "models" not in config:
        config["models"] = {"mode": "merge", "providers": {}}
    if "providers" not in config["models"]:
        config["models"]["providers"] = {}
    
    provider_config = {
        "baseUrl": baseUrl,
        "api": api,
    }
    if apiKey:
        provider_config["apiKey"] = apiKey
    if authHeader:
        provider_config["authHeader"] = True
    if models:
        provider_config["models"] = models
    
    config["models"]["providers"][name] = provider_config
    save_openclaw_config(config)
    return True


def update_model_provider(name, **kwargs):
    """更新 Provider 配置"""
    config = get_openclaw_config()
    providers = config.get("models", {}).get("providers", {})
    if name not in providers:
        return False
    
    for key, value in kwargs.items():
        if value is not None:
            providers[name][key] = value
    
    save_openclaw_config(config)
    return True


def delete_model_provider(name):
    """删除 Provider 及其所有模型"""
    config = get_openclaw_config()
    providers = config.get("models", {}).get("providers", {})
    if name not in providers:
        return False
    
    del providers[name]
    save_openclaw_config(config)
    return True


# =============================================================================
# Model Management (within Provider)
# =============================================================================

def add_model_to_provider(provider_name, model_data):
    """
    向 Provider 添加模型
    
    Args:
        provider_name: Provider 名称
        model_data: 模型数据，包含:
            - id: 模型 ID (必填)
            - name: 模型显示名
            - reasoning: 是否支持推理
            - input: 输入类型 ["text"] 或 ["text", "image"]
            - cost: 成本 {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}
            - contextWindow: 上下文窗口大小
            - maxTokens: 最大输出 token
    """
    config = get_openclaw_config()
    providers = config.get("models", {}).get("providers", {})
    if provider_name not in providers:
        raise ValueError(f"Provider '{provider_name}' not found")
    
    if "models" not in providers[provider_name]:
        providers[provider_name]["models"] = []
    
    # 检查 model id 是否已存在
    for m in providers[provider_name]["models"]:
        if m.get("id") == model_data.get("id"):
            raise ValueError(f"Model '{model_data.get('id')}' already exists in provider '{provider_name}'")
    
    # 补全默认值
    model = {
        "id": model_data.get("id"),
        "name": model_data.get("name", model_data.get("id")),
        "reasoning": model_data.get("reasoning", False),
        "input": model_data.get("input", ["text"]),
        "cost": model_data.get("cost", {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}),
        "contextWindow": model_data.get("contextWindow", 200000),
        "maxTokens": model_data.get("maxTokens", 8192),
    }
    
    providers[provider_name]["models"].append(model)
    save_openclaw_config(config)
    return True


def update_model_in_provider(provider_name, model_id, **kwargs):
    """更新 Provider 中的模型"""
    config = get_openclaw_config()
    providers = config.get("models", {}).get("providers", {})
    if provider_name not in providers:
        return False
    
    models = providers[provider_name].get("models", [])
    for model in models:
        if model.get("id") == model_id:
            for key, value in kwargs.items():
                if value is not None:
                    model[key] = value
            save_openclaw_config(config)
            return True
    
    return False


def delete_model_from_provider(provider_name, model_id):
    """从 Provider 删除模型"""
    config = get_openclaw_config()
    providers = config.get("models", {}).get("providers", {})
    if provider_name not in providers:
        return False
    
    models = providers[provider_name].get("models", [])
    original_len = len(models)
    providers[provider_name]["models"] = [m for m in models if m.get("id") != model_id]
    
    if len(providers[provider_name]["models"]) < original_len:
        save_openclaw_config(config)
        return True
    
    return False


# =============================================================================
# Agent Model Config (agents.defaults.models - alias/allowlist)
# =============================================================================

def get_agent_models():
    """获取 agents.defaults.models 配置（模型别名/白名单）"""
    config = get_openclaw_config()
    return config.get("agents", {}).get("defaults", {}).get("models", {})


def set_agent_model(provider_model_ref, alias=None):
    """
    添加或更新 agents.defaults.models 条目
    
    Args:
        provider_model_ref: 模型引用，如 "minimax/MiniMax-M2.7"
        alias: 可选别名
    """
    config = get_openclaw_config()
    if "agents" not in config:
        config["agents"] = {}
    if "defaults" not in config["agents"]:
        config["agents"]["defaults"] = {}
    if "models" not in config["agents"]["defaults"]:
        config["agents"]["defaults"]["models"] = {}
    
    if alias:
        config["agents"]["defaults"]["models"][provider_model_ref] = {"alias": alias}
    else:
        config["agents"]["defaults"]["models"][provider_model_ref] = {}
    
    save_openclaw_config(config)
    return True


def remove_agent_model(provider_model_ref):
    """从 agents.defaults.models 移除模型"""
    config = get_openclaw_config()
    models = config.get("agents", {}).get("defaults", {}).get("models", {})
    if provider_model_ref in models:
        del models[provider_model_ref]
        save_openclaw_config(config)
        return True
    return False


# =============================================================================
# Default Model Selection (agents.defaults.model)
# =============================================================================

def get_default_model():
    """获取默认模型配置 (primary + fallbacks)"""
    config = get_openclaw_config()
    model_config = config.get("agents", {}).get("defaults", {}).get("model", {})
    return {
        "primary": model_config.get("primary", ""),
        "fallbacks": model_config.get("fallbacks", [])
    }


def set_default_model(primary, fallbacks=None):
    """
    设置默认模型 (primary + fallbacks)
    
    Args:
        primary: 主模型，如 "minimax/MiniMax-M2.7"
        fallbacks: 备用模型列表
    """
    config = get_openclaw_config()
    if "agents" not in config:
        config["agents"] = {}
    if "defaults" not in config["agents"]:
        config["agents"]["defaults"] = {}
    if "model" not in config["agents"]["defaults"]:
        config["agents"]["defaults"]["model"] = {}
    
    config["agents"]["defaults"]["model"]["primary"] = primary
    if fallbacks is not None:
        config["agents"]["defaults"]["model"]["fallbacks"] = fallbacks
    
    save_openclaw_config(config)
    return True


def clear_default_model():
    """清除默认模型配置"""
    config = get_openclaw_config()
    if "agents" in config and "defaults" in config["agents"] and "model" in config["agents"]["defaults"]:
        del config["agents"]["defaults"]["model"]
        save_openclaw_config(config)
    return True


# =============================================================================
# Misc
# =============================================================================

def get_models():
    """获取模型配置（兼容旧接口）"""
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

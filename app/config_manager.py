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

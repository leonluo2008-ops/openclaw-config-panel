#!/usr/bin/env python3
# server.py - OpenClaw Config Panel Web Server
import os
import sys
import argparse
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)
app.template_folder = "../templates"
app.static_folder = "../static"

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config_manager


@app.route("/")
def index():
    bots = config_manager.list_bots()
    bindings = config_manager.get_bindings()
    agents = config_manager.get_agents()
    models = config_manager.get_models()
    service_ok = config_manager.service_status()
    model_providers = config_manager.get_model_providers()
    agent_models = config_manager.get_agent_models()
    default_model = config_manager.get_default_model()
    
    return render_template(
        "index.html",
        bots=bots,
        bindings=bindings,
        agents=agents,
        models=models,
        model_providers=model_providers,
        agent_models=agent_models,
        default_model=default_model,
        service_ok=service_ok
    )


# ---- Bot Management API ----

@app.route("/api/bots", methods=["GET"])
def api_list_bots():
    return jsonify(config_manager.list_bots())


@app.route("/api/bots/<name>", methods=["GET"])
def api_get_bot(name):
    bot = config_manager.get_bot(name)
    if bot is None:
        return jsonify({"error": "Bot not found"}), 404
    return jsonify(bot)


@app.route("/api/bots", methods=["POST"])
def api_add_bot():
    data = request.json
    
    name = data.get("name", "").strip()
    appId = data.get("appId", "").strip()
    appSecret = data.get("appSecret", "").strip()
    dmPolicy = data.get("dmPolicy", "open")
    groupPolicy = data.get("groupPolicy", "closed")
    webhookPath = data.get("webhookPath", "/feishu/events")
    
    if not name or not appId or not appSecret:
        return jsonify({"error": "name, appId, appSecret are required"}), 400
    
    try:
        config_manager.backup_current()
        config_manager.add_bot(name, appId, appSecret, dmPolicy, groupPolicy, webhookPath)
        return jsonify({"success": True, "name": name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bots/<name>", methods=["PUT"])
def api_update_bot(name):
    data = request.json
    
    try:
        config_manager.backup_current()
        config_manager.update_bot(name, **data)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bots/<name>", methods=["DELETE"])
def api_delete_bot(name):
    try:
        config_manager.backup_current()
        config_manager.delete_bot(name)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bots/<name>/enable", methods=["POST"])
def api_enable_bot(name):
    try:
        config_manager.backup_current()
        config_manager.update_bot(name, enabled=True)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bots/<name>/disable", methods=["POST"])
def api_disable_bot(name):
    try:
        config_manager.backup_current()
        config_manager.update_bot(name, enabled=False)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---- Binding API ----

@app.route("/api/bindings", methods=["GET"])
def api_list_bindings():
    return jsonify(config_manager.get_bindings())


@app.route("/api/bindings", methods=["POST"])
def api_set_binding():
    data = request.json
    agentId = data.get("agentId", "").strip()
    accountId = data.get("accountId", "").strip()
    
    if not agentId or not accountId:
        return jsonify({"error": "agentId and accountId are required"}), 400
    
    try:
        config_manager.backup_current()
        config_manager.set_binding(agentId, accountId)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bindings/<agentId>", methods=["DELETE"])
def api_remove_binding(agentId):
    try:
        config_manager.backup_current()
        config_manager.remove_binding(agentId)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Model Provider API (models.providers)
# =============================================================================

@app.route("/api/models/providers", methods=["GET"])
def api_list_model_providers():
    """获取所有模型 Provider"""
    providers = config_manager.get_model_providers()
    # 脱敏 apiKey
    result = {}
    for name, conf in providers.items():
        p = dict(conf)
        if "apiKey" in p:
            p["apiKey_masked"] = config_manager.mask_secret(p["apiKey"])
        result[name] = p
    return jsonify(result)


@app.route("/api/models/providers/<name>", methods=["GET"])
def api_get_model_provider(name):
    """获取单个 Provider"""
    provider = config_manager.get_model_provider(name)
    if provider is None:
        return jsonify({"error": "Provider not found"}), 404
    p = dict(provider)
    if "apiKey" in p:
        p["apiKey_masked"] = config_manager.mask_secret(p["apiKey"])
    return jsonify(p)


@app.route("/api/models/providers", methods=["POST"])
def api_add_model_provider():
    """添加新 Provider"""
    data = request.json
    
    name = data.get("name", "").strip()
    baseUrl = data.get("baseUrl", "").strip()
    apiKey = data.get("apiKey", "").strip()
    api = data.get("api", "anthropic-messages")
    authHeader = data.get("authHeader", False)
    
    if not name or not baseUrl:
        return jsonify({"error": "name and baseUrl are required"}), 400
    
    try:
        config_manager.backup_current()
        config_manager.add_model_provider(name, baseUrl, apiKey, api, authHeader)
        return jsonify({"success": True, "name": name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models/providers/<name>", methods=["PUT"])
def api_update_model_provider(name):
    """更新 Provider"""
    data = request.json
    
    try:
        config_manager.backup_current()
        # 只传递非 None 的字段
        kwargs = {k: v for k, v in data.items() if v is not None}
        config_manager.update_model_provider(name, **kwargs)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models/providers/<name>", methods=["DELETE"])
def api_delete_model_provider(name):
    """删除 Provider"""
    try:
        config_manager.backup_current()
        config_manager.delete_model_provider(name)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Model API (within Provider)
# =============================================================================

@app.route("/api/models/providers/<provider_name>/models", methods=["POST"])
def api_add_model(provider_name):
    """向 Provider 添加模型"""
    data = request.json
    
    required_fields = ["id"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"Field '{field}' is required"}), 400
    
    try:
        config_manager.backup_current()
        config_manager.add_model_to_provider(provider_name, data)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models/providers/<provider_name>/models/<model_id>", methods=["PUT"])
def api_update_model(provider_name, model_id):
    """更新 Provider 中的模型"""
    data = request.json
    
    try:
        config_manager.backup_current()
        kwargs = {k: v for k, v in data.items() if v is not None}
        ok = config_manager.update_model_in_provider(provider_name, model_id, **kwargs)
        if ok:
            return jsonify({"success": True})
        return jsonify({"error": "Model not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models/providers/<provider_name>/models/<model_id>", methods=["DELETE"])
def api_delete_model(provider_name, model_id):
    """从 Provider 删除模型"""
    try:
        config_manager.backup_current()
        ok = config_manager.delete_model_from_provider(provider_name, model_id)
        if ok:
            return jsonify({"success": True})
        return jsonify({"error": "Model not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Agent Model API (agents.defaults.models)
# =============================================================================

@app.route("/api/models/agent", methods=["GET"])
def api_get_agent_models():
    """获取 agents.defaults.models（别名/白名单）"""
    return jsonify(config_manager.get_agent_models())


@app.route("/api/models/agent", methods=["POST"])
def api_set_agent_model():
    """添加/更新模型别名"""
    data = request.json
    ref = data.get("ref", "").strip()
    alias = data.get("alias", "").strip() or None
    
    if not ref:
        return jsonify({"error": "ref (provider/model-id) is required"}), 400
    
    try:
        config_manager.backup_current()
        config_manager.set_agent_model(ref, alias)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models/agent/<path:ref>", methods=["DELETE"])
def api_remove_agent_model(ref):
    """移除模型别名"""
    try:
        config_manager.backup_current()
        config_manager.remove_agent_model(ref)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Default Model API (agents.defaults.model)
# =============================================================================

@app.route("/api/models/default", methods=["GET"])
def api_get_default_model():
    """获取默认模型配置 (primary + fallbacks)"""
    return jsonify(config_manager.get_default_model())


@app.route("/api/models/default", methods=["POST"])
def api_set_default_model():
    """设置默认模型"""
    data = request.json
    primary = data.get("primary", "").strip()
    fallbacks = data.get("fallbacks", [])
    
    if not primary:
        return jsonify({"error": "primary model is required"}), 400
    
    try:
        config_manager.backup_current()
        config_manager.set_default_model(primary, fallbacks)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models/default", methods=["DELETE"])
def api_clear_default_model():
    """清除默认模型"""
    try:
        config_manager.backup_current()
        config_manager.clear_default_model()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# Service Control
# =============================================================================

@app.route("/api/service/restart", methods=["POST"])
def api_restart_service():
    try:
        ok = config_manager.restart_service()
        if ok:
            return jsonify({"success": True, "message": "Service restarted"})
        else:
            return jsonify({"error": "Restart failed"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/service/status", methods=["GET"])
def api_service_status():
    return jsonify({"running": config_manager.service_status()})


# ---- Backup ----

@app.route("/api/backup", methods=["POST"])
def api_backup():
    try:
        path = config_manager.backup_current()
        return jsonify({"success": True, "path": path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18790)
    parser.add_argument("--host", default="0.0.0.0")  # 局域网其他电脑可访问
    parser.add_argument("--auth", default="")           # Basic Auth 用户:密码，例 admin:123456
    args = parser.parse_args()
    
    # Basic Auth 中间件
    if args.auth:
        from functools import wraps
        import base64
        
        user, password = args.auth.split(":", 1)
        
        @app.before_request
        def basic_auth():
            from flask import request
            auth = request.authorization
            if not auth or auth.username != user or auth.password != password:
                return ("需要认证", 401, {"WWW-Authenticate": 'Basic realm="OpenClaw Config Panel"'})
    
    print(f"Starting OpenClaw Config Panel on http://{args.host}:{args.port}")
    if args.auth:
        print(f"Basic Auth: {user}:****")
    app.run(host=args.host, port=args.port, debug=False)

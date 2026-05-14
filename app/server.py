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
    
    return render_template(
        "index.html",
        bots=bots,
        bindings=bindings,
        agents=agents,
        models=models,
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


# ---- Agent Management API ----

@app.route("/api/agents", methods=["GET"])
def api_list_agents():
    return jsonify(config_manager.get_agents())


@app.route("/api/agents", methods=["POST"])
def api_add_agent():
    data = request.json
    agent_id = data.get("id", "").strip()
    name = data.get("name", "").strip()
    workspace = data.get("workspace", "").strip()
    model = data.get("model", "").strip()
    
    if not agent_id:
        return jsonify({"error": "Agent ID 不能为空"}), 400
    
    # 验证 ID 格式（只允许字母、数字、连字符、下划线）
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', agent_id):
        return jsonify({"error": "Agent ID 只允许字母、数字、连字符和下划线"}), 400
    
    try:
        config_manager.backup_current()
        config_manager.create_agent(agent_id, name=name or None, workspace=workspace or None, model=model or None)
        return jsonify({"success": True, "id": agent_id})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents/<agent_id>", methods=["PUT"])
def api_update_agent(agent_id):
    data = request.json
    
    try:
        config_manager.backup_current()
        config_manager.update_agent(agent_id, **data)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents/<agent_id>", methods=["DELETE"])
def api_delete_agent(agent_id):
    try:
        config_manager.backup_current()
        config_manager.delete_agent(agent_id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---- Agent Core Files API ----

@app.route("/api/agents/<agent_id>/files", methods=["GET"])
def api_list_agent_files(agent_id):
    files = config_manager.list_core_files(agent_id)
    if files is None:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify(files)


@app.route("/api/agents/<agent_id>/files/<filename>", methods=["GET"])
def api_get_agent_file(agent_id, filename):
    content = config_manager.get_core_file(agent_id, filename)
    if content is None:
        return jsonify({"error": "File not found or not supported"}), 404
    return jsonify({"filename": filename, "content": content})


@app.route("/api/agents/<agent_id>/files/<filename>", methods=["PUT"])
def api_save_agent_file(agent_id, filename):
    data = request.json
    content = data.get("content", "")

    try:
        config_manager.backup_current()
        config_manager.save_core_file(agent_id, filename, content)
        return jsonify({"success": True, "filename": filename})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents/<agent_id>/files/<filename>/template", methods=["GET"])
def api_get_file_template(agent_id, filename):
    config = config_manager.get_openclaw_config()
    agents_list = config.get("agents", {}).get("list", [])
    agent_name = None
    for a in agents_list:
        if a.get("id", a.get("name", "")) == agent_id:
            agent_name = a.get("name", "")
            break
    template = config_manager.generate_template(filename, agent_id, agent_name)
    return jsonify({"filename": filename, "content": template})


# ---- Model Config API ----

@app.route("/api/models/config", methods=["GET"])
def api_get_model_config():
    return jsonify(config_manager.get_model_config())


@app.route("/api/models/default", methods=["PUT"])
def api_set_default_model():
    data = request.json
    model_id = data.get("model", "").strip()
    if not model_id:
        return jsonify({"error": "模型 ID 不能为空"}), 400
    try:
        config_manager.backup_current()
        config_manager.set_default_model(model_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models/allowlist/<path:model_id>/alias", methods=["PUT"])
def api_set_model_alias(model_id):
    data = request.json
    alias = data.get("alias", "").strip()
    try:
        config_manager.backup_current()
        config_manager.set_model_alias(model_id, alias)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models/allowlist", methods=["POST"])
def api_add_to_allowlist():
    data = request.json
    model_id = data.get("model", "").strip()
    alias = data.get("alias", "").strip()
    if not model_id:
        return jsonify({"error": "模型 ID 不能为空"}), 400
    try:
        config_manager.backup_current()
        config_manager.add_to_allowlist(model_id, alias)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/models/allowlist/<path:model_id>", methods=["DELETE"])
def api_remove_from_allowlist(model_id):
    try:
        config_manager.backup_current()
        config_manager.remove_from_allowlist(model_id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents/<agent_id>/model", methods=["PUT"])
def api_set_agent_model(agent_id):
    data = request.json
    model_id = data.get("model", "").strip()
    if not model_id:
        return jsonify({"error": "模型 ID 不能为空"}), 400
    try:
        config_manager.backup_current()
        config_manager.set_agent_model(agent_id, model_id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---- Provider Management API ----

@app.route("/api/providers/available", methods=["GET"])
def api_get_available_providers():
    return jsonify(config_manager.get_available_providers())


@app.route("/api/providers/schema", methods=["GET"])
def api_get_provider_schema():
    return jsonify(config_manager.get_provider_schema())


@app.route("/api/providers/<provider_id>", methods=["PUT"])
def api_add_provider(provider_id):
    data = request.json
    base_url = data.get("baseUrl", "").strip()
    api_key = data.get("apiKey", "").strip()
    api = data.get("api", "openai-completions").strip()
    models = data.get("models")

    if not base_url:
        return jsonify({"error": "Base URL 不能为空"}), 400

    try:
        config_manager.backup_current()
        config_manager.add_provider(provider_id, base_url, api_key, api, models)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/providers/<provider_id>", methods=["DELETE"])
def api_remove_provider(provider_id):
    try:
        config_manager.backup_current()
        config_manager.remove_provider(provider_id)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---- Skill Management API ----

@app.route("/api/skills", methods=["GET"])
def api_get_all_skills():
    return jsonify(config_manager.get_all_skills())


@app.route("/api/skills/<skill_id>/enabled", methods=["PUT"])
def api_set_skill_enabled(skill_id):
    data = request.json
    enabled = data.get("enabled", True)
    try:
        config_manager.backup_current()
        config_manager.set_skill_enabled(skill_id, enabled)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/skills/default", methods=["PUT"])
def api_set_default_skills():
    data = request.json
    skill_ids = data.get("skills")
    try:
        config_manager.backup_current()
        config_manager.set_default_skills(skill_ids)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents/<agent_id>/skills", methods=["PUT"])
def api_set_agent_skills(agent_id):
    data = request.json
    skill_ids = data.get("skills")
    try:
        config_manager.backup_current()
        config_manager.set_agent_skills(agent_id, skill_ids)
        return jsonify({"success": True})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---- Service Control ----

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

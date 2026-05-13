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
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    
    print(f"Starting OpenClaw Config Panel on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)

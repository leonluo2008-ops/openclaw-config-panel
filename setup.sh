#!/bin/bash
#===========================================================
# setup.sh - 安装 openclaw-config-panel
#
# 用法: bash setup.sh [--port 18790]
#===========================================================

set -e

PORT="${1:-18790}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PANEL_ROOT="$HOME/openclaw-config-panel"

echo "安装 openclaw-config-panel 到 $PANEL_ROOT"
echo "端口: $PORT"

# 克隆或更新仓库
if [ ! -d "$PANEL_ROOT/.git" ]; then
    git clone https://github.com/leonluo2008-ops/openclaw-config-panel.git "$PANEL_ROOT" 2>/dev/null || {
        echo "仓库不存在，初始化新仓库..."
        mkdir -p "$PANEL_ROOT"
        cd "$PANEL_ROOT"
        git init
    }
else
    cd "$PANEL_ROOT"
    git pull origin main 2>/dev/null || true
fi

# 复制 app 到目标目录
cp -r "$SCRIPT_DIR/app "$PANEL_ROOT/"
cp -r "$SCRIPT_DIR/templates "$PANEL_ROOT/"
cp -r "$SCRIPT_DIR/static "$PANEL_ROOT/"

# 安装依赖
pip3 install flask jq 2>/dev/null || true

# 启动服务
cd "$PANEL_ROOT"
nohup python3 app/server.py --port $PORT > app/panel.log 2>&1 &
echo "服务已启动: http://localhost:$PORT"
echo "日志: $PANEL_ROOT/app/panel.log"
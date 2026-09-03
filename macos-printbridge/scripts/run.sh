#!/bin/bash
# PrintBridge 启动脚本：确保 uvicorn/fastapi 在用户 site-packages 可见
export HOME=/Users/vanhci
export PYTHONPATH=/Users/vanhci/Library/Python/3.9/lib/python/site-packages
cd /Users/vanhci/works/printbridge || exit 1
exec /usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8899
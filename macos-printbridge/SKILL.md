---
name: macos-printbridge
description: Mac mini 打印桥：老打印机接入 CUPS + 公网打印页 + HA 面板整合。触发：配置打印机远程打印、打印桥服务、HA 打印视图。
category: devops
---

# Mac 打印桥（PrintBridge）

将局域网内支持 AirPrint/IPP 的打印机接入 Mac mini CUPS，提供公网打印页面，并整合到 Home Assistant 仪表盘。

**适用场景**：云打印服务停止/不支持的老打印机，需要远程打印能力。

## 前置条件

- macOS（已安装 CUPS，macOS 自带）
- 打印机在同一局域网，支持 AirPrint/IPP（mDNS 可发现）
- Home Assistant 已部署（可选，用于 HA 面板整合）
- Cloudflare Tunnel 已运行（可选，用于公网访问）

## Step 1：发现打印机

```bash
dns-sd -B _ipp._tcp local.
```

找到打印机名称和 IP（如 `Canon TS8000 series` → IP 192.168.x.x）。

## Step 2：接入 CUPS

```bash
# 获取打印机 URI（替换为实际 IP）
dns-sd -L "打印机名称" _ipp._tcp local. | grep "reached at"
# 输出格式：printer-name.local:631 → 记下 rp=ipp/print

# 添加打印机（driverless 模式）
lpadmin -p <printer-name> -E -v "ipp://<printer-ip>:631/ipp/print" -m everywhere

# 验证
lpstat -p <printer-name>
```

## Step 3：部署打印桥服务

### 3.1 代码结构

```
~/works/printbridge/
├── main.py          # FastAPI 服务（后端）
├── web/
│   └── index.html   # 打印页面（前端）
└── run.sh           # 启动脚本（设置环境变量）
```

- `main.py`：核心服务，提供 `/print`（上传打印）、`/status`（打印机状态）接口
- `web/index.html`：单页应用，支持彩色/黑白、单双面、纸张/介质/质量选择
- `run.sh`：设置 `PYTHONPATH` 指向 hermes venv 的 site-packages

### 3.2 启动服务

```bash
# 手动测试
cd ~/works/printbridge
python3 -m uvicorn main:app --host 0.0.0.0 --port 8899

# 浏览器访问 http://localhost:8899 测试上传打印
```

### 3.3 配置 launchd 自启

创建 `~/Library/LaunchAgents/com.<user>.printbridge.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.<user>.printbridge</string>
  <key>ProgramArguments</key>
  <array>
    <string><hermes-venv>/bin/python3</string>
    <string>/Users/<user>/works/printbridge/main.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/<user>/works/printbridge</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/tmp/printbridge.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/printbridge.err.log</string>
</dict>
</plist>
```

**关键**：必须用 hermes venv 的 python（系统 python3 没有 uvicorn/fastapi，bash 包装脚本在外接盘路径会被 TCC 拦截）。

```bash
# 加载服务
launchctl load ~/Library/LaunchAgents/com.<user>.printbridge.plist

# 验证
curl -s http://localhost:8899/status
```

## Step 4：公网访问（Cloudflare Tunnel）

### 4.1 添加 ingress 规则

编辑 `~/.cloudflared/config.yml`，在 `ingress:` 下添加：

```yaml
- hostname: <your-print-domain>
  service: http://localhost:8899
  originRequest:
    httpHostHeader: localhost:8899
```

### 4.2 添加 DNS 记录

```bash
# 自动添加 CNAME 到隧道（需要 cloudflared 登录态）
cloudflared tunnel route dns <tunnel-id> <your-print-domain>
```

### 4.3 重启隧道

```bash
# launchd 管理的隧道会自动重启，或手动：
launchctl kickstart -k "gui/$(id -u)/com.hermes.cloudflared"
```

## Step 5：整合到 Home Assistant

通过 HA WebSocket API 热更新仪表盘（不重启 HA）：

```python
import json, asyncio, websockets

async def add_print_view(ha_url, token):
    async with websockets.connect(f"{ha_url}/api/websocket") as ws:
        await ws.recv()  # auth_required
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        await ws.recv()  # auth_ok

        # 获取仪表盘配置
        await ws.send(json.dumps({"type": "lovelace/config", "url_path": "<dashboard-url-path>", "id": 1}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 1:
                cfg = r["result"]
                break

        # 添加打印视图（panel 全屏模式）
        new_view = {
            "path": "print",
            "title": "打印",
            "icon": "mdi:printer",
            "type": "panel",
            "cards": [{"type": "iframe", "url": f"https://<your-print-domain>", "title": "🖨️ 打印机"}]
        }
        cfg["views"].append(new_view)

        # 保存
        await ws.send(json.dumps({"type": "lovelace/config/save", "url_path": "<dashboard-url-path>", "config": cfg, "id": 2}))
        while True:
            r = json.loads(await ws.recv())
            if r.get("id") == 2:
                print("save:", r.get("success"))
                break
```

## 打印选项说明

| 选项 | 值 | CUPS 参数 |
|------|-----|-----------|
| 份数 | 1-99 | `-n <copies>` |
| 颜色 | 彩色/黑白 | `-o ColorModel=Gray`（黑白）|
| 双面 | 单面/长边/短边 | `-o Duplex=DuplexNoTumble`/`DuplexTumble` |
| 纸张 | A4/A5/Letter/4×6/5×7/B5 | `-o PageSize=<size>` |
| 介质 | 普通纸/相纸/信封 | `-o MediaType=Photographic`/`Envelope` |
| 质量 | 草稿/标准/高 | `-o cupsPrintQuality=Draft`/`Normal`/`High` |

**注意**：非 A4 纸张（A5、相纸等）需先手动装入打印机纸盒，否则作业会排队等待。

## 排障

| 问题 | 排查 |
|------|------|
| 打印作业卡住不走纸 | 检查打印机是否缺纸/卡纸：`lpstat -o <printer-name>` 查看作业状态 |
| 公网访问 502 | 检查 cloudflared 隧道：`curl https://<ha-domain>/` 看 HA 是否正常 |
| launchd 服务启动失败 | 查日志：`cat /tmp/printbridge.err.log`；常见原因：python 路径错误、uvicorn 未安装 |
| 打印机状态一直显示"离线" | 打印机可能休眠：发送一个测试打印作业唤醒（`echo test \| lp -d <printer-name>`）|
| HA 视图不显示 | 检查 WebSocket API 返回：`save: true` 表示成功，刷新 HA 页面 |

## References

- [CUPS 打印管理](https://www.cups.org/documentation.html)
- [AirPrint 协议](https://support.apple.com/en-us/108091)
- [Cloudflare Tunnel 配置](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/)
- [HA Lovelace WebSocket API](https://developers.home-assistant.io/docs/api/websocket/)

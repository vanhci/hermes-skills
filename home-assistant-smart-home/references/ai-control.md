# AI 助手接管

## REST API 控制

```bash
# 查全部设备状态
curl -H "Authorization: Bearer <token>" http://<nas-ip>:8123/api/states

# 控制设备
curl -X POST -H "Authorization: Bearer <token>" \
  http://<nas-ip>:8123/api/services/switch/turn_on \
  -d '{"entity_id":"switch.xxx_power"}'
```

## 让 AI Agent 代劳一切

真正的懒人玩法：**整个部署、接入、调仪表盘的过程都可以交给 AI Agent 做**（如 Hermes Agent）：

- 它 SSH 进 NAS 改防火墙、改配置、重启容器
- 它下载 APK 逆向、破解协议、写自定义集成
- 它调 HA API 读全部实体、自动分组排版仪表盘
- 你只需要说"我要什么结果"，它负责"怎么做"

分工原则：**大方向你定（方案选择/账号决策），细节它执行**。关键决策点它停下来让你选，其余全自动。

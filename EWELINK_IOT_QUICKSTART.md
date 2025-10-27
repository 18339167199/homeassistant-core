# eWeLink IoT 集成快速开始指南

## 🎯 集成概述

eWeLink IoT 集成让您可以在 Home Assistant 中控制 eWeLink 云平台的设备。

### 主要特性
✅ 账号登录认证
✅ 设备自动同步
✅ 实时状态更新（WebSocket 长连接）
✅ 多通道开关支持
✅ 重新认证支持

## 📦 文件清单

### 核心文件
```
homeassistant/components/ewelink_iot/
├── __init__.py          # 主入口：设置集成，创建协调器
├── api.py               # HTTP API 客户端：登录、获取设备、控制设备
├── websocket.py         # WebSocket 客户端：实时状态更新
├── coordinator.py       # 数据协调器：管理数据获取和 WebSocket
├── config_flow.py       # UI 配置流程：用户登录界面
├── entity.py            # 基础实体类：所有实体的父类
├── switch.py            # Switch 平台：开关设备实现
├── const.py             # 常量定义
├── manifest.json        # 集成元数据
├── strings.json         # UI 文本翻译
└── quality_scale.yaml   # 质量标准配置
```

### 测试文件
```
tests/components/ewelink_iot/
├── __init__.py
├── conftest.py          # 测试 fixtures
├── test_config_flow.py  # 配置流程测试
└── test_init.py         # 初始化测试
```

## 🚀 使用方法

### 1. 添加集成

在 Home Assistant 中：
1. 设置 → 设备与服务 → 添加集成
2. 搜索 "eWeLink IoT"
3. 输入登录信息

### 2. 登录参数

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| Email | ✅ | eWeLink 账号邮箱 | user@example.com |
| Password | ✅ | 账号密码 | ******** |
| Region | ❌ | 服务器区域 | cn (默认) |
| App ID | ❌ | 应用 ID | 使用默认值 |
| App Secret | ❌ | 应用密钥 | 使用默认值 |

### 3. 区域选项

- `cn` - 中国 (默认)
- `as` - 亚洲
- `us` - 美洲
- `eu` - 欧洲

## 💡 工作原理

### 数据流程图

```
┌─────────────────┐
│   用户配置      │
│  (config_flow)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   登录 API      │
│   获取 Token    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  创建协调器     │
│  (Coordinator)  │
└────────┬────────┘
         │
         ├─────────────────┬──────────────────┐
         ▼                 ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  HTTP API    │  │  WebSocket   │  │  设备实体    │
│ (定期轮询)   │  │  (实时推送)  │  │   (Switch)   │
└──────────────┘  └──────────────┘  └──────────────┘
```

### 状态更新机制

**方式1：HTTP 轮询（备用）**
- 每 5 分钟自动轮询一次
- 确保长期数据一致性

**方式2：WebSocket 推送（主要）**
- 设备状态改变时立即推送
- 延迟低于 1 秒
- 自动重连机制

### 设备控制流程

```
用户操作
  ↓
调用 async_turn_on/off()
  ↓
发送 API 请求到 eWeLink
  ↓
本地立即更新状态 (乐观更新)
  ↓
WebSocket 收到确认消息
  ↓
最终状态同步完成
```

## 📝 代码示例

### 创建单通道开关

设备 params:
```json
{
  "switch": "on"
}
```

生成实体:
```
switch.device_name
```

### 创建多通道开关

设备 params:
```json
{
  "switches": [
    {"switch": "on"},
    {"switch": "off"},
    {"switch": "on"}
  ]
}
```

生成实体:
```
switch.device_name_channel_1
switch.device_name_channel_2
switch.device_name_channel_3
```

### 在自动化中使用

```yaml
# 示例：早上7点开启所有通道
automation:
  - alias: "Morning Switches On"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id:
            - switch.living_room_channel_1
            - switch.living_room_channel_2
            - switch.living_room_channel_3
```

## 🔧 开发和调试

### 运行验证

```bash
# 验证集成结构
python3 -m script.hassfest --integration-path homeassistant/components/ewelink_iot

# 生成依赖文件
python3 -m script.gen_requirements_all

# 编译翻译
python3 -m script.translations develop --integration ewelink_iot

# 运行测试
pytest tests/components/ewelink_iot/ \
  --cov=homeassistant.components.ewelink_iot \
  --cov-report term-missing
```

### 查看日志

在 `configuration.yaml` 中添加：
```yaml
logger:
  default: info
  logs:
    homeassistant.components.ewelink_iot: debug
```

### 常见问题

**Q: 设备不显示？**
- 检查登录账号是否正确
- 确认区域选择是否匹配
- 查看日志中的错误信息

**Q: 状态不更新？**
- 检查 WebSocket 连接状态
- 查看网络是否稳定
- 等待下次轮询更新（最多5分钟）

**Q: 控制失败？**
- 检查设备是否在线
- 确认 Token 是否过期（会自动重新认证）
- 查看 API 错误日志

## 🎓 技术亮点

1. **异步编程**
   - 所有操作都是非阻塞的
   - 使用 `async/await` 语法
   - 遵循 Home Assistant 最佳实践

2. **数据协调器模式**
   - 统一管理数据获取
   - 避免重复请求
   - 高效的状态共享

3. **实时通信**
   - WebSocket 长连接
   - 自动重连
   - 事件驱动更新

4. **用户体验**
   - UI 配置流程
   - 支持重新认证
   - 多语言支持

## 📚 参考资源

- [Home Assistant 开发文档](https://developers.home-assistant.io/)
- [集成质量标准](https://developers.home-assistant.io/docs/integration_quality_scale/)
- [异步编程最佳实践](https://developers.home-assistant.io/docs/asyncio_working_with_async/)
- [配置流程文档](https://developers.home-assistant.io/docs/config_entries_config_flow_handler/)

## 📄 许可证

Apache 2.0 License - 与 Home Assistant 相同

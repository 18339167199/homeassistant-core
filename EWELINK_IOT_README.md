# eWeLink IoT 集成

这是一个为 Home Assistant 开发的 eWeLink IoT 云平台集成。

## 功能特性

### ✅ 已实现的功能

1. **账号登录**
   - 通过 UI 配置流程登录 eWeLink 账号
   - 支持多个区域（中国、亚洲、美洲、欧洲）
   - 支持重新认证流程

2. **设备同步**
   - 自动同步 eWeLink 平台的所有设备
   - 支持多通道开关设备
   - 设备状态实时更新

3. **WebSocket 长连接**
   - 建立与 eWeLink 云平台的 WebSocket 连接
   - 实时接收设备状态变化推送
   - 自动重连机制

4. **开关控制**
   - 支持单通道开关
   - 支持多通道开关（如三通道开关）
   - 每个通道作为独立的 switch 实体

## 文件结构

```
homeassistant/components/ewelink_iot/
├── __init__.py              # 集成入口点
├── api.py                   # eWeLink API 客户端
├── config_flow.py           # 配置流程
├── const.py                 # 常量定义
├── coordinator.py           # 数据更新协调器
├── entity.py                # 基础实体类
├── manifest.json            # 集成元数据
├── quality_scale.yaml       # 质量等级配置
├── strings.json             # 翻译字符串
├── switch.py                # 开关平台
└── websocket.py             # WebSocket 客户端

tests/components/ewelink_iot/
├── __init__.py
├── conftest.py              # 测试 fixtures
├── test_config_flow.py      # 配置流程测试
└── test_init.py             # 初始化测试
```

## 核心组件说明

### 1. API 客户端 (`api.py`)

提供与 eWeLink HTTP API 的交互：
- `login()` - 用户登录，获取 access token
- `get_devices()` - 获取所有设备列表
- `set_device_status()` - 设置设备状态

支持的异常：
- `EWeLinkAuthError` - 认证失败
- `EWeLinkConnectionError` - 连接失败
- `EWeLinkApiError` - API 错误

### 2. WebSocket 客户端 (`websocket.py`)

处理实时设备状态更新：
- 自动建立 WebSocket 连接
- 发送握手消息进行认证
- 接收设备状态变化消息
- 自动重连机制（10秒延迟）
- 支持设备级别的回调注册

### 3. 数据协调器 (`coordinator.py`)

管理数据获取和更新：
- 继承自 `DataUpdateCoordinator`
- 5分钟更新间隔（通过 API 轮询）
- 管理 WebSocket 连接
- 处理设备数据缓存
- 支持 WebSocket 回调注册

### 4. 配置流程 (`config_flow.py`)

用户配置界面：
- `async_step_user` - 初始配置步骤
- `async_step_reauth_confirm` - 重新认证步骤
- 支持的输入字段：
  - Email（必填）
  - Password（必填）
  - Region（可选，默认中国）
  - App ID（可选）
  - App Secret（可选）

### 5. Switch 平台 (`switch.py`)

实现开关实体：
- 支持单通道开关
- 支持多通道开关
- 每个通道作为独立实体
- 实时状态更新（通过 WebSocket）
- 状态控制（通过 API）

## 数据流程

### 初始化流程
```
1. 用户在 UI 中输入账号密码
2. config_flow 验证登录
3. 创建 ConfigEntry
4. __init__ 中创建 API 客户端和 WebSocket 客户端
5. 创建 DataUpdateCoordinator
6. 执行首次数据获取
7. 建立 WebSocket 连接
8. 设置 switch 平台
9. 为每个设备创建 switch 实体
```

### 状态更新流程
```
方式1：定期轮询（每5分钟）
Coordinator -> API.get_devices() -> 更新设备数据 -> 触发实体更新

方式2：实时推送（WebSocket）
eWeLink 服务器 -> WebSocket 消息 -> 回调函数 -> 更新设备数据 -> 触发实体更新
```

### 控制流程
```
用户操作 -> Switch.async_turn_on/off() -> API.set_device_status() ->
本地立即更新 -> WebSocket 确认 -> 最终状态一致
```

## 使用示例

### 配置集成

1. 打开 Home Assistant
2. 进入 设置 > 设备与服务
3. 点击 "添加集成"
4. 搜索 "eWeLink IoT"
5. 输入账号信息：
   - Email: your_email@example.com
   - Password: your_password
   - Region: cn（中国）

### 设备示例

配置完成后，如果你的 eWeLink 账号下有一个三通道开关，将会创建3个 switch 实体：

- `switch.device_name_channel_1`
- `switch.device_name_channel_2`
- `switch.device_name_channel_3`

### 自动化示例

```yaml
automation:
  - alias: "打开所有通道"
    trigger:
      - platform: time
        at: "07:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id:
            - switch.device_name_channel_1
            - switch.device_name_channel_2
            - switch.device_name_channel_3
```

## 技术要点

### 1. 异步编程
- 所有 I/O 操作都是异步的
- 使用 `aiohttp` 进行 HTTP 和 WebSocket 通信
- 不阻塞事件循环

### 2. 错误处理
- 登录失败自动触发重新认证流程
- WebSocket 断开自动重连
- API 调用失败标记实体为不可用

### 3. 性能优化
- 使用 WebSocket 减少 API 轮询
- 本地缓存设备数据
- 操作后立即更新本地状态，无需等待服务器确认

### 4. 符合 HA 规范
- 使用 DataUpdateCoordinator 模式
- 实现 config_flow 用户界面配置
- 支持 config entry 运行时数据
- 实现 async_setup_entry 和 async_unload_entry
- 使用 has_entity_name 和翻译系统

## API 端点

### HTTP API
- 基础 URL: `https://api.ewelink.cc/v2`
- 登录: `POST /user/login`
- 设备列表: `GET /device/thing`
- 设备控制: `POST /device/thing/status`

### WebSocket
- URL: `wss://api.ewelink.cc:8080/api/ws`
- 消息类型:
  - `userOnline` - 握手认证
  - `update` - 设备状态更新

## 待实现功能

1. 更多设备类型支持（灯光、传感器等）
2. 设备离线/在线事件
3. 场景控制
4. 诊断信息收集
5. 设备自动发现

## 测试

运行测试：
```bash
pytest tests/components/ewelink_iot/ \
  --cov=homeassistant.components.ewelink_iot \
  --cov-report term-missing
```

## 注意事项

1. **API 密钥**: 当前使用的是示例 App ID 和 App Secret，实际使用时应该申请官方密钥
2. **区域选择**: 确保选择正确的区域，否则可能无法连接
3. **WebSocket 稳定性**: 网络不稳定时可能需要多次重连
4. **设备兼容性**: 目前仅测试了开关设备，其他设备类型可能需要额外适配

## 许可证

本集成遵循 Home Assistant 的 Apache 2.0 许可证。

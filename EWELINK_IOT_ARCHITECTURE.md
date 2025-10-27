# eWeLink IoT 集成架构设计

## 系统架构概览

```
┌───────────────────────────────────────────────────────────────────┐
│                         Home Assistant                             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │                    eWeLink IoT Integration                    │ │
│  │                                                                │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐    │ │
│  │  │ Config Flow │  │ Coordinator  │  │  Entity Layer    │    │ │
│  │  │   (UI配置)  │  │  (数据管理)  │  │   (switch等)     │    │ │
│  │  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘    │ │
│  │         │                │                    │               │ │
│  │         └────────────────┴────────────────────┘               │ │
│  │                          │                                     │ │
│  │         ┌────────────────┴───────────────────┐               │ │
│  │         │                                     │               │ │
│  │    ┌────▼─────┐                      ┌───────▼──────┐        │ │
│  │    │ API      │                      │  WebSocket   │        │ │
│  │    │ Client   │                      │   Client     │        │ │
│  │    └────┬─────┘                      └───────┬──────┘        │ │
│  └─────────┼────────────────────────────────────┼───────────────┘ │
└────────────┼────────────────────────────────────┼─────────────────┘
             │                                     │
             │ HTTPS                               │ WSS
             │                                     │
┌────────────▼─────────────────────────────────────▼─────────────────┐
│                   eWeLink Cloud Platform                            │
│                    api.ewelink.cc                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## 核心组件详解

### 1. Config Flow (config_flow.py)

**职责**：用户界面配置和认证

**关键方法**：
- `async_step_user`: 初始配置步骤
  - 收集用户凭证（邮箱、密码）
  - 验证登录
  - 创建 ConfigEntry

- `async_step_reauth_confirm`: 重新认证
  - Token 过期时触发
  - 只需要重新输入密码
  - 更新现有 ConfigEntry

**数据流**：
```
用户输入
  ↓
验证凭证 (调用 API.login())
  ↓
设置 unique_id (邮箱)
  ↓
检查是否已配置
  ↓
创建/更新 ConfigEntry
```

**错误处理**：
- `invalid_auth`: 邮箱或密码错误
- `cannot_connect`: 网络连接失败
- `unknown`: 未知错误

---

### 2. API Client (api.py)

**职责**：与 eWeLink HTTP API 交互

**核心类**：
```python
class EWeLinkApiClient:
    def __init__(session, email, password, app_id, app_secret, region)
    async def login() -> dict
    async def get_devices() -> list[EWeLinkDevice]
    async def set_device_status(device_id, params) -> dict
```

**认证机制**：
```
1. 调用 /user/login
2. 获取 access_token
3. 后续请求携带 Bearer token
```

**设备数据结构**：
```python
@dataclass
class EWeLinkDevice:
    device_id: str          # 设备唯一ID
    name: str               # 设备名称
    brand_name: str         # 品牌名称
    product_model: str      # 产品型号
    device_type: str        # 设备类型
    online: bool            # 在线状态
    params: dict            # 设备参数（状态）
    tags: dict              # 标签信息
```

**API 端点**：
| 功能 | 方法 | 端点 | 说明 |
|------|------|------|------|
| 登录 | POST | /user/login | 获取 access token |
| 获取设备 | GET | /device/thing | 获取所有设备列表 |
| 控制设备 | POST | /device/thing/status | 设置设备状态 |

---

### 3. WebSocket Client (websocket.py)

**职责**：实时设备状态更新

**核心功能**：
```python
class EWeLinkWebSocketClient:
    async def connect()                    # 连接到 WebSocket
    async def _send_handshake()            # 发送握手认证
    async def _listen()                    # 监听消息
    def register_callback(device_id, cb)   # 注册回调
    async def disconnect()                 # 断开连接
```

**连接流程**：
```
1. 建立 WebSocket 连接 (wss://api.ewelink.cc:8080/api/ws)
2. 发送 handshake 消息
   {
     "action": "userOnline",
     "at": access_token,
     "apikey": api_key,
     ...
   }
3. 服务器返回认证结果
4. 开始监听设备更新消息
```

**消息处理**：
```python
# 接收到的消息格式
{
  "action": "update",
  "deviceid": "1000abcdef",
  "params": {
    "switch": "on"
  }
}

# 处理流程
收到消息
  ↓
解析 JSON
  ↓
查找 device_id 的回调函数
  ↓
调用所有注册的回调
  ↓
更新设备状态
```

**重连机制**：
```
连接断开
  ↓
等待 10 秒
  ↓
尝试重新连接
  ↓
如果失败，继续等待重试
```

---

### 4. Data Coordinator (coordinator.py)

**职责**：统一管理数据获取和更新

**继承关系**：
```python
class EWeLinkDataCoordinator(DataUpdateCoordinator[dict[str, EWeLinkDevice]]):
    pass
```

**核心功能**：
```python
async def _async_update_data()           # 定期更新数据（HTTP API）
async def async_setup()                  # 初始化设置
async def async_shutdown()               # 清理资源
def register_device_callback()           # 注册 WebSocket 回调
```

**更新策略**：
```
策略1：定期轮询
  - 间隔：5 分钟
  - 方法：HTTP API
  - 用途：保证数据一致性

策略2：实时推送
  - 触发：设备状态改变
  - 方法：WebSocket
  - 用途：低延迟更新
```

**数据结构**：
```python
# Coordinator.data 的格式
{
  "device_id_1": EWeLinkDevice(...),
  "device_id_2": EWeLinkDevice(...),
  ...
}
```

**回调机制**：
```python
# WebSocket 收到更新时
WebSocket 消息
  ↓
ws_callback(params)
  ↓
更新 coordinator.data[device_id].params
  ↓
调用实体的回调函数
  ↓
实体更新状态
```

---

### 5. Entity Layer (entity.py)

**职责**：所有实体的基类

**核心实现**：
```python
class EWeLinkEntity(CoordinatorEntity[EWeLinkDataCoordinator]):
    _attr_has_entity_name = True

    def __init__(coordinator, device_id):
        # 设置 device_info
        # 设置基础属性

    @property
    def available(self) -> bool:
        # 检查 coordinator 可用性
        # 检查设备在线状态
```

**设备信息**：
```python
DeviceInfo(
    identifiers={(DOMAIN, device_id)},
    name=device.name,
    manufacturer=device.brand_name or "eWeLink",
    model=device.product_model,
)
```

**可用性判断**：
```python
available = super().available and device.online
```

---

### 6. Switch Platform (switch.py)

**职责**：实现开关设备

**实体类型**：
1. **单通道开关**
   - unique_id: `{device_id}_switch`
   - name: 使用设备名称

2. **多通道开关**
   - unique_id: `{device_id}_switch_{channel}`
   - name: `Channel {channel + 1}`

**状态读取**：
```python
# 单通道
is_on = device.params.get("switch") == "on"

# 多通道
switches = device.params.get("switches", [])
is_on = switches[channel].get("switch") == "on"
```

**状态设置**：
```python
# 单通道
await api_client.set_device_status(
    device_id,
    {"switch": "on"}
)

# 多通道
switches = device.params.get("switches").copy()
switches[channel]["switch"] = "on"
await api_client.set_device_status(
    device_id,
    {"switches": switches}
)
```

**生命周期**：
```python
async_added_to_hass():
    # 注册 WebSocket 回调
    coordinator.register_device_callback(device_id, callback)

async_will_remove_from_hass():
    # 取消注册回调
    coordinator.unregister_device_callback(device_id)
```

---

## 数据流详解

### 初始化流程

```
1. 用户配置
   ConfigFlow.async_step_user
     ↓
   验证登录凭证
     ↓
   创建 ConfigEntry

2. 集成加载
   __init__.async_setup_entry
     ↓
   创建 API Client
     ↓
   登录获取 Token
     ↓
   创建 WebSocket Client
     ↓
   创建 Coordinator
     ↓
   首次数据获取
     ↓
   建立 WebSocket 连接
     ↓
   加载平台 (switch)

3. 平台设置
   switch.async_setup_entry
     ↓
   遍历所有设备
     ↓
   为每个设备创建实体
     ↓
   注册实体到 HA
```

### 状态更新流程（HTTP 轮询）

```
定时器触发 (每5分钟)
  ↓
Coordinator._async_update_data()
  ↓
API.get_devices()
  ↓
解析设备数据
  ↓
更新 coordinator.data
  ↓
触发 coordinator 更新事件
  ↓
所有实体的 _handle_coordinator_update() 被调用
  ↓
实体调用 async_write_ha_state()
  ↓
前端更新显示
```

### 状态更新流程（WebSocket 推送）

```
eWeLink 服务器推送消息
  ↓
WebSocket._listen() 接收
  ↓
WebSocket._handle_message() 解析
  ↓
找到对应的 device_id 回调
  ↓
执行回调函数
  ↓
更新 coordinator.data[device_id].params
  ↓
调用实体的回调
  ↓
实体调用 async_write_ha_state()
  ↓
前端立即更新
```

### 设备控制流程

```
用户操作 (前端点击开关)
  ↓
Switch.async_turn_on()
  ↓
Switch._async_set_switch_state(True)
  ↓
API.set_device_status()
  ↓
发送 HTTP POST 请求
  ↓
本地立即更新状态 (乐观更新)
  device.params["switch"] = "on"
  async_write_ha_state()
  ↓
eWeLink 服务器处理请求
  ↓
通过 WebSocket 推送确认
  ↓
最终状态一致
```

---

## 错误处理策略

### API 错误

```python
try:
    await api_client.login()
except EWeLinkAuthError:
    # 触发重新认证流程
    raise ConfigEntryAuthFailed
except EWeLinkConnectionError:
    # 暂时不可用，稍后重试
    raise ConfigEntryNotReady
```

### WebSocket 错误

```python
# 连接失败
except (ClientError, TimeoutError):
    _LOGGER.error("WebSocket connection failed")
    # 自动调度重连
    schedule_reconnect()

# 消息处理错误
except Exception:
    _LOGGER.exception("Error handling message")
    # 继续监听，不中断连接
```

### 实体操作错误

```python
try:
    await api_client.set_device_status(...)
except EWeLinkApiError:
    # 标记实体为不可用
    self._attr_available = False
    self.async_write_ha_state()
    # 重新抛出异常让 HA 显示错误
    raise
```

---

## 性能优化

### 1. 数据缓存
- Coordinator 缓存所有设备数据
- 避免重复 API 请求
- 减少网络流量

### 2. 乐观更新
- 用户操作后立即更新本地状态
- 不等待服务器确认
- 提升响应速度

### 3. WebSocket 优先
- 优先使用 WebSocket 推送
- HTTP 轮询作为备用
- 减少 API 调用次数

### 4. 批量操作
- 一次获取所有设备
- 减少 API 请求次数
- 提高效率

---

## 安全考虑

### 1. 凭证存储
- 密码加密存储在 ConfigEntry
- 不在日志中输出敏感信息
- Token 仅在内存中保存

### 2. 通信加密
- HTTPS 用于 API 请求
- WSS 用于 WebSocket 连接
- 所有通信都加密

### 3. 错误信息
- 不暴露内部实现细节
- 用户友好的错误提示
- 详细日志仅在调试模式

---

## 可扩展性

### 添加新设备类型

```python
# 1. 在 const.py 中定义常量
DEVICE_TYPE_LIGHT = "light"

# 2. 创建新平台文件 light.py
class EWeLinkLight(EWeLinkEntity, LightEntity):
    pass

# 3. 在 __init__.py 中添加平台
PLATFORMS = [Platform.SWITCH, Platform.LIGHT]

# 4. 在 switch.py 的 async_setup_entry 中添加逻辑
if device.device_type == DEVICE_TYPE_LIGHT:
    # 跳过，由 light 平台处理
    continue
```

### 添加新 API 方法

```python
# 在 api.py 中添加
async def get_device_history(device_id: str) -> list:
    """Get device history."""
    url = f"{API_BASE_URL}/device/history"
    # 实现逻辑
```

---

## 总结

这个集成采用了现代化的 Home Assistant 集成架构：

✅ **清晰的职责分离**：每个模块各司其职
✅ **高效的数据管理**：Coordinator 模式
✅ **实时性**：WebSocket 推送 + HTTP 轮询
✅ **用户友好**：UI 配置流程
✅ **健壮性**：完善的错误处理和重连机制
✅ **可扩展性**：模块化设计，易于添加新功能

这个架构为后续添加更多设备类型和功能提供了坚实的基础。

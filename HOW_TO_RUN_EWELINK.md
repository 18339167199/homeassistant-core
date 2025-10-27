# 如何运行和测试 eWeLink IoT 集成

## 🎯 运行方式

有两种方式可以运行和测试这个集成：

### 方式 1：运行完整的 Home Assistant（推荐）
### 方式 2：运行测试

---

## 📋 方式 1：运行完整的 Home Assistant

### 步骤 1：启动 Home Assistant

```bash
cd /workspaces/homeassistant-core

# 启动 Home Assistant
python3 -m homeassistant -c ./config
```

或者使用已配置的任务：

```bash
# 在 VS Code 中按 Ctrl+Shift+P
# 输入 "Tasks: Run Task"
# 选择 "Run Home Assistant Core"
```

### 步骤 2：访问 Web 界面

启动后，访问：
```
http://localhost:8123
```

### 步骤 3：完成初始设置

首次启动时需要：
1. 创建管理员账号
2. 设置位置和时区
3. 等待初始化完成

### 步骤 4：添加 eWeLink IoT 集成

1. **进入集成页面**
   - 点击左侧菜单 "设置"
   - 点击 "设备与服务"
   - 点击右下角 "+ 添加集成" 按钮

2. **搜索集成**
   - 在搜索框输入 "ewelink" 或 "ewelink iot"
   - 点击 "eWeLink IoT" 集成

3. **输入登录信息**
   ```
   Email:     你的 eWeLink 邮箱
   Password:  你的 eWeLink 密码
   Region:    cn (中国) 或其他区域
   App ID:    (可选，使用默认值)
   App Secret: (可选，使用默认值)
   ```

4. **等待同步**
   - 集成会自动登录
   - 获取设备列表
   - 建立 WebSocket 连接
   - 创建 switch 实体

5. **查看设备**
   - 返回 "设备与服务" 页面
   - 找到 "eWeLink IoT" 卡片
   - 点击查看同步的设备和实体

### 步骤 5：查看和控制设备

**在概览页面：**
- 所有开关实体会自动显示
- 可以直接点击开关控制

**在开发者工具：**
1. 左侧菜单 → 开发者工具 → 状态
2. 搜索 `switch.` 查看所有开关实体
3. 查看实体的详细状态信息

**示例实体：**
```
switch.device_name_channel_1
switch.device_name_channel_2
switch.device_name_channel_3
```

---

## 🧪 方式 2：运行测试

### 运行所有测试

```bash
cd /workspaces/homeassistant-core

# 运行 ewelink_iot 的所有测试
pytest tests/components/ewelink_iot/ \
  --cov=homeassistant.components.ewelink_iot \
  --cov-report term-missing \
  -v
```

### 运行特定测试

```bash
# 只测试配置流程
pytest tests/components/ewelink_iot/test_config_flow.py -v

# 只测试初始化
pytest tests/components/ewelink_iot/test_init.py -v
```

### 查看测试覆盖率

```bash
pytest tests/components/ewelink_iot/ \
  --cov=homeassistant.components.ewelink_iot \
  --cov-report html

# 在浏览器中打开
# htmlcov/index.html
```

---

## 🔍 查看效果的方法

### 1. 查看日志

**启用调试日志：**

编辑 `config/configuration.yaml`：
```yaml
logger:
  default: info
  logs:
    homeassistant.components.ewelink_iot: debug
```

重启 HA 后，查看日志：
```bash
tail -f config/home-assistant.log
```

**你会看到类似这样的日志：**
```
DEBUG (MainThread) [homeassistant.components.ewelink_iot.api] Successfully logged in to eWeLink
DEBUG (MainThread) [homeassistant.components.ewelink_iot.api] Retrieved 5 devices from eWeLink
INFO (MainThread) [homeassistant.components.ewelink_iot.websocket] Connected to eWeLink WebSocket
DEBUG (MainThread) [homeassistant.components.ewelink_iot.websocket] Sent handshake message
DEBUG (MainThread) [homeassistant.components.ewelink_iot.websocket] Received WebSocket message: {...}
```

### 2. 查看设备信息

**在开发者工具 → 状态：**
```
实体 ID: switch.living_room_channel_1
状态: on
属性:
  friendly_name: Living Room Channel 1
  device_class: switch
  assumed_state: false
```

### 3. 实时测试 WebSocket 更新

1. **在 HA 中打开开关**
2. **在 eWeLink App 中关闭同一个开关**
3. **观察 HA 前端是否立即更新**（应该在 1 秒内更新）

### 4. 查看 WebSocket 连接状态

在日志中搜索：
```bash
grep -i "websocket" config/home-assistant.log
```

应该看到：
```
INFO ... Connected to eWeLink WebSocket
DEBUG ... Sent handshake message
DEBUG ... Received WebSocket message
```

---

## 🎮 测试场景

### 场景 1：单通道开关

**模拟设备数据：**
```python
{
    "deviceid": "1000abcd",
    "name": "客厅灯",
    "params": {"switch": "on"}
}
```

**预期结果：**
- 创建实体：`switch.living_room_light`
- 状态：`on`
- 可以点击控制

### 场景 2：三通道开关

**模拟设备数据：**
```python
{
    "deviceid": "1000efgh",
    "name": "客厅开关",
    "params": {
        "switches": [
            {"switch": "on"},
            {"switch": "off"},
            {"switch": "on"}
        ]
    }
}
```

**预期结果：**
- 创建 3 个实体：
  - `switch.living_room_switch_channel_1` (on)
  - `switch.living_room_switch_channel_2` (off)
  - `switch.living_room_switch_channel_3` (on)

### 场景 3：实时状态更新

1. 在 HA 中打开开关
2. WebSocket 应该接收到确认消息
3. 在 eWeLink App 中改变状态
4. HA 应该立即更新（< 1秒）

---

## 🐛 调试技巧

### 1. 检查 API 连接

在 Python 环境中手动测试：

```python
import asyncio
import aiohttp
from homeassistant.components.ewelink_iot.api import EWeLinkApiClient

async def test_api():
    session = aiohttp.ClientSession()
    client = EWeLinkApiClient(
        session=session,
        email="your_email@example.com",
        password="your_password",
        app_id="4s1FXKC9FaGfoqXhmXSJneb3qcm1gOak",
        app_secret="oKvCM06gvwkRbfetd6qWRrbC3rFrbIpV",
        region="cn"
    )

    try:
        # 测试登录
        await client.login()
        print(f"✅ 登录成功！Token: {client.access_token[:20]}...")

        # 获取设备
        devices = await client.get_devices()
        print(f"✅ 获取到 {len(devices)} 个设备")

        for device in devices:
            print(f"  - {device.name} ({device.device_id})")
            print(f"    在线: {device.online}")
            print(f"    参数: {device.params}")
    finally:
        await session.close()

# 运行测试
asyncio.run(test_api())
```

### 2. 检查 WebSocket 连接

```python
import asyncio
import aiohttp
from homeassistant.components.ewelink_iot.websocket import EWeLinkWebSocketClient

async def test_websocket():
    session = aiohttp.ClientSession()

    # 先登录获取 token
    # ... (使用上面的 API 测试代码)

    ws_client = EWeLinkWebSocketClient(
        session=session,
        api_key="your_api_key",
        access_token="your_access_token",
        user_id="your_user_id"
    )

    try:
        await ws_client.connect()
        print("✅ WebSocket 连接成功")

        # 等待接收消息
        await asyncio.sleep(30)
    finally:
        await ws_client.disconnect()
        await session.close()

asyncio.run(test_websocket())
```

### 3. 查看实体注册

```bash
# 在 HA 运行时执行
grep -r "ewelink_iot" config/.storage/core.entity_registry
```

### 4. 检查配置入口

```bash
# 查看配置入口
grep -r "ewelink_iot" config/.storage/core.config_entries
```

---

## 📊 预期的运行流程

### 启动流程（约 5-10 秒）

```
1. [0s] Home Assistant 启动
2. [1s] 加载 ewelink_iot 集成
3. [2s] 创建 API 客户端
4. [3s] 登录 eWeLink (API 请求)
5. [4s] 获取设备列表 (API 请求)
6. [5s] 建立 WebSocket 连接
7. [6s] 创建 switch 实体
8. [7s] 实体就绪，可以控制
```

### 控制流程（< 1 秒）

```
1. [0ms] 用户点击开关
2. [50ms] 发送 API 请求
3. [100ms] 本地状态更新（乐观更新）
4. [200ms] eWeLink 服务器处理
5. [300ms] WebSocket 推送确认
6. [350ms] 最终状态同步
```

### 状态更新流程

**WebSocket 推送（< 1 秒）：**
```
设备状态改变
  ↓ (100ms)
WebSocket 推送
  ↓ (50ms)
解析消息
  ↓ (10ms)
更新协调器
  ↓ (10ms)
通知实体
  ↓ (10ms)
前端更新
```

**HTTP 轮询（每 5 分钟）：**
```
定时器触发
  ↓
API 请求
  ↓ (500ms)
获取所有设备
  ↓
更新协调器
  ↓
批量更新实体
```

---

## 🎯 成功指标

运行成功的标志：

✅ **无错误日志** - 没有红色的 ERROR 消息
✅ **设备同步** - 能看到所有 eWeLink 设备
✅ **实体创建** - 每个设备创建了对应的实体
✅ **状态正确** - 实体状态与实际设备一致
✅ **可以控制** - 点击开关能正常工作
✅ **实时更新** - eWeLink App 改变状态，HA 立即更新
✅ **WebSocket 连接** - 日志显示 "Connected to eWeLink WebSocket"

---

## ⚠️ 常见问题

### 问题 1：找不到集成

**原因：** 集成未正确加载

**解决：**
```bash
# 重启 Home Assistant
# 或检查日志中的错误信息
```

### 问题 2：登录失败

**可能原因：**
- 邮箱或密码错误
- 区域选择错误
- 网络连接问题

**检查：**
```bash
# 查看日志
grep -i "login" config/home-assistant.log
grep -i "auth" config/home-assistant.log
```

### 问题 3：没有设备

**可能原因：**
- eWeLink 账号下没有设备
- API 请求失败
- 设备类型不支持

**检查：**
```bash
# 查看设备获取日志
grep -i "devices" config/home-assistant.log
```

### 问题 4：WebSocket 断开

**正常现象：**
- 网络波动时会自动重连
- 10 秒后自动尝试重连

**检查：**
```bash
# 查看 WebSocket 状态
grep -i "websocket" config/home-assistant.log | tail -20
```

---

## 📱 推荐测试流程

### 完整测试流程（15 分钟）

1. **启动 HA**（2 分钟）
   ```bash
   python3 -m homeassistant -c ./config
   ```

2. **添加集成**（2 分钟）
   - 访问 http://localhost:8123
   - 添加 eWeLink IoT 集成
   - 输入凭证

3. **查看设备**（1 分钟）
   - 检查设备列表
   - 确认实体创建

4. **测试控制**（2 分钟）
   - 打开/关闭开关
   - 观察响应速度

5. **测试实时更新**（3 分钟）
   - 在 eWeLink App 中改变状态
   - 观察 HA 是否立即更新

6. **查看日志**（2 分钟）
   - 检查有无错误
   - 确认 WebSocket 连接

7. **测试重启**（3 分钟）
   - 重启 HA
   - 确认集成正常加载
   - 确认设备状态恢复

---

## 🎉 成功示例

如果一切正常，你应该看到：

**前端界面：**
```
概览
├── 客厅开关 Channel 1  [开启]
├── 客厅开关 Channel 2  [关闭]
└── 客厅开关 Channel 3  [开启]
```

**开发者工具 → 状态：**
```
switch.living_room_switch_channel_1
  状态: on
  属性:
    friendly_name: Living Room Switch Channel 1
    device_class: switch

switch.living_room_switch_channel_2
  状态: off
  属性:
    friendly_name: Living Room Switch Channel 2
    device_class: switch
```

**日志输出：**
```
INFO ... Setup of domain ewelink_iot took 3.2 seconds
DEBUG ... Successfully logged in to eWeLink
DEBUG ... Retrieved 3 devices from eWeLink
INFO ... Connected to eWeLink WebSocket
DEBUG ... Setting up switch platform for ewelink_iot
```

---

## 🚀 开始运行吧！

现在你可以：

1. **运行 Home Assistant**
   ```bash
   python3 -m homeassistant -c ./config
   ```

2. **打开浏览器访问**
   ```
   http://localhost:8123
   ```

3. **添加 eWeLink IoT 集成并查看效果！**

祝你测试顺利！🎉

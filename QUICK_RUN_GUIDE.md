# 🚀 eWeLink IoT 集成 - 快速运行指南

## 方法概览

有 **3 种方法** 查看集成效果：

### 方法 1：运行 Home Assistant（完整功能）⭐ 推荐
### 方法 2：运行演示脚本（快速测试）
### 方法 3：运行单元测试（验证功能）

---

## 📱 方法 1：运行 Home Assistant（完整功能）

### 步骤 1：启动 Home Assistant

```bash
cd /workspaces/homeassistant-core
python3 -m homeassistant -c ./config
```

等待启动完成（约 30-60 秒），你会看到：
```
INFO (MainThread) [homeassistant.core] Starting Home Assistant
INFO (MainThread) [homeassistant.bootstrap] Home Assistant initialized in XXs
```

### 步骤 2：访问 Web 界面

在浏览器中打开：
```
http://localhost:8123
```

### 步骤 3：添加 eWeLink IoT 集成

1. **首次访问**：创建管理员账号
2. **进入集成页面**：
   - 点击左侧菜单 "设置"
   - 点击 "设备与服务"
   - 点击右下角 "+ 添加集成"

3. **搜索集成**：
   - 搜索框输入 "ewelink"
   - 点击 "eWeLink IoT"

4. **输入登录信息**：
   ```
   Email:     你的 eWeLink 邮箱
   Password:  你的密码
   Region:    cn (中国)
   ```

5. **查看设备**：
   - 配置完成后自动跳转
   - 可以看到同步的设备和实体

### 步骤 4：查看效果

**在概览页面：**
- 所有开关实体会自动显示
- 可以点击控制

**在开发者工具：**
- 左侧菜单 → 开发者工具 → 状态
- 搜索 `switch.` 查看所有实体

**查看日志：**
```bash
# 实时查看日志
tail -f config/home-assistant.log

# 搜索 ewelink 相关日志
grep -i "ewelink" config/home-assistant.log
```

---

## 🎮 方法 2：运行演示脚本（快速测试）

如果你有真实的 eWeLink 账号，可以运行演示脚本：

```bash
cd /workspaces/homeassistant-core
python3 demo_ewelink.py
```

### 演示脚本功能：

1. **API 客户端测试**
   - 登录验证
   - 获取设备列表
   - 显示设备详情

2. **WebSocket 连接测试**
   - 建立长连接
   - 监听实时更新

3. **查看集成结构**
   - 文件组织
   - 数据流程

### 使用示例：

```
请选择演示内容：

  1. API 客户端演示（需要真实账号）
  2. 查看集成文件结构
  3. 查看数据流程
  4. 查看模拟数据演示
  0. 退出

请选择 (0-4): 1

请输入 eWeLink 邮箱: your_email@example.com
请输入 eWeLink 密码: ******
请输入区域 (cn/as/us/eu, 默认 cn): cn

🔐 正在登录 eWeLink (cn)...
✅ 登录成功！
   User ID: abc123def
   Token: eyJhbGciOiJIUzI1NiIsInR5cCI...

📱 正在获取设备列表...
✅ 获取到 3 个设备

   1. 客厅开关
      ID: 1000abcdef
      型号: POWR316D
      在线: 🟢 是
      参数: {'switches': [...]}

      ➡️ 多通道开关 (3 个通道):
         通道 1: 🟢 开启
         通道 2: 🔴 关闭
         通道 3: 🟢 开启
```

---

## 🧪 方法 3：运行单元测试（验证功能）

### 运行所有测试：

```bash
cd /workspaces/homeassistant-core

pytest tests/components/ewelink_iot/ -v
```

### 运行特定测试：

```bash
# 测试配置流程
pytest tests/components/ewelink_iot/test_config_flow.py -v

# 测试初始化
pytest tests/components/ewelink_iot/test_init.py -v
```

### 查看测试覆盖率：

```bash
pytest tests/components/ewelink_iot/ \
  --cov=homeassistant.components.ewelink_iot \
  --cov-report term-missing
```

### 预期输出：

```
tests/components/ewelink_iot/test_config_flow.py::test_user_flow_success PASSED
tests/components/ewelink_iot/test_config_flow.py::test_user_flow_invalid_auth PASSED
tests/components/ewelink_iot/test_config_flow.py::test_user_flow_cannot_connect PASSED
tests/components/ewelink_iot/test_config_flow.py::test_user_flow_already_configured PASSED
tests/components/ewelink_iot/test_init.py::test_setup_unload PASSED

====== 5 passed in 2.34s ======
```

---

## 📊 查看效果的具体内容

### 1. 设备同步效果

**eWeLink 平台设备 → Home Assistant 实体：**

单通道开关：
```
eWeLink: "客厅灯" (switch: on)
   ↓
HA:      switch.living_room_light (开启)
```

三通道开关：
```
eWeLink: "客厅开关" (switches: [on, off, on])
   ↓
HA:      switch.living_room_switch_channel_1 (开启)
         switch.living_room_switch_channel_2 (关闭)
         switch.living_room_switch_channel_3 (开启)
```

### 2. 实时更新效果

**测试步骤：**
1. 在 HA 中打开一个开关
2. 在 eWeLink App 中关闭同一个开关
3. 观察 HA 前端是否在 1 秒内更新

**预期效果：**
- ⚡ WebSocket 推送：< 1 秒更新
- 🔄 HTTP 轮询：最多 5 分钟更新

### 3. 控制效果

**操作流程：**
```
用户点击开关
  ↓ (50ms)
HA 发送 API 请求
  ↓ (50ms)
前端立即更新（乐观更新）
  ↓ (200ms)
eWeLink 处理请求
  ↓ (100ms)
WebSocket 推送确认
  ↓
最终状态一致
```

**总响应时间：** < 500ms

---

## 🎯 验证成功的标志

### ✅ 集成加载成功

**日志中应该看到：**
```
INFO ... Setup of domain ewelink_iot took 3.2 seconds
DEBUG ... Successfully logged in to eWeLink
DEBUG ... Retrieved 5 devices from eWeLink
INFO ... Connected to eWeLink WebSocket
```

### ✅ 设备同步成功

**在 HA 设备页面应该看到：**
- eWeLink IoT 卡片
- 显示设备数量
- 可以点击查看详情

### ✅ 实体创建成功

**在状态页面应该看到：**
```
switch.device_name_channel_1
  状态: on
  属性:
    friendly_name: Device Name Channel 1
```

### ✅ WebSocket 连接成功

**日志中应该看到：**
```
INFO ... Connected to eWeLink WebSocket
DEBUG ... Sent handshake message
```

**没有错误：**
```
# 不应该看到这些
ERROR ... WebSocket connection failed
ERROR ... Failed to login
ERROR ... Authentication failed
```

---

## 🔍 调试技巧

### 查看详细日志

编辑 `config/configuration.yaml`：
```yaml
logger:
  default: info
  logs:
    homeassistant.components.ewelink_iot: debug
    homeassistant.components.ewelink_iot.api: debug
    homeassistant.components.ewelink_iot.websocket: debug
```

### 实时监控日志

```bash
# 实时查看所有日志
tail -f config/home-assistant.log

# 只看 ewelink 相关
tail -f config/home-assistant.log | grep -i ewelink

# 只看错误
tail -f config/home-assistant.log | grep ERROR
```

### 检查集成状态

```bash
# 检查配置入口
cat config/.storage/core.config_entries | jq '.data.entries[] | select(.domain=="ewelink_iot")'

# 检查实体注册
cat config/.storage/core.entity_registry | jq '.data.entities[] | select(.platform=="ewelink_iot")'
```

---

## ⚡ 快速测试命令

### 一键启动并查看日志

```bash
# 启动 HA 并实时查看日志
cd /workspaces/homeassistant-core
python3 -m homeassistant -c ./config 2>&1 | tee ha.log | grep -i ewelink
```

### 一键运行所有测试

```bash
cd /workspaces/homeassistant-core
pytest tests/components/ewelink_iot/ --tb=short
```

### 一键验证集成

```bash
cd /workspaces/homeassistant-core
python3 -m script.hassfest --integration-path homeassistant/components/ewelink_iot
```

---

## 📸 预期效果截图说明

### Web 界面效果

**添加集成页面：**
- 搜索框显示 "ewelink iot"
- 可以看到 "eWeLink IoT" 集成卡片
- 点击后显示登录表单

**配置表单：**
- Email 输入框
- Password 输入框
- Region 下拉框（cn, as, us, eu）
- App ID（可选）
- App Secret（可选）

**设备页面：**
- eWeLink IoT 卡片
- 显示设备数量：X 台设备
- 显示实体数量：Y 个实体
- 可以点击查看详情

**概览页面：**
- 自动显示所有 switch 实体
- 每个开关有开/关按钮
- 点击立即切换状态

---

## 📝 总结

**最简单的方法：**
```bash
# 1. 启动 HA
python3 -m homeassistant -c ./config

# 2. 打开浏览器
http://localhost:8123

# 3. 添加集成，输入账号

# 4. 查看设备和控制
```

**最快的验证方法：**
```bash
# 运行测试
pytest tests/components/ewelink_iot/ -v
```

**如果没有真实设备：**
```bash
# 查看模拟演示
python3 demo_ewelink.py
# 选择 4 - 查看模拟数据演示
```

---

## 🎉 开始体验吧！

选择适合你的方法，立即查看 eWeLink IoT 集成的效果！

有任何问题请查看：
- **详细文档**: HOW_TO_RUN_EWELINK.md
- **快速指南**: EWELINK_IOT_QUICKSTART.md
- **架构说明**: EWELINK_IOT_ARCHITECTURE.md

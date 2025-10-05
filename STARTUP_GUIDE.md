# 🚀 PocketSpeak 启动指南

## 📋 环境检查

### ✅ 已安装环境
- **Python**: 3.11.9 ✅
- **Flutter**: 3.35.3 ✅
- **操作系统**: macOS (Darwin 24.4.0) ✅

---

## 🔧 后端启动步骤

### 1️⃣ 安装后端依赖

```bash
cd /Users/good/Desktop/PocketSpeak/backend

# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2️⃣ 检查环境配置

后端配置文件位于 `backend/.env`，当前配置：

```env
# 小智AI服务配置
XIAOZHI_BASE_URL=https://xiaozhi.me
XIAOZHI_OTA_URL=https://api.tenclass.net/xiaozhi/ota/
XIAOZHI_WS_URL=wss://api.xiaozhi.com/v1/ws
XIAOZHI_API_URL=https://api.xiaozhi.com

# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=true

# 日志配置
LOG_LEVEL=info
LOG_FILE=logs/pocketspeak.log
```

### 3️⃣ 启动后端服务

```bash
cd /Users/good/Desktop/PocketSpeak/backend

# 方式1: 直接运行（推荐用于测试）
python main.py

# 方式2: 使用uvicorn命令行
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4️⃣ 验证后端启动成功

启动成功后，你会看到类似输出：
```
🚀 PocketSpeak Backend 正在启动...
📱 应用名称: PocketSpeak Backend
🔢 版本: 1.0.0
🌟 启动 PocketSpeak Backend
🔧 调试模式: 开启
🌐 服务地址: http://0.0.0.0:8000
📚 API文档: http://0.0.0.0:8000/docs
```

**访问测试地址**:
- 根路径: http://localhost:8000/
- 健康检查: http://localhost:8000/health
- API文档（Swagger UI）: http://localhost:8000/docs
- API文档（ReDoc）: http://localhost:8000/redoc

---

## 📱 前端启动步骤

### 1️⃣ 安装Flutter依赖

```bash
cd /Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app

# 安装依赖
flutter pub get
```

### 2️⃣ 配置后端API地址

检查前端配置文件，确保API地址指向后端服务：
```bash
# 查看API服务配置
cat lib/services/api_service.dart
```

API地址配置说明：
- **iOS模拟器**: `http://localhost:8000` ✅ (推荐)
- **Android模拟器**: `http://10.0.2.2:8000`
- **真机**: `http://你的电脑IP:8000` (例如: `http://192.168.1.100:8000`)

### 3️⃣ 启动iOS模拟器（推荐）

#### 方法1: 使用已启动的模拟器（最快）

当前已有运行中的模拟器：
- **iPhone 14 x86_64** (iOS 18.6) ✅ 已启动

直接运行Flutter应用：
```bash
cd /Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app

# 启动到iOS模拟器
flutter run
```

#### 方法2: 启动指定的iOS模拟器

```bash
# 查看所有可用的iOS模拟器
xcrun simctl list devices available | grep iPhone

# 启动iPhone 15 Pro模拟器（推荐，iOS 17）
open -a Simulator --args -CurrentDeviceUDID C92986D5-0DF7-4E36-B03A-F29A18E00D99

# 或启动iPhone 16 Pro模拟器（最新，iOS 18.6）
open -a Simulator --args -CurrentDeviceUDID DEAB2B51-2FFD-4B09-A7B6-9DDA3DE813CC

# 等待模拟器启动后，运行Flutter应用
cd /Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app
flutter run
```

#### 方法3: 使用Flutter命令启动模拟器

```bash
cd /Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app

# 查看可用设备
flutter devices

# 启动到iOS模拟器（会自动选择或打开模拟器）
flutter run -d ios

# 或指定具体的iOS模拟器设备ID
flutter run -d 527BFB9E-281A-42FA-9C93-39ED428A9D1E
```

### 4️⃣ 其他设备启动方式

```bash
# Chrome浏览器（快速测试UI）
flutter run -d chrome

# macOS桌面应用
flutter run -d macos

# Android模拟器
flutter run -d android
```

---

## 🧪 测试已完成功能

### ✅ 后端API测试

#### 方法1: 浏览器访问 Swagger UI

1. 启动后端服务
2. 打开浏览器访问: http://localhost:8000/docs
3. 测试以下端点:

**设备管理API** (`/api/device/`):
- `GET /api/device/info` - 获取设备信息
- `GET /api/device/status` - 获取设备状态
- `POST /api/device/activate/start` - 开始设备激活
- `GET /api/device/activate/status` - 查询激活状态
- `POST /api/device/activate/verify` - 验证绑定状态

**WebSocket管理API** (`/api/ws/`):
- `POST /api/ws/start` - 启动WebSocket连接
- `GET /api/ws/status` - 查询WebSocket状态
- `POST /api/ws/stop` - 停止WebSocket连接
- `POST /api/ws/reconnect` - 重新连接WebSocket
- `GET /api/ws/health` - WebSocket健康检查
- `GET /api/ws/stats` - WebSocket统计信息

#### 方法2: 使用测试脚本

```bash
cd /Users/good/Desktop/PocketSpeak/backend

# 运行WebSocket API测试
python test_websocket_api.py
```

#### 方法3: 使用curl命令

```bash
# 健康检查
curl http://localhost:8000/health

# 获取设备信息
curl http://localhost:8000/api/device/info

# 获取设备状态
curl http://localhost:8000/api/device/status

# 开始设备激活
curl -X POST http://localhost:8000/api/device/activate/start

# 查询WebSocket状态
curl http://localhost:8000/api/ws/status
```

### ✅ 前端功能测试

启动前端后，可以测试：

1. **设备绑定流程**:
   - 查看设备信息显示
   - 获取验证码并展示二维码
   - 验证码输入界面

2. **设备激活流程**:
   - 前往 https://xiaozhi.me 绑定设备
   - 应用内轮询激活状态
   - 激活成功提示

---

## 📊 功能完成度检查清单

### ✅ 后端核心功能

- [x] **设备生成与管理** (device_generator.py)
  - 设备信息生成
  - 设备持久化存储

- [x] **设备激活流程** (device_lifecycle.py, pocketspeak_activator.py)
  - 验证码获取
  - 绑定状态轮询
  - 激活状态管理

- [x] **WebSocket连接管理** (ws_client.py, ws_lifecycle.py)
  - 连接到小智AI服务器
  - 设备身份认证
  - 心跳机制
  - 自动重连

- [x] **语音通信模块** (voice_chat/)
  - 语音录制与OPUS编码 (speech_recorder.py)
  - AI响应解析 (ai_response_parser.py)
  - TTS语音播放 (tts_player.py)

- [x] **FastAPI路由系统**
  - 设备管理路由 (routers/device.py)
  - WebSocket管理路由 (routers/ws_lifecycle.py)

### ⚠️ 待确认功能

- [ ] **文字通信模块** (text_chat/text_client.py)
  - 状态需要检查

- [ ] **端到端语音交互**
  - WebSocket + 语音模块集成
  - 完整通信流程测试

### ✅ 前端核心功能

- [x] **设备绑定页面** (binding_page.dart)
  - UI界面已实现
  - API调用集成

- [ ] **聊天交互页面**
  - 待确认实现状态

---

## 🔍 常见问题排查

### ❌ 后端启动失败

**问题1**: `ModuleNotFoundError: No module named 'xxx'`
```bash
# 解决方案: 重新安装依赖
pip install -r backend/requirements.txt
```

**问题2**: `Address already in use` (端口占用)
```bash
# 查找占用8000端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或修改.env文件中的PORT配置
```

### ❌ 前端启动失败

**问题1**: `Flutter SDK not found`
```bash
# 检查Flutter安装
flutter doctor

# 如有问题，按提示修复
```

**问题2**: `Error: Cannot run with sound null safety`
```bash
# 清理并重新获取依赖
flutter clean
flutter pub get
```

**问题3**: 无法连接到后端
```bash
# 检查后端是否启动
curl http://localhost:8000/health

# 检查防火墙设置
# 检查API地址配置是否正确
```

---

## 📝 测试建议流程

### 🎯 推荐测试顺序

1. **启动后端服务**
   ```bash
   cd backend
   python main.py
   ```

2. **测试后端API** (浏览器打开 http://localhost:8000/docs)
   - ✅ 健康检查
   - ✅ 设备信息获取
   - ✅ 设备激活开始
   - ✅ WebSocket状态查询

3. **启动前端应用到iOS模拟器**
   ```bash
   cd frontend/pocketspeak_app
   flutter run
   ```
   或启动到Chrome:
   ```bash
   flutter run -d chrome
   ```

4. **测试设备绑定流程**
   - 查看设备信息
   - 获取验证码
   - 前往小智官网绑定
   - 验证激活状态

5. **测试WebSocket连接**
   - 通过API或前端启动WebSocket
   - 查看连接状态
   - 验证心跳机制

---

## 📚 相关文档

- **API文档**: http://localhost:8000/docs (启动后端后访问)
- **项目蓝图**: backend_claude_memory/references/project_blueprint.md
- **开发路线图**: backend_claude_memory/specs/development_roadmap.md
- **PRD文档**: backend_claude_memory/specs/pocketspeak_PRD_V1.0.md
- **任务列表**: backend_claude_memory/specs/pocketspeak_v1_task_list.md
- **工作日志**: claude_workspace/ 目录下的各个日志文件

---

## 💡 下一步建议

根据当前完成度，建议按以下顺序进行测试和开发：

1. ✅ **测试后端基础功能** - 验证所有API端点正常工作
2. ✅ **测试设备激活流程** - 完整走通设备绑定和激活
3. ✅ **测试WebSocket连接** - 验证与小智AI服务器的通信
4. ⏭️ **集成语音通信模块** - 将语音模块与WebSocket连接整合
5. ⏭️ **前端完整测试** - 测试前端所有页面和功能
6. ⏭️ **端到端测试** - 完整的语音交互流程测试

---

**生成时间**: 2025-10-01
**文档版本**: 1.0.0
**项目版本**: PocketSpeak V1.0

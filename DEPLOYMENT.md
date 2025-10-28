# PocketSpeak 部署指南

## 📋 目录

1. [后端部署](#后端部署)
2. [前端部署](#前端部署)
3. [API 链接配置](#api-链接配置)
4. [macOS 特殊配置](#macos-特殊配置)

---

## 🚀 后端部署

### 1. 系统要求

- Python 3.11+
- macOS (Apple Silicon) 或 Linux
- Homebrew (macOS) 或 apt (Linux)

### 2. 安装系统依赖

#### macOS:
```bash
# 安装 Opus 音频库
brew install opus

# 验证安装
ls /opt/homebrew/lib/libopus.dylib
```

#### Linux:
```bash
# 安装 Opus 音频库
sudo apt update
sudo apt install -y libopus-dev libopus0

# 安装虚拟音频驱动（服务器环境需要）
sudo apt install -y pulseaudio pulseaudio-utils alsa-utils
sudo modprobe snd-dummy
echo "snd-dummy" | sudo tee -a /etc/modules
```

### 3. 创建 Python 虚拟环境

```bash
cd PocketSpeak/backend
python3 -m venv venv
source venv/bin/activate
```

### 4. 安装 Python 依赖

```bash
# 安装所有依赖
pip install --upgrade pip
pip install \
    numpy soundfile sounddevice pyaudio librosa \
    opuslib PyYAML \
    colorlog webrtcvad \
    email-validator \
    PyJWT httpx bcrypt passlib python-jose \
    paho-mqtt uvloop \
    cryptography cffi \
    fastapi uvicorn pydantic websockets aiohttp requests python-multipart
```

### 5. 修复 macOS Opus 库加载问题（仅 macOS 需要）

编辑文件：`venv/lib/python3.11/site-packages/opuslib/api/__init__.py`

在第 18 行添加以下代码（替换原有的库加载逻辑）：

```python
# 🔥 硬编码 Homebrew Opus 路径以解决 macOS 问题
lib_location = '/opt/homebrew/lib/libopus.dylib'

if not os.path.exists(lib_location):
    lib_location = find_library('opus')
    if lib_location is None:
        raise Exception(
            'Could not find Opus library. Make sure it is installed.')
```

### 6. 配置后端环境

确保 `setup_paths.py` 正确配置（已包含在仓库中）。

### 7. 启动后端服务

```bash
# 方式 1: 使用启动脚本（推荐）
./start_server.sh

# 方式 2: 直接启动
source venv/bin/activate
export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"
python main.py
```

### 8. 验证后端运行

```bash
# 健康检查
curl http://localhost:8000/health

# 应该返回
# {"status":"healthy","version":"1.0"}
```

---

## 📱 前端部署

### 1. 系统要求

- Flutter SDK 3.24.0+
- Xcode 15+ (iOS 开发)
- CocoaPods (iOS 依赖管理)

### 2. 安装 Flutter 依赖

```bash
cd PocketSpeak/frontend/pocketspeak_app
flutter pub get
```

### 3. iOS 特定配置

```bash
# 安装 iOS 依赖
cd ios
pod install
cd ..
```

### 4. 运行应用

```bash
# iOS 模拟器
flutter run

# iOS 真机
flutter run -d <device-id>
```

---

## 🔗 API 链接配置

### ⚠️ 重要：根据部署环境修改 API 链接

默认情况下，前端代码中的 API 链接设置为本地开发环境。**在不同环境下需要修改以下文件：**

### 需要修改的文件（共 7 个）

#### 1. `lib/services/api_service.dart`
```dart
// 第 5-7 行
static const String baseUrl = 'http://127.0.0.1:8000';  // 👈 修改这里
```

**修改为：**
- **本地开发（模拟器）**: `http://127.0.0.1:8000`
- **iOS 真机测试**: `http://你的Mac的IP:8000` (例如 `http://192.168.100.148:8000`)
- **生产环境**: `http://你的服务器IP:8000` (例如 `http://47.128.225.10:8000`)

#### 2. `lib/services/auth_service.dart`
```dart
// 第 17-18 行
static const String baseUrl = 'http://127.0.0.1:8000';  // 👈 修改这里
```

#### 3. `lib/services/user_service.dart`
```dart
// 第 17-18 行
static const String _baseUrl = 'http://127.0.0.1:8000';  // 👈 修改这里
```

#### 4. `lib/services/word_service.dart`
```dart
// 第 11-12 行
static const String baseUrl = 'http://localhost:8000';  // 👈 修改这里
```

#### 5. `lib/services/voice_service.dart`
```dart
// 第 10-11 行
static const String baseUrl = 'http://localhost:8000';  // 👈 修改这里
static const String wsUrl = 'ws://localhost:8000/api/voice/ws';  // 👈 修改这里（WebSocket）
```

#### 6. `lib/services/speech_eval_service.dart`
```dart
// 第 10-11 行
static const String baseUrl = 'http://localhost:8000';  // 👈 修改这里
```

#### 7. `lib/widgets/word_popup_sheet.dart`
```dart
// 第 398 行
: '${WordService.baseUrl}$audioUrl';  // 👈 这个会自动使用 WordService.baseUrl，无需修改
```

### 快速查找替换方法

使用文本编辑器全局搜索并替换：

```
查找：http://127.0.0.1:8000
替换为：http://你的服务器IP:8000

查找：http://localhost:8000
替换为：http://你的服务器IP:8000

查找：ws://localhost:8000
替换为：ws://你的服务器IP:8000
```

### 获取 Mac 本地 IP（用于真机测试）

```bash
# macOS
ifconfig | grep "inet " | grep -v 127.0.0.1

# 或者
ipconfig getifaddr en0
```

---

## 🍎 macOS 特殊配置

### Opus 库路径问题

macOS 的 System Integrity Protection (SIP) 会阻止 `DYLD_LIBRARY_PATH` 在某些情况下生效，因此需要：

1. **硬编码 Homebrew 路径**（已在步骤 5 中完成）
2. **启动时设置环境变量**（`start_server.sh` 已包含）

### 验证 Opus 库加载

```bash
# 检查 Homebrew Opus 安装
ls /opt/homebrew/lib/libopus.dylib

# 如果不存在，重新安装
brew reinstall opus
```

---

## 🧪 测试部署

### 后端测试

```bash
# 1. 健康检查
curl http://localhost:8000/health

# 2. 设备信息
curl http://localhost:8000/api/device/info

# 3. 单词查询
curl "http://localhost:8000/api/words/lookup?word=hello"
```

### 前端测试

1. 启动后端服务
2. 确保修改了正确的 API 链接
3. 运行 Flutter 应用
4. 测试登录功能
5. 测试语音对话功能
6. 测试单词查询和发音功能

---

## 📝 注意事项

1. **API 链接配置**：这是最重要的步骤，根据部署环境修改所有 7 个文件中的 API 链接
2. **防火墙配置**：确保服务器防火墙允许 8000 端口访问
3. **iOS 真机测试**：确保 iPhone 和 Mac 在同一 WiFi 网络下
4. **macOS Opus 库**：必须修复 opuslib 的库加载路径
5. **Python 路径**：setup_paths.py 确保 py-xiaozhi 库路径正确

---

## 🆘 故障排查

### 后端启动失败

1. 检查虚拟环境是否激活
2. 检查所有依赖是否安装完整
3. 检查 Opus 库是否正确加载
4. 查看日志：`tail -f backend/server.log`

### 前端连接失败

1. 检查后端是否正在运行
2. 检查 API 链接是否正确配置
3. 检查防火墙设置
4. 对于真机测试，验证 Mac IP 地址是否正确

### 单词发音播放失败

1. 确认 `word_popup_sheet.dart` 使用正确的 baseUrl
2. 确认后端 TTS 接口正常工作
3. 检查网络连接

---

## 📞 联系方式

如有问题，请参考项目文档或联系开发团队。

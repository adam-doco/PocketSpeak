# 🍎 PocketSpeak iOS模拟器快速启动指南

## ⚡️ 快速启动（最简步骤）

### 终端1: 启动后端服务

```bash
cd /Users/good/Desktop/PocketSpeak/backend
./start_server.sh
```

✅ 看到 "Uvicorn running on http://0.0.0.0:8000" 表示成功

**或者手动设置环境变量启动**:
```bash
cd /Users/good/Desktop/PocketSpeak/backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)/libs/py_xiaozhi"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**⚠️ 注意**: 不要使用 `python main.py` 启动，会导致路径配置丢失！

---

### 终端2: 启动Flutter到iOS模拟器

```bash
cd /Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app
flutter run
```

✅ 应用会自动部署到已运行的 **iPhone 14 x86_64** 模拟器

---

## 📱 当前可用的iOS模拟器

### ✅ 已启动的模拟器（推荐使用）
- **iPhone 14 x86_64** (iOS 18.6) - 当前运行中 ✅

### 📋 其他可用模拟器（iOS 17.0）
- iPhone 15 Pro
- iPhone 15 Pro Max
- iPhone 15
- iPhone 15 Plus
- iPhone SE (3rd generation)

### 📋 最新模拟器（iOS 18.6）
- iPhone 16 Pro
- iPhone 16 Pro Max
- iPhone 16e
- iPhone 16
- iPhone 16 Plus

---

## 🔧 启动指定模拟器

### 启动iPhone 15 Pro（iOS 17.0）

```bash
# 打开模拟器
open -a Simulator --args -CurrentDeviceUDID C92986D5-0DF7-4E36-B03A-F29A18E00D99

# 等待模拟器完全启动后，运行Flutter
cd /Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app
flutter run
```

### 启动iPhone 16 Pro（iOS 18.6 - 最新）

```bash
# 打开模拟器
open -a Simulator --args -CurrentDeviceUDID DEAB2B51-2FFD-4B09-A7B6-9DDA3DE813CC

# 等待模拟器完全启动后，运行Flutter
cd /Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app
flutter run
```

---

## 🧪 测试功能

### 1️⃣ 验证后端运行

浏览器打开: http://localhost:8000/docs

测试端点：
- `GET /health` - 健康检查
- `GET /api/device/info` - 设备信息
- `GET /api/device/status` - 设备状态

### 2️⃣ 在iOS模拟器中测试

启动应用后，你可以测试：

✅ **设备绑定页面**:
- 查看设备信息展示
- 点击"开始激活"按钮
- 查看验证码显示
- 扫描二维码或手动输入验证码

✅ **激活流程**:
1. 在模拟器中获取验证码
2. 在浏览器访问 https://xiaozhi.me
3. 输入验证码完成绑定
4. 返回应用查看激活状态

---

## 🔍 常见问题

### ❌ 问题1: 后端启动失败 "Error loading ASGI app"

**症状**: 运行 `python main.py` 时报错 "Attribute 'app' not found in module 'main'"

**原因**: 使用 `python main.py` 启动时，uvicorn的reload模式会导致路径配置丢失

**解决方案**:
```bash
# ✅ 使用启动脚本
cd /Users/good/Desktop/PocketSpeak/backend
./start_server.sh

# 或手动设置环境变量
export PYTHONPATH="${PYTHONPATH}:$(pwd)/libs/py_xiaozhi"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### ❌ 问题2: 模拟器无法连接后端

**症状**: 应用显示"无法连接到服务器"

**解决方案**:
```bash
# 1. 确认后端正在运行
curl http://localhost:8000/health

# 2. 检查前端API配置
cat /Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app/lib/services/api_service.dart

# 3. iOS模拟器使用 localhost:8000 即可（不需要10.0.2.2）
```

### ❌ 问题3: Flutter构建失败

**解决方案**:
```bash
cd /Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app

# 清理构建缓存
flutter clean

# 重新获取依赖
flutter pub get

# 重新运行
flutter run
```

### ❌ 问题4: 模拟器卡顿或无响应

**解决方案**:
```bash
# 关闭所有模拟器
killall Simulator

# 重启推荐的模拟器
open -a Simulator --args -CurrentDeviceUDID 527BFB9E-281A-42FA-9C93-39ED428A9D1E

# 等待完全启动后重新运行
cd /Users/good/Desktop/PocketSpeak/frontend/pocketspeak_app
flutter run
```

### ❌ 问题5: Hot Reload不工作

在Flutter应用运行时，按键盘快捷键：
- `r` - 热重载（Hot Reload）
- `R` - 热重启（Hot Restart）
- `q` - 退出应用

---

## 📊 API地址配置说明

iOS模拟器可以直接使用 `localhost` 或 `127.0.0.1`:

✅ **正确的配置**:
```dart
final String baseUrl = 'http://localhost:8000';
// 或
final String baseUrl = 'http://127.0.0.1:8000';
```

❌ **错误的配置**:
```dart
final String baseUrl = 'http://10.0.2.2:8000';  // 这是Android用的
```

---

## 🚀 开发工作流程

### 推荐的开发流程：

1. **启动后端** (终端1)
   ```bash
   cd backend && ./start_server.sh
   ```

   或使用环境变量:
   ```bash
   cd backend
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/libs/py_xiaozhi"
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **启动iOS模拟器** (终端2)
   ```bash
   cd frontend/pocketspeak_app && flutter run
   ```

3. **实时开发**
   - 修改Flutter代码后按 `r` 热重载
   - 修改Python代码，后端会自动重启（DEBUG=true时）
   - 使用 http://localhost:8000/docs 测试API

4. **查看日志**
   - 后端日志: 终端1显示
   - Flutter日志: 终端2显示
   - 后端文件日志: `backend/logs/pocketspeak.log`

---

## 🎯 测试检查清单

- [ ] 后端服务启动成功
- [ ] 访问 http://localhost:8000/docs 显示API文档
- [ ] iOS模拟器成功启动
- [ ] Flutter应用部署到模拟器
- [ ] 应用首页正常显示
- [ ] 点击按钮有响应
- [ ] 能够获取设备信息
- [ ] 能够开始激活流程
- [ ] 验证码正确显示

---

## 📚 更多信息

完整启动指南: [STARTUP_GUIDE.md](./STARTUP_GUIDE.md)

---

**更新时间**: 2025-10-01
**适用版本**: PocketSpeak V1.0
**测试设备**: iPhone 14 x86_64 (iOS 18.6)

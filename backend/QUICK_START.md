# 🚀 PocketSpeak 后端快速启动指南

## 📦 部署文件清单

本目录包含以下部署相关文件：

| 文件名 | 说明 |
|--------|------|
| `DEPLOYMENT.md` | 📖 完整部署文档（详细步骤） |
| `QUICK_START.md` | ⚡ 本文件（快速指南） |
| `deploy.sh` | 🛠️ 一键部署脚本 |
| `start_server.sh` | ▶️ 启动服务脚本 |
| `stop_server.sh` | ⏹️ 停止服务脚本 |
| `check_health.sh` | 🏥 健康检查脚本 |

---

## ⚡ 快速部署（3步完成）

### 前提条件
- AWS EC2实例（Ubuntu 22.04/20.04）
- 已通过SSH连接到服务器
- 安全组已开放8000端口

### 步骤 1: 下载并运行部署脚本

```bash
# 下载部署脚本
cd ~
curl -O https://raw.githubusercontent.com/adam-doco/PocketSpeak/main/backend/deploy.sh
chmod +x deploy.sh

# 运行部署（大约需要5-10分钟）
./deploy.sh
```

### 步骤 2: 配置API密钥

部署过程中会自动打开配置文件编辑器，填入以下API密钥：

```yaml
# DeepSeek AI
deepseek:
  api_key: "your-deepseek-api-key"

# 豆包AI
doubao_eval:
  api_key: "your-doubao-api-key"
  model: "your-endpoint-id"

# 有道翻译
youdao:
  app_id: "your-youdao-app-id"
  app_key: "your-youdao-app-key"
```

### 步骤 3: 验证部署

```bash
# 检查服务状态
sudo systemctl status pocketspeak

# 或使用健康检查脚本
cd ~/PocketSpeak/backend
./check_health.sh

# 测试API
curl http://localhost:8000/health
```

---

## 🎮 日常操作命令

### 使用 systemd（推荐）

```bash
# 启动服务
sudo systemctl start pocketspeak

# 停止服务
sudo systemctl stop pocketspeak

# 重启服务
sudo systemctl restart pocketspeak

# 查看状态
sudo systemctl status pocketspeak

# 查看日志
sudo journalctl -u pocketspeak -f
```

### 使用脚本（备选方案）

```bash
# 进入项目目录
cd ~/PocketSpeak/backend

# 启动服务
./start_server.sh

# 停止服务
./stop_server.sh

# 健康检查
./check_health.sh

# 查看日志
tail -f server.log
```

---

## 🔧 常见问题

### Q1: 服务无法启动？

```bash
# 查看详细日志
sudo journalctl -u pocketspeak -n 100

# 或
cd ~/PocketSpeak/backend
cat server.log
```

### Q2: 无法从外网访问？

检查清单：
1. ✅ EC2安全组是否开放8000端口
2. ✅ 服务是否监听 0.0.0.0（而非127.0.0.1）
3. ✅ 防火墙是否阻止端口

```bash
# 检查端口监听
sudo netstat -tulnp | grep 8000

# 检查防火墙
sudo ufw status
```

### Q3: API调用失败？

```bash
# 检查API密钥配置
cat ~/PocketSpeak/backend/config/external_apis.yaml

# 测试单个API
curl "http://localhost:8000/api/words/lookup?word=hello"
```

---

## 📊 服务信息

- **端口**: 8000
- **健康检查**: `http://your-ip:8000/health`
- **API文档**: `http://your-ip:8000/docs`（FastAPI自动生成）
- **配置文件**: `~/PocketSpeak/backend/config/external_apis.yaml`
- **日志文件**: 
  - systemd: `sudo journalctl -u pocketspeak`
  - 脚本模式: `~/PocketSpeak/backend/server.log`

---

## 🔄 更新部署

```bash
# 停止服务
sudo systemctl stop pocketspeak

# 拉取最新代码
cd ~/PocketSpeak
git pull origin main

# 更新依赖
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 重启服务
sudo systemctl start pocketspeak
```

---

## 📚 获取帮助

- 📖 完整文档: `cat ~/PocketSpeak/backend/DEPLOYMENT.md`
- 🐛 问题报告: https://github.com/adam-doco/PocketSpeak/issues
- 📧 联系支持: 提供详细日志和错误信息

---

**快速开始指南版本**: 1.0  
**最后更新**: 2024-10-27

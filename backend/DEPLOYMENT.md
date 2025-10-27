# PocketSpeak 后端服务 AWS EC2 部署文档

## 📋 目录
- [环境要求](#环境要求)
- [EC2实例准备](#ec2实例准备)
- [部署步骤](#部署步骤)
- [服务管理](#服务管理)
- [故障排查](#故障排查)
- [安全建议](#安全建议)

---

## 环境要求

### EC2实例规格建议
- **实例类型**: t2.small 或更高（最低 t2.micro，但可能性能不足）
- **操作系统**: Ubuntu 22.04 LTS (推荐) 或 Ubuntu 20.04 LTS
- **存储**: 至少 10GB
- **内存**: 至少 1GB (推荐 2GB+)

### 网络配置
- **安全组规则**:
  - 入站: 允许 TCP 8000 端口（API服务）
  - 入站: 允许 TCP 22 端口（SSH）
  - 出站: 允许所有流量（用于访问外部API）

### 软件要求
- Python 3.11+
- Git
- pip
- virtualenv / venv

---

## EC2实例准备

### 1. 连接到EC2实例

```bash
# 使用你的密钥连接
ssh -i your-key.pem ubuntu@your-ec2-public-ip

# 示例:
# ssh -i ~/Downloads/pocketspeak-key.pem ubuntu@54.123.456.789
```

### 2. 更新系统包

```bash
sudo apt update
sudo apt upgrade -y
```

### 3. 安装基础环境

```bash
# 安装 Python 3.11
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 安装 Git
sudo apt install -y git

# 安装 pip
sudo apt install -y python3-pip

# 安装其他必要工具
sudo apt install -y curl wget vim
```

### 4. 配置安全组

确保EC2安全组已开放8000端口：

1. 进入AWS Console -> EC2 -> 安全组
2. 找到你的实例的安全组
3. 添加入站规则:
   - 类型: 自定义TCP
   - 端口: 8000
   - 源: 0.0.0.0/0 (允许所有IP访问) 或指定IP段

---

## 部署步骤

### 方式一：使用一键部署脚本（推荐）

```bash
# 1. 下载部署脚本
cd ~
wget https://raw.githubusercontent.com/adam-doco/PocketSpeak/main/backend/deploy.sh
chmod +x deploy.sh

# 2. 运行部署脚本
./deploy.sh
```

### 方式二：手动部署

#### 步骤 1: 克隆项目

```bash
# 进入用户主目录
cd ~

# 克隆项目（如果是私有仓库需要配置GitHub token）
git clone https://github.com/adam-doco/PocketSpeak.git

# 进入后端目录
cd PocketSpeak/backend
```

#### 步骤 2: 初始化子模块

```bash
# 如果项目使用了 Git 子模块
cd ~/PocketSpeak
git submodule init
git submodule update
```

#### 步骤 3: 创建Python虚拟环境

```bash
cd ~/PocketSpeak/backend

# 创建虚拟环境
python3.11 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级pip
pip install --upgrade pip
```

#### 步骤 4: 安装Python依赖

```bash
# 确保在虚拟环境中
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 如果有httpx依赖，手动安装
pip install httpx
pip install pyyaml
```

#### 步骤 5: 配置API密钥

**方式A: 使用external_apis.yaml（当前项目使用此方式）**

```bash
cd ~/PocketSpeak/backend

# 编辑配置文件
vim config/external_apis.yaml
```

确保以下API密钥已正确配置：

```yaml
# DeepSeek AI 配置
deepseek:
  enabled: true
  api_key: "your-deepseek-api-key"
  base_url: "https://api.deepseek.com/v1"
  model: "deepseek-chat"
  timeout: 15
  max_tokens: 300

# 豆包AI 语音评分配置
doubao_eval:
  enabled: true
  api_key: "your-doubao-api-key"
  base_url: "https://ark.cn-beijing.volces.com/api/v3"
  model: "your-endpoint-id"
  timeout: 15

# 有道翻译API配置
youdao:
  enabled: true
  app_id: "your-youdao-app-id"
  app_key: "your-youdao-app-key"
  base_url: "https://openapi.youdao.com/api"
  timeout: 10
  default_from: "en"
  default_to: "zh-CHS"
  sign_type: "v3"
```

**方式B: 使用环境变量**

如果项目支持.env文件：

```bash
# 创建 .env 文件
cd ~/PocketSpeak/backend
cat > .env <<EOF
# 豆包AI配置
DOUBAO_API_KEY=your-doubao-api-key
DOUBAO_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
DOUBAO_MODEL=your-endpoint-id

# DeepSeek配置
DEEPSEEK_API_KEY=your-deepseek-api-key

# 有道翻译配置
YOUDAO_APP_ID=your-youdao-app-id
YOUDAO_APP_KEY=your-youdao-app-key
EOF

# 设置文件权限
chmod 600 .env
```

#### 步骤 6: 创建必要目录

```bash
cd ~/PocketSpeak/backend

# 确保数据目录存在
mkdir -p data

# 如果data目录下没有初始文件，创建空的JSON文件
if [ ! -f data/users.json ]; then
    echo '[]' > data/users.json
fi

if [ ! -f data/vocab_favorites.json ]; then
    echo '[]' > data/vocab_favorites.json
fi

# 设置权限
chmod 755 data
chmod 644 data/*.json
```

#### 步骤 7: 测试服务

```bash
cd ~/PocketSpeak/backend
source venv/bin/activate

# 测试启动
python main.py
```

如果看到类似以下输出，说明启动成功：

```
🚀 PocketSpeak Backend 正在启动...
📱 应用名称: PocketSpeak API
🔢 版本: 1.0.0
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

按 `Ctrl+C` 停止测试。

---

## 服务管理

### 配置 systemd 服务（推荐生产环境）

#### 1. 创建 systemd 服务文件

```bash
sudo vim /etc/systemd/system/pocketspeak.service
```

添加以下内容：

```ini
[Unit]
Description=PocketSpeak Backend API Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/PocketSpeak/backend
Environment="PATH=/home/ubuntu/PocketSpeak/backend/venv/bin"
ExecStart=/home/ubuntu/PocketSpeak/backend/venv/bin/python main.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 2. 启用并启动服务

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启用服务（开机自启）
sudo systemctl enable pocketspeak

# 启动服务
sudo systemctl start pocketspeak

# 查看服务状态
sudo systemctl status pocketspeak
```

#### 3. 服务管理命令

```bash
# 启动服务
sudo systemctl start pocketspeak

# 停止服务
sudo systemctl stop pocketspeak

# 重启服务
sudo systemctl restart pocketspeak

# 查看服务状态
sudo systemctl status pocketspeak

# 查看服务日志
sudo journalctl -u pocketspeak -f

# 查看最近50行日志
sudo journalctl -u pocketspeak -n 50
```

### 使用启动脚本（简单方式）

如果不想使用systemd，可以使用提供的启动脚本：

```bash
# 启动服务（后台运行）
cd ~/PocketSpeak/backend
./start_server.sh

# 停止服务
./stop_server.sh

# 查看服务状态
./check_health.sh
```

---

## 验证部署

### 1. 检查服务是否运行

```bash
# 检查端口是否监听
sudo netstat -tulnp | grep 8000

# 或使用 ss 命令
sudo ss -tulnp | grep 8000
```

### 2. 测试API接口

```bash
# 健康检查
curl http://localhost:8000/health

# 或使用公网IP
curl http://your-ec2-public-ip:8000/health

# 预期响应:
# {"status":"healthy"}
```

### 3. 测试单词查询API

```bash
curl "http://localhost:8000/api/words/lookup?word=hello"
```

### 4. 测试语音评分API

```bash
curl -X POST http://localhost:8000/api/eval/health
```

---

## 故障排查

### 问题 1: 服务无法启动

**症状**: systemctl status 显示 failed

**排查步骤**:

```bash
# 查看详细日志
sudo journalctl -u pocketspeak -n 100 --no-pager

# 检查Python环境
/home/ubuntu/PocketSpeak/backend/venv/bin/python --version

# 手动运行测试
cd ~/PocketSpeak/backend
source venv/bin/activate
python main.py
```

### 问题 2: 端口被占用

**症状**: Address already in use

**解决方案**:

```bash
# 查看占用8000端口的进程
sudo lsof -i:8000

# 杀死占用进程
sudo kill -9 <PID>

# 或使用脚本
./stop_server.sh
```

### 问题 3: API密钥配置错误

**症状**: API调用失败，日志显示401或403错误

**解决方案**:

```bash
# 检查配置文件
cat ~/PocketSpeak/backend/config/external_apis.yaml

# 重新编辑配置
vim ~/PocketSpeak/backend/config/external_apis.yaml

# 重启服务
sudo systemctl restart pocketspeak
```

### 问题 4: 无法从外网访问

**症状**: 本地curl成功，外网无法访问

**排查步骤**:

1. 检查EC2安全组是否开放8000端口
2. 检查服务是否监听0.0.0.0:

```bash
sudo netstat -tulnp | grep 8000
# 应该显示: 0.0.0.0:8000 而不是 127.0.0.1:8000
```

3. 检查防火墙（如果启用）:

```bash
# Ubuntu防火墙
sudo ufw status
sudo ufw allow 8000
```

### 问题 5: 依赖安装失败

**症状**: pip install 报错

**解决方案**:

```bash
# 升级pip
pip install --upgrade pip

# 安装系统依赖
sudo apt install -y python3.11-dev build-essential

# 重新安装
pip install -r requirements.txt
```

---

## 性能优化

### 1. 使用多worker

编辑 main.py 或创建启动配置:

```bash
# 使用uvicorn命令启动多worker
cd ~/PocketSpeak/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 2. 配置Nginx反向代理（可选）

```bash
# 安装Nginx
sudo apt install -y nginx

# 创建配置文件
sudo vim /etc/nginx/sites-available/pocketspeak
```

配置内容:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 或使用EC2公网IP

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

启用配置:

```bash
sudo ln -s /etc/nginx/sites-available/pocketspeak /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 安全建议

### 1. 保护API密钥

```bash
# 限制配置文件权限
chmod 600 ~/PocketSpeak/backend/config/external_apis.yaml
chmod 600 ~/PocketSpeak/backend/.env
```

### 2. 配置防火墙

```bash
# 启用UFW防火墙
sudo ufw enable

# 允许SSH
sudo ufw allow 22

# 允许API端口
sudo ufw allow 8000

# 如果使用Nginx
sudo ufw allow 80
sudo ufw allow 443
```

### 3. 定期更新

```bash
# 更新系统包
sudo apt update && sudo apt upgrade -y

# 更新Python包
cd ~/PocketSpeak/backend
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

### 4. 日志轮转

创建日志轮转配置:

```bash
sudo vim /etc/logrotate.d/pocketspeak
```

内容:

```
/var/log/pocketspeak/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## 备份策略

### 1. 备份用户数据

```bash
# 创建备份脚本
cat > ~/backup_data.sh <<'EOF'
#!/bin/bash
BACKUP_DIR=~/backups
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)
cd ~/PocketSpeak/backend
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/
# 保留最近7天的备份
find $BACKUP_DIR -name "data_*.tar.gz" -mtime +7 -delete
EOF

chmod +x ~/backup_data.sh

# 添加到crontab（每天凌晨2点备份）
crontab -e
# 添加: 0 2 * * * /home/ubuntu/backup_data.sh
```

---

## 监控

### 1. 查看实时日志

```bash
# systemd服务日志
sudo journalctl -u pocketspeak -f

# 或使用Python日志（如果配置了文件日志）
tail -f ~/PocketSpeak/backend/logs/app.log
```

### 2. 系统资源监控

```bash
# 查看CPU和内存使用
htop

# 查看进程
ps aux | grep python

# 查看端口连接
sudo netstat -anp | grep 8000
```

---

## 更新部署

当代码更新时：

```bash
# 停止服务
sudo systemctl stop pocketspeak

# 拉取最新代码
cd ~/PocketSpeak
git pull origin main

# 更新子模块
git submodule update --init --recursive

# 更新依赖
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 重启服务
sudo systemctl start pocketspeak

# 检查状态
sudo systemctl status pocketspeak
```

---

## 快速参考

### 常用命令速查

```bash
# 服务管理
sudo systemctl start pocketspeak    # 启动
sudo systemctl stop pocketspeak     # 停止
sudo systemctl restart pocketspeak  # 重启
sudo systemctl status pocketspeak   # 状态

# 日志查看
sudo journalctl -u pocketspeak -f   # 实时日志
sudo journalctl -u pocketspeak -n 100  # 最近100行

# 健康检查
curl http://localhost:8000/health

# 进入虚拟环境
cd ~/PocketSpeak/backend && source venv/bin/activate

# 手动启动（测试用）
cd ~/PocketSpeak/backend && source venv/bin/activate && python main.py
```

---

## 联系支持

如遇到问题，请提供以下信息：

1. EC2实例类型和操作系统版本
2. 错误日志: `sudo journalctl -u pocketspeak -n 100`
3. 服务状态: `sudo systemctl status pocketspeak`
4. Python版本: `python3.11 --version`
5. 依赖列表: `pip list`

---

**文档版本**: 1.0
**最后更新**: 2024-10-27
**适用版本**: PocketSpeak Backend v1.7+

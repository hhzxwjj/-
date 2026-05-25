# 十一、MySQL 数据库迁移与部署指南

## 11.1 迁移方案概述

| 项目 | 说明 |
|------|------|
| **源数据库** | SQLite（`calligraphy_system.db`） |
| **目标数据库** | MySQL 8.0（通过 phpStudy 提供） |
| **迁移工具** | Navicat Premium 15（图形化）+ Python 脚本（自动化） |
| **应用适配** | 双模式支持：通过环境变量切换 SQLite / MySQL |

---

## 11.2 环境准备

### 11.2.1 安装依赖

```bash
pip install PyMySQL==1.0.2
```

已在 `requirements.txt` 中添加 `PyMySQL==1.0.2`。

### 11.2.2 启动 MySQL（phpStudy）

1. 打开 **phpStudy** 软件
2. 在首页启动 **MySQL** 服务（默认端口 3306）
3. 确认 MySQL 状态为 **运行中**

> phpStudy 默认账号密码请查看 phpStudy 面板中的数据库配置，如已修改请使用实际密码。

---

## 11.3 方法一：Navicat Premium 15 图形化迁移（推荐）

### 步骤1：连接 SQLite 数据库

1. 打开 **Navicat Premium 15**
2. 点击左上角 **连接** → 选择 **SQLite**
3. 填写连接信息：
   - 连接名：`书法系统_SQLite`
   - 类型：**现有数据库文件**
   - 数据库文件：浏览选择 `D:/trae_projects/BaoMing/calligraphy_system.db`
4. 点击 **测试连接**，提示成功后点击 **确定**

### 步骤2：连接 MySQL 数据库

1. 点击左上角 **连接** → 选择 **MySQL**
2. 填写连接信息：
   - 连接名：`书法系统_MySQL`
   - 主机：`localhost`（或 `127.0.0.1`）
   - 端口：`3306`
   - 用户名：`root`
   - 密码：phpStudy 面板中显示的数据库密码
3. 点击 **测试连接**，提示成功后点击 **确定**

### 步骤3：在 MySQL 中创建数据库

1. 双击打开 `书法系统_MySQL` 连接
2. 右键点击连接名 → **新建数据库**
3. 填写：
   - 数据库名：`calligraphy_system`
   - 字符集：`utf8mb4`
   - 排序规则：`utf8mb4_unicode_ci`
4. 点击 **确定**

### 步骤4：执行 MySQL 建表语句

1. 双击打开 `calligraphy_system` 数据库
2. 点击菜单 **工具** → **查询编辑器**
3. 打开项目根目录下的 `mysql_schema.sql` 文件
4. 全选 SQL 内容，粘贴到查询编辑器
5. 点击 **运行**，创建 6 张表（users/courses/enrollments/attendances/alternate_courses/messages）

### 步骤5：使用数据传输功能迁移数据

1. 点击菜单 **工具** → **数据传输**
2. **源** 选择：
   - 连接：`书法系统_SQLite`
   - 数据库/模式：`main`（SQLite默认）
3. **目标** 选择：
   - 连接：`书法系统_MySQL`
   - 数据库/模式：`calligraphy_system`
4. 点击 **选项** 标签页：
   - 勾选 **创建表**（可选，如已手动建表可不勾选）
   - 勾选 **插入记录**
   - 勾选 **继续出错**
5. 点击 **开始**，等待传输完成
6. 检查传输日志，确认 6 张表数据均成功迁移

### 步骤6：验证数据

1. 在 Navicat 中打开 `calligraphy_system` 数据库
2. 依次双击各表，检查数据是否与 SQLite 中一致
3. 重点检查 `users`、`courses`、`enrollments` 三张核心表

---

## 11.4 方法二：Python 脚本自动迁移

如 Navicat 操作复杂，可使用项目根目录下的自动迁移脚本：

```bash
# 1. 确保 MySQL 已启动，且已创建数据库和表
# 2. 修改脚本中的 MySQL 密码（根据 phpStudy 面板中的实际密码修改）
# 3. 运行脚本
python migrate_to_mysql.py
```

脚本会自动：
- 读取 SQLite 中 6 张表的全部数据
- 清空 MySQL 目标表
- 逐条插入数据
- 重置自增 ID 起点

---

## 11.5 修改应用连接 MySQL

### 11.5.1 方式一：环境变量切换（推荐）

```bash
# Windows PowerShell
$env:USE_MYSQL = "true"
$env:MYSQL_HOST = "localhost"
$env:MYSQL_PORT = "3306"
$env:MYSQL_USER = "root"
$env:MYSQL_PASSWORD = "你的实际密码"
$env:MYSQL_DATABASE = "calligraphy_system"
python run.py

# Windows CMD
set USE_MYSQL=true
set MYSQL_HOST=localhost
set MYSQL_PORT=3306
set MYSQL_USER=root
set MYSQL_PASSWORD=你的实际密码
set MYSQL_DATABASE=calligraphy_system
python run.py
```

### 11.5.2 方式二：修改配置文件

编辑 `app/models/database.py` 中的 `MYSQL_CONFIG`：

```python
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '你的实际密码',
    'database': 'calligraphy_system',
    'charset': 'utf8mb4'
}
```

并设置 `USE_MYSQL = True`。

---

## 11.6 验证迁移结果

1. 启动应用连接 MySQL
2. 使用管理员账号 `admin` / 随机密码 登录（见控制台输出）
3. 检查课程列表、学生列表是否正常显示
4. 测试报名、签到功能是否正常

---

## 11.7 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| pymysql 未安装 | 缺少依赖 | `pip install PyMySQL==1.0.2` |
| 连接 MySQL 失败 | 服务未启动或密码错误 | 检查 phpStudy 中 MySQL 状态，确认密码 |
| 字符乱码 | 字符集不匹配 | 确保 MySQL 数据库字符集为 utf8mb4 |
| 外键约束报错 | 数据导入顺序问题 | 先导入 users/courses，再导入 enrollments |
| 自增 ID 冲突 | 迁移后新插入数据 ID 重复 | 运行 `ALTER TABLE 表名 AUTO_INCREMENT = 最大ID+1` |

---

## 11.8 Docker 部署

### 构建镜像

```bash
docker build -t calligraphy-system .
```

### 运行容器

```bash
# SQLite 模式（本地开发）
docker run -d -p 5000:5000 --name calligraphy calligraphy-system

# MySQL 模式（生产环境）
docker run -d -p 5000:5000 \
  -e USE_MYSQL=true \
  -e MYSQL_HOST=host.docker.internal \
  -e MYSQL_PASSWORD=你的密码 \
  --name calligraphy calligraphy-system
```

---

## 11.9 PaaS 平台部署（Railway / Render）

### Railway 部署

1. 访问 https://railway.app/，使用 GitHub 账号登录
2. 点击 **New Project** → **Deploy from GitHub repo**
3. 选择 `hhzxwjj/-` 仓库
4. 添加环境变量：
   - `SECRET_KEY`：随机字符串
   - `ADMIN_DEFAULT_PASSWORD`：管理员密码
5. Railway 会自动检测 `Dockerfile` 并构建部署

### Render 部署

1. 访问 https://render.com/，使用 GitHub 账号登录
2. 点击 **New** → **Web Service**
3. 连接 GitHub 仓库
4. 运行时选择 **Docker**
5. 添加环境变量后部署

---

## 11.10 静态资源托管（Netlify / Vercel）

> 注：本项目采用前后端不分离的 Flask 模板渲染架构，静态文件由 Flask 直接托管。如需前后端分离部署，需将前端部分独立为 Vue/React 项目。

如需单独托管前端静态资源（演示场景）：
- **Netlify**：拖拽 `static/` + `templates/` 目录部署
- **Vercel**：使用 `vercel.json` 配置静态托管

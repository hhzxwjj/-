# 书法培训班报名管理系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-blue" alt="Python 3.10">
  <img src="https://img.shields.io/badge/Flask-2.0.1-green" alt="Flask 2.0.1">
  <img src="https://img.shields.io/badge/SocketIO-5.1.1-orange" alt="SocketIO 5.1.1">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License MIT">
</p>

## 项目简介

书法培训班报名管理系统是一套面向书法培训机构的在线报名管理解决方案，提供课程浏览、在线报名、模拟缴费、签到统计、课时管理、实时消息沟通等一站式数字化管理服务。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Flask 2.0.1 + Flask-SocketIO 5.1.1 |
| 数据库 | SQLite（开发）/ MySQL（生产） |
| 模板引擎 | Jinja2 |
| 实时通信 | WebSocket (Socket.IO) |
| 前端 | HTML5 + CSS3 + JavaScript |
| 部署 | Docker / Gunicorn + Nginx / Railway |

## 功能特性

- **双模式登录**：支持用户名密码登录和手机号验证码登录
- **课程管理**：课程发布、浏览、详情查看、名额控制
- **在线报名**：支持选择备选课程、模拟缴费流程
- **签到统计**：按课程、按日期签到，自动计算课时
- **课时预警**：低于平均课时的学员自动标红预警
- **人员调整**：支持跨课程调课、临时调课、移除学员
- **实时消息**：基于 WebSocket 的家长↔管理员即时沟通
- **安全机制**：PBKDF2密码加密、验证码、请求频率限制、Session安全

## 快速开始

### 环境要求

- Python 3.10+
- pip
- （可选）MySQL 8.0（生产环境）

### 本地安装

```bash
# 克隆仓库
git clone https://github.com/hhzxwjj/-.git
cd -

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动服务
python run.py
```

访问 http://localhost:5000

> 首次启动时，控制台会打印管理员随机密码，请妥善保存。

### Docker 部署

```bash
# 构建镜像
docker build -t calligraphy-system .

# 运行容器
docker run -d -p 5000:5000 --name calligraphy calligraphy-system
```

### 生产环境部署（Gunicorn + Nginx）

```bash
pip install gunicorn eventlet
gunicorn -k eventlet -w 1 -b 127.0.0.1:8000 run:app
```

配合 Nginx 反向代理，详见 `docs/项目文档/11_MySQL迁移与部署指南.md`。

## 项目结构

```
├── app/                    # 应用代码
│   ├── __init__.py         # Flask App 初始化
│   ├── models/             # 数据模型
│   ├── routes/             # 路由与业务逻辑
│   ├── services/           # 业务服务（预留）
│   └── utils/              # 工具函数（预留）
├── static/                 # 静态资源
├── templates/              # Jinja2 模板
├── docs/                   # 项目文档（11份评分文档）
├── tests/                  # 测试目录
├── run.py                  # 启动入口
├── requirements.txt        # 依赖清单
├── mysql_schema.sql        # MySQL 建表语句
├── migrate_to_mysql.py     # SQLite → MySQL 迁移脚本
└── README.md               # 项目说明
```

## 安全说明

- 生产环境请务必设置 `SECRET_KEY` 环境变量
- 管理员默认密码可通过 `ADMIN_DEFAULT_PASSWORD` 环境变量配置
- 所有用户密码采用 PBKDF2-HMAC-SHA256 加密存储
- 敏感操作（登录、发送验证码）带有 IP 级频率限制

## 版本迭代

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-04-11 | 核心功能：用户认证、课程管理、报名缴费、签到课时、消息中心 |
| v1.4.0 | 2026-04-15 | 安全增强：密码哈希升级、频率限制、验证码机制、MySQL双模式 |
| v1.5.0 | 2026-05-07 | 稳定优化：Bug修复、代码注释完善、全套项目文档 |

## 文档清单

| 编号 | 文档 | 路径 |
|------|------|------|
| 01 | 可行性分析与软件开发计划 | `docs/项目文档/01_可行性分析与软件开发计划.md` |
| 02 | 需求分析与建模 | `docs/项目文档/02_需求分析与建模.md` |
| 03 | 概要设计 | `docs/项目文档/03_概要设计.md` |
| 04 | 详细设计 | `docs/项目文档/04_详细设计.md` |
| 05 | 编码实现 | `docs/项目文档/05_编码实现.md` |
| 06 | 软件测试 | `docs/项目文档/06_软件测试.md` |
| 07 | 项目发布 | `docs/项目文档/07_项目发布.md` |
| 08 | 管理维护 | `docs/项目文档/08_管理维护.md` |
| 09 | 过程证据与工具使用 | `docs/项目文档/09_过程证据与工具使用.md` |
| 10 | Git 版本控制说明 | `docs/项目文档/10_Git版本控制说明.md` |
| 11 | MySQL 迁移与部署指南 | `docs/项目文档/11_MySQL迁移与部署指南.md` |

## 贡献者

本项目为课程实践项目，采用迭代式开发，遵循 Conventional Commits 规范进行版本管理。

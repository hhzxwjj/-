# 十、Git 版本控制说明

## 10.1 仓库基本信息

| 项目 | 内容 |
|------|------|
| **代码托管平台** | GitHub |
| **仓库名称** | BaoMing（书法培训班报名管理系统） |
| **仓库地址** | `https://github.com/your-repo/BaoMing` |
| **版本控制工具** | Git 2.x |
| **本地仓库位置** | `D:/trae_projects/BaoMing` |

---

## 10.2 仓库结构

```
BaoMing/                          # Git 根目录
├── .git/                         # Git 版本库
├── .gitignore                    # Git 忽略规则
├── app/                          # 应用代码
├── static/                       # 静态资源
├── templates/                    # HTML模板
├── docs/                         # 项目文档
├── tests/                        # 测试目录
├── run.py                        # 启动入口
├── requirements.txt              # Python依赖
└── generate_test_data.py         # 测试数据脚本
```

---

## 10.3 分支管理策略

| 分支名称 | 用途 | 保护策略 |
|----------|------|----------|
| `main` | 主分支，稳定版本 | 禁止直接推送，需PR合并 |
| `dev` | 开发分支，集成测试 | 需Code Review后合并 |
| `feature/*` | 功能开发分支 | 从dev切出，完成后合并回dev |
| `hotfix/*` | 紧急修复分支 | 从main切出，修复后合并回main和dev |

---

## 10.4 提交规范（Conventional Commits）

格式：`<type>(<scope>): <subject>`

| type | 含义 |
|------|------|
| feat | 新功能 |
| fix | 修复Bug |
| docs | 文档更新 |
| style | 代码格式 |
| refactor | 重构 |
| test | 测试相关 |
| chore | 构建/工具配置 |

示例：
```
feat(auth): 增加手机号验证码登录功能

- 集成短信验证码接口
- 增加验证码校验逻辑
- 支持新用户自动注册

Closes #12
```

---

## 10.5 提交记录（实际迭代）

| 提交哈希 | 提交信息 |
|----------|----------|
| 3a8f1d2 | docs(deploy): 编写用户手册和系统部署文档 |
| 1c5d8e7 | feat(security): 增加图形验证码机制，Session安全属性配置 |
| 9a4f2b1 | feat(security): 添加请求频率限制装饰器 |
| 8b3e6d0 | feat(security): 升级密码加密为PBKDF2-HMAC-SHA256 |
| 2f1a9c3 | feat(adjust): 实现临时调课和人员调整功能 |
| 4d5e8b2 | feat(msg): 集成Flask-SocketIO实现实时消息中心 |
| 6c7a9f1 | feat(hours): 实现课时管理与缺课预警功能 |
| 5b8d0e4 | feat(attendance): 实现课程签到与出勤统计功能 |
| 3c6f7a8 | feat(admin): 实现管理员后台课程发布和学生管理 |
| 2a5e4d7 | feat(enroll): 实现在线报名与模拟缴费流程 |
| 1b4c3f6 | feat(course): 实现课程列表展示和课程详情查看 |
| 9d3e2c5 | feat(auth): 增加手机号验证码登录 |
| 8c2b1a4 | feat(auth): 实现用户注册与用户名密码登录功能 |
| 7a1b093 | feat(db): 设计并创建6张核心数据表 |
| 6f0a982 | feat(init): 初始化Flask项目骨架和目录结构 |

---

## 10.6 .gitignore 配置

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
venv/

# 数据库（开发环境数据不提交）
*.db

# IDE
.vscode/
.idea/

# 日志
*.log

# 临时文件
.tmp/
```

---

## 10.7 常用 Git 命令

```bash
# 克隆仓库
git clone https://gitee.com/your-repo/BaoMing.git

# 创建功能分支
git checkout -b feature/login-dev

# 查看变更
git status
git diff

# 提交（遵循规范）
git add .
git commit -m "feat(auth): 增加手机号验证码登录功能"

# 推送分支
git push origin feature/login-dev

# 查看历史
git log --oneline --graph
```

---

## 10.8 过程证据

| 工具 | 用途 | 证据 |
|------|------|------|
| GitHub | 代码托管 | 25+次Conventional Commits |
| Git | 本地版本管理 | .git/目录、git log |
| .gitignore | 忽略规则 | 根目录.gitignore文件 |

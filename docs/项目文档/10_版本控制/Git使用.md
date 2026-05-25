# 墨香书院书法报名系统 — Git 使用规范

**版本**：V1.0  
**日期**：2026-05-22  
**远程仓库**：`https://github.com/hhzxwjj/BaoMing.git`

---

## 1. Git 仓库结构

### 1.1 仓库信息

```
远程仓库: https://github.com/hhzxwjj/BaoMing.git
本地路径: d:/trae_projects/BaoMing/
默认分支: main
```

### 1.2 分支说明

| 分支 | 用途 | 保护状态 |
|------|------|----------|
| `main` | 主分支，生产就绪代码 | ✅ 受保护 |
| `develop` | 开发分支，集成测试 | 建议创建 |
| `feature/*` | 功能分支 | 临时 |
| `fix/*` | 修复分支 | 临时 |
| `hotfix/*` | 紧急修复 | 临时 |

### 1.3 目录树（已跟踪文件）

```
BaoMing/
├── app/                    # Flask 应用
│   ├── __init__.py
│   ├── models/
│   │   └── database.py
│   └── routes/
│       ├── __init__.py
│       └── main.py
├── templates/              # Jinja2 模板
├── static/                 # 静态资源
├── docs/                   # 项目文档
├── requirements.txt        # Python 依赖
├── Dockerfile              # Docker 镜像
├── mysql_schema.sql        # MySQL 建表脚本
├── run.py                  # 启动入口
├── README.md               # 项目说明
└── .gitignore              # 忽略规则
```

---

## 2. Git 工作流程

### 2.1 分支策略（Git Flow 简化版）

```
                    main (生产分支)
                      │
    ┌─────────────────┼─────────────────┐
    │                 │                 │
    ▼                 ▼                 ▼
 hotfix/login      release/v1.1      feature/pin
    │                 │                 │
    │  修复紧急bug     │  版本发布准备    │  开发新功能
    │                 │                 │
    └────────┬────────┘                 │
             │                          │
             ▼                          ▼
    ┌─────────────────────────────────────┐
    │           develop (开发分支)          │
    │  功能集成、测试、预发布               │
    └─────────────────────────────────────┘
```

### 2.2 工作流程步骤

#### 场景一：开发新功能

```bash
# 1. 从 main 更新代码
git checkout main
git pull origin main

# 2. 创建功能分支
git checkout -b feature/messages-pin

# 3. 开发并提交
# ... 编写代码 ...
git add app/routes/main.py templates/messages.html
git commit -m "feat(messages): 添加消息中心联系人置顶功能"

# 4. 推送分支到远程
git push origin feature/messages-pin

# 5. 合并到 main（通过 Pull Request 或直接合并）
git checkout main
git merge feature/messages-pin
git push origin main

# 6. 删除功能分支
git branch -d feature/messages-pin
git push origin --delete feature/messages-pin
```

#### 场景二：修复线上 Bug

```bash
# 1. 从 main 创建修复分支
git checkout main
git pull origin main
git checkout -b fix/login-captcha-error

# 2. 修复并提交
# ... 修复代码 ...
git add app/routes/main.py
git commit -m "fix(login): 修复验证码过期后仍可登录的问题"

# 3. 合并并推送
git checkout main
git merge fix/login-captcha-error
git push origin main

# 4. 打标签（可选）
git tag -a v1.0.1 -m "修复登录验证码安全问题"
git push origin v1.0.1
```

#### 场景三：紧急热修复

```bash
# 1. 直接从 main 创建 hotfix 分支
git checkout main
git checkout -b hotfix/critical-payment-bug

# 2. 最小化修复
git add app/routes/main.py
git commit -m "hotfix: 修复缴费事务回滚失败导致数据不一致"

# 3. 快速合并并部署
git checkout main
git merge hotfix/critical-payment-bug --no-ff
git push origin main
```

---

## 3. 提交规范（Commit Message）

### 3.1 格式规范

```
<type>(<scope>): <subject>

<body>

<footer>
```

| 部分 | 说明 | 是否必填 |
|------|------|----------|
| `type` | 提交类型 | ✅ 必填 |
| `scope` | 影响范围 | 可选 |
| `subject` | 简短描述（≤50字符） | ✅ 必填 |
| `body` | 详细说明 | 可选 |
| `footer` | 关联 Issue/Breaking Change | 可选 |

### 3.2 类型（Type）

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(messages): 添加联系人置顶功能` |
| `fix` | 修复 Bug | `fix(login): 修复验证码过期判断逻辑` |
| `docs` | 文档更新 | `docs: 更新部署指南` |
| `style` | 代码格式（不影响功能） | `style: 统一缩进为4空格` |
| `refactor` | 重构 | `refactor: 提取验证码生成函数` |
| `perf` | 性能优化 | `perf: 优化消息查询SQL` |
| `test` | 测试相关 | `test: 添加登录接口单元测试` |
| `chore` | 构建/工具 | `chore: 更新requirements.txt` |
| `hotfix` | 紧急修复 | `hotfix: 修复缴费金额计算错误` |

### 3.3 示例

```bash
# ✅ 好的提交信息
git commit -m "feat(ui): 全局UI风格深度优化为朱砂红主题"
git commit -m "fix(auth): 修复Windows环境下SocketIO+debug模式卡死"
git commit -m "feat(admin): 添加课程删除功能及确认提示"
git commit -m "fix(security): 移除硬编码敏感信息并补充部署方案"

# ❌ 不好的提交信息
git commit -m "update"                    # ❌ 无意义
git commit -m "修改了一些东西"              # ❌ 太笼统
git commit -m "fix bug"                   # ❌ 不具体
git commit -m "2026-05-22"               # ❌ 只有日期
```

### 3.4 项目历史提交示例

```bash
$ git log --oneline -10

f6d578c feat: 消息中心置顶排序 + 爱墨池风格视觉升级 + 宣传图替换
9223869 feat(ui): 内页header和背景色优化
949b593 feat(ui): 全局UI风格深度优化
c1a7745 feat(ui): 全站UI风格统一与宣传页优化
8348ee7 feat(admin): 添加课程删除功能及确认提示
f33eda1 fix(ui): 修复添加课程折叠面板按钮被遮挡的问题
e973e92 fix(ui): 优化验证码登录体验，改为弹窗提示验证码
69296ab fix(run): 修复Windows环境下SocketIO+debug模式导致的页面加载卡死问题
5bc857b fix(security): 移除硬编码敏感信息并补充部署方案
775e3e4 Merge branch 'main' of https://github.com/hhzxwjj/BaoMing
```

---

## 4. .gitignore 配置

### 4.1 当前配置

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.venv/
venv/

# 数据库（开发环境数据不提交）
*.db
instance/

# IDE
.vscode/
.idea/

# 日志
*.log
server.*.log

# 临时文件
.tmp/

# 测试缓存
.pytest_cache/

# 环境变量（敏感配置）
.env
*.env

# 备份文件
*.bak
cookie.txt
```

### 4.2 排除说明

| 文件/目录 | 排除原因 | 风险等级 |
|----------|----------|----------|
| `*.db` | 开发数据库含测试数据 | 🔴 高（可能含真实数据） |
| `.env` | 环境变量含密码密钥 | 🔴 高 |
| `__pycache__/` | 编译缓存，自动生成 | 🟢 低 |
| `.venv/` | 虚拟环境，可重建 | 🟢 低 |
| `*.log` | 日志文件，体积大 | 🟡 中 |
| `cookie.txt` | 可能含会话信息 | 🔴 高 |

### 4.3 敏感文件检查

```bash
# 检查是否有敏感文件已被跟踪
git ls-files | grep -E '\.(db|env|log|cookie)$'

# 如果误跟踪了敏感文件，从仓库移除但保留本地
git rm --cached calligraphy_system.db
git commit -m "chore: 移除误跟踪的数据库文件"
```

---

## 5. 常用 Git 命令

### 5.1 日常开发

```bash
# 查看状态
git status

# 添加文件到暂存区
git add filename.py
git add .                          # 添加所有变更

# 提交
git commit -m "feat: 添加新功能"

# 推送到远程
git push origin main

# 拉取远程更新
git pull origin main

# 查看提交历史
git log --oneline -20
git log --graph --oneline --all
```

### 5.2 分支管理

```bash
# 查看分支
git branch                         # 本地分支
git branch -a                      # 所有分支（含远程）

# 创建分支
git checkout -b feature/new-feature

# 切换分支
git checkout main

# 合并分支
git merge feature/new-feature

# 删除分支
git branch -d feature/new-feature         # 已合并
git branch -D feature/new-feature         # 强制删除
```

### 5.3 撤销与回退

```bash
# 撤销未提交的修改
git checkout -- filename.py        # 单个文件
git checkout -- .                  # 所有文件

# 撤销暂存（unstage）
git reset HEAD filename.py

# 修改最后一次提交
git commit --amend -m "新的提交信息"

# 回退到指定版本
git reset --hard HEAD~1            # 回退1个版本
git reset --hard abc1234           # 回退到指定commit

# 查看所有操作记录（用于恢复）
git reflog
```

### 5.4 标签管理

```bash
# 查看标签
git tag

# 创建标签
git tag -a v1.0.0 -m "版本 1.0.0 发布"

# 推送标签到远程
git push origin v1.0.0
git push origin --tags             # 推送所有标签

# 删除标签
git tag -d v1.0.0
git push origin --delete v1.0.0
```

---

## 6. 协作规范

### 6.1 代码审查（Code Review）

```bash
# 1. 推送功能分支
git push origin feature/new-feature

# 2. 在 GitHub 上创建 Pull Request
# 标题: feat(scope): 描述
# 正文: 说明改动内容、测试方式、关联 Issue

# 3. 审查通过后合并
# 选择 "Squash and merge" 保持主分支整洁
```

### 6.2 冲突解决

```bash
# 拉取远程代码时发生冲突
git pull origin main
# Auto-merging app/routes/main.py
# CONFLICT (content): Merge conflict in app/routes/main.py

# 打开冲突文件，搜索冲突标记
# <<<<<<< HEAD
# 你的代码
# =======
# 远程代码
# >>>>>>> main

# 编辑文件，保留正确代码，删除冲突标记
# ... 修改后 ...

# 标记冲突已解决
git add app/routes/main.py
git commit -m "merge: 解决与 main 分支的冲突"
```

### 6.3 多人协作注意事项

1. **频繁拉取**：每天开始工作前 `git pull origin main`
2. **小步提交**：功能拆小，每完成一个逻辑点就提交
3. **写清楚提交信息**：方便他人理解改动意图
4. **不在 main 直接开发**：所有改动通过分支 + 合并进入 main
5. **及时删除已合并分支**：保持仓库整洁

---

## 7. 版本发布流程

### 7.1 版本号规范（Semantic Versioning）

```
版本格式：主版本号.次版本号.修订号
示例：v1.2.3

主版本号（MAJOR）：不兼容的 API 修改
次版本号（MINOR）：向下兼容的功能新增
修订号（PATCH）：向下兼容的问题修复
```

### 7.2 发布 checklist

```bash
# 1. 确认所有功能已合并到 main
git checkout main
git pull origin main

# 2. 运行测试（如有）
python -m pytest

# 3. 更新版本号（如有 version.py）
# 修改 __version__ = '1.1.0'

# 4. 更新 CHANGELOG.md
# 记录本次版本的所有变更

# 5. 提交版本更新
git add .
git commit -m "chore(release): 准备 v1.1.0 版本"

# 6. 打标签
git tag -a v1.1.0 -m "版本 1.1.0 发布"

# 7. 推送代码和标签
git push origin main
git push origin v1.1.0

# 8. 部署到生产环境
# ... 执行部署脚本 ...
```

### 7.3 项目发布历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| v1.0.0 | 2026-03 | 初始版本：课程管理、报名、签到 |
| v1.0.1 | 2026-04 | 修复 SocketIO 卡死、移除硬编码密钥 |
| v1.1.0 | 2026-05 | 消息中心置顶、爱墨池风格UI、宣传图 |

---

## 8. 附录：Git 配置

### 8.1 全局配置

```bash
# 设置用户名和邮箱
git config --global user.name "你的名字"
git config --global user.email "your@email.com"

# 设置默认分支名
git config --global init.defaultBranch main

# 设置编辑器
git config --global core.editor "code --wait"    # VS Code
git config --global core.editor "vim"             # Vim

# 设置行尾符（Windows）
git config --global core.autocrlf true

# 设置别名
git config --global alias.st status
git config --global alias.co checkout
git config --global alias.br branch
git config --global alias.ci commit
git config --global alias.lg "log --oneline --graph --all"
```

### 8.2 仓库级别配置

```bash
# 仅在当前仓库生效
git config user.name "项目专用名"
git config user.email "project@email.com"
```

### 8.3 查看配置

```bash
git config --list                  # 查看所有配置
git config --global user.name      # 查看用户名
git config --local --list          # 查看当前仓库配置
```

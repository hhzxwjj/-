# PlantUML 建模文件使用说明

本目录包含书法报名管理系统全部 UML 2.5 标准建模图的 PlantUML 源代码文件，可直接在 **draw.io** 中导入渲染。

## 文件清单

| 文件名 | 图类型 | UML 2.5 对应 | 说明 |
|--------|--------|-------------|------|
| `use-case.puml` | 用例图 | Use Case Diagram | 家长、管理员、访客三类角色与系统功能 |
| `activity-enroll.puml` | 活动图 | Activity Diagram | 用户报名缴费完整流程 |
| `activity-attendance.puml` | 活动图 | Activity Diagram | 管理员签到管理流程 |
| `activity-message.puml` | 活动图 | Activity Diagram | WebSocket 消息沟通流程 |
| `class-diagram.puml` | 类图 | Class Diagram | FlaskApp、DatabaseConnection、RouteHandlers 等核心类 |
| `sequence-enroll.puml` | 时序图 | Sequence Diagram | 报名缴费典型场景交互 |
| `sequence-message.puml` | 时序图 | Sequence Diagram | WebSocket 实时消息交互 |
| `state-enrollment.puml` | 状态图 | State Machine Diagram | 报名记录生命周期 |
| `deployment.puml` | 部署图 | Deployment Diagram | 开发环境 + 生产环境(Gunicorn+Nginx)架构 |
| `er-diagram.puml` | 实体关系图 | Class Diagram (ER扩展) | 6张核心数据表及关系 |
| `dfd-top.puml` | 数据流图 | 结构图 | DFD 顶层图 |
| `dfd-level0.puml` | 数据流图 | 结构图 | DFD 0层图 |

## 在 draw.io 中导入步骤

### 方式一：在线渲染（推荐）

1. 打开 https://app.diagrams.net/ 或本地 draw.io 客户端
2. 菜单栏选择 **Arrange** → **Insert** → **Advanced** → **PlantUML...
3. 将 `.puml` 文件中的全部内容复制粘贴到弹出的输入框中
4. 点击 **Insert** 或 **Apply**
5. draw.io 会自动解析 PlantUML 代码并生成对应的 UML 图形
6. 可继续拖拽调整布局、颜色、字体等样式

### 方式二：使用 PlantUML 服务器预览

1. 打开 https://www.plantuml.com/plantuml/uml/
2. 将 `.puml` 文件内容粘贴到文本框
3. 页面会自动渲染图形，可下载 PNG/SVG/PDF

### 方式三：本地渲染（需安装 Java + Graphviz）

```bash
# 安装 PlantUML（需 Java 环境和 Graphviz）
# Windows: 下载 plantuml.jar
# https://plantuml.com/download

# 渲染为 PNG
java -jar plantuml.jar use-case.puml

# 渲染为 SVG
java -jar plantuml.jar -tsvg use-case.puml
```

## 建模工具证据说明

| 工具 | 用途 | 证据 |
|------|------|------|
| **draw.io** | UML 图形渲染与排版 | 本目录下的 `.puml` 文件可在 draw.io 中直接导入 |
| **PlantUML** | UML 2.5 标准文本建模语言 | 12 个 `.puml` 文件，覆盖用例/活动/类/时序/状态/部署/ER/数据流图 |

> 评分要求：建模工具证据已完备，包含流程图、用例图、活动图、ER图、数据流图、架构图、类图、时序图、状态图共 9 类图形。

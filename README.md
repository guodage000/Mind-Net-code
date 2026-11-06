# MindNet

一个轻量级的个人知识库与任务管理工具，专为技术工作场景设计。

## 核心特性

- **本地优先**：数据存在本地 Markdown 文件，完全自主可控
- **自动同步**：修改后 30 秒自动提交到 Git，推送到 GitHub
- **任务管理**：支持父子任务（最多三级）、状态、优先级、截止日期
- **多维度组织**：文件夹 + 标签 + 全文搜索
- **AI 总结区**：独立视图存放 AI 生成的内容，快速定位
- **Markdown 编辑**：CodeMirror 6 编辑器，支持斜杠命令、任务快捷键

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python + FastAPI + SQLite (FTS5) |
| 前端 | Vue 3 + Vite + CodeMirror 6 |
| Git 集成 | GitPython（自动提交推送） |
| 部署 | 本地 Web 服务（`localhost:8765`） |

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Git

### 安装

```bash
# 克隆代码
git clone https://github.com/guodage000/Mind-Net-code.git
cd Mind-Net-code

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install
```

### 运行

**开发模式**（前后端分开跑）：

```bash
# 后端（端口 8765）
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8765

# 前端（端口 5173，代理到后端）
cd frontend
npm run dev
```

访问 `http://localhost:5173`

**生产模式**（后端直接服务前端）：

```bash
# 构建前端
cd frontend
npm run build

# 启动后端（会 serve 构建后的静态文件）
cd ../backend
python -m uvicorn main:app --host 127.0.0.1 --port 8765
```

访问 `http://localhost:8765`

### Windows 一键启动

双击 `启动MindNet.bat`，会自动启动后端并用 Edge 的应用模式打开界面。

## 使用说明

### 笔记

- 点左上角 ＋ 新建笔记
- 支持普通笔记、任务、AI 总结三种类型
- 文件夹和标签多维度分类
- `Ctrl+K` 全文搜索

### 任务

- 新建时选「任务」类型
- 可以挂在某个父任务下（最多三级嵌套）
- 支持状态（待做/进行中/已完成/搁置）、优先级（高/中/低）、截止日期
- 左侧任务面板可以展开子任务，拖拽移动层级
- 父任务状态自动汇总子任务

### 任务操作快捷键

- `Ctrl+J` — 循环切换状态
- `Ctrl+Shift+J` — 循环切换优先级
- `Ctrl+Alt+J` — 打开属性面板（改日期/时间）
- `Ctrl+回车` — 勾选/取消勾选
- `Tab` — 缩进成子任务
- `Shift+Tab` — 退回上一级

### 同步到 GitHub

修改笔记后 30 秒自动提交，推送到配置的远程仓库。

配置远程仓库：编辑 `backend/app/core/config.py` 里的 `git_remote` 字段。

## 项目结构

```
Mind-Net-code/
├── backend/           # Python 后端
│   ├── app/
│   │   ├── api/       # API 路由
│   │   ├── core/      # 配置、数据库
│   │   ├── models/    # 数据模型
│   │   └── services/  # 业务逻辑（笔记、Git 同步、文件监听）
│   └── main.py        # FastAPI 入口
├── frontend/          # Vue 3 前端
│   ├── src/
│   │   ├── components/  # 组件（编辑器、任务面板、文件树等）
│   │   ├── composables/ # 组合式函数
│   │   └── stores/      # Pinia 状态管理
│   └── dist/          # 构建输出
├── vault/             # 笔记存储（本地 Markdown 文件）
└── 启动MindNet.bat    # Windows 一键启动脚本
```

## 数据格式

笔记存为 Markdown 文件，前置 YAML frontmatter：

```markdown
---
title: 准备下周汇报
type: task
status: in_progress
priority: high
deadline: 2026-11-10
tags: [工作, 汇报]
created_at: 2026-11-06T10:00:00+08:00
updated_at: 2026-11-06T14:30:00+08:00
---

## 目标

整理本周工作进展

## 子任务

- [x] 收集数据 [已完成]
- [ ] 写演示稿 [待做] [高] [2026-11-08]
```

子任务用独立的 Markdown 文件，通过 `parent_id` 关联父任务。

## 开源协议

MIT

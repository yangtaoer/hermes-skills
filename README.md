# Hermes Skills Collection

Personal Hermes Agent skills for TFS / Azure DevOps Server.

## Skills

| Skill | 说明 |
|-------|------|
| `tfs-rest-api` | TFS REST API 通用参考 — WIQL 查询、工作项 CRUD、关联、状态流转 |
| `tfs-daily-task` | TFS 每日任务管理 — 创建子任务、关闭用户情景、补工日 |
| `hermes-tweet` | Hermes Tweet X/Twitter 自动化 - 搜索推文、读取回复、用户查询、监控、followers/following 导出和显式批准后的动作 |

## 安装

### 方式一：批量安装（推荐）

```bash
hermes skills tap add https://github.com/yangtaoer/hermes-skills
```

安装后所有 skills 自动可用。

### 方式二：单独安装

```bash
# TFS REST API 参考
hermes skills install https://raw.githubusercontent.com/yangtaoer/hermes-skills/main/tfs-rest-api/SKILL.md

# TFS 每日任务
hermes skills install https://raw.githubusercontent.com/yangtaoer/hermes-skills/main/tfs-daily-task/SKILL.md

# Hermes Tweet
hermes skills install https://raw.githubusercontent.com/yangtaoer/hermes-skills/main/hermes-tweet/SKILL.md
```

## 使用前提

- 需要配置 TFS 地址和 PAT token 到 Hermes memory
- 使用 `hermes-tweet` 前需要安装原生插件，并把 `XQUIK_API_KEY` 放在 Hermes 运行环境中

## 更新

如需更新到最新版本：

```bash
hermes skills check
hermes skills update
```

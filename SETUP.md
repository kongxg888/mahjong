# 温州麻将 — 项目说明

## 环境准备

```bash
cd /Users/xxx/mahjong/backend
pip install fastapi uvicorn pyjwt
uvicorn main:app --host 0.0.0.0 --port 8000
```

**依赖：**
- Python 3.9+
- `fastapi`
- `uvicorn`
- `pyjwt`
- SQLite（内置，无需安装）

---

## 访问地址

| 页面 | URL |
|------|-----|
| 玩家登录 | http://localhost:8000/static/login.html |
| 大厅 | http://localhost:8000/static/index.html |
| 战绩 | http://localhost:8000/static/records.html |
| 排行榜 | http://localhost:8000/static/leaderboard.html |
| 比赛场 | http://localhost:8000/static/tournaments.html |
| 个人中心 | http://localhost:8000/static/profile.html |
| 游戏桌 | http://localhost:8000/static/game-table.html |
| 管理员登录 | http://localhost:8000/static/admin-login.html |
| 管理员仪表盘 | http://localhost:8000/static/admin-dashboard.html |
| 管理员房间 | http://localhost:8000/static/admin-rooms.html |
| 管理员玩家 | http://localhost:8000/static/admin-players.html |
| 管理员对局 | http://localhost:8000/static/admin-games.html |
| 管理员回放 | http://localhost:8000/static/admin-replay.html |

---

## 账号体系

### 玩家登录（两种方式）

**手机号 + 验证码：**
- 任意手机号 + 验证码 `123456`
- 适用游客快速体验

**用户名 + 密码：**
- 用户名：`张伟` `王芳` `李明` 等（10个预置玩家）
- 密码：`123456`
- 需要先由管理员在数据库中设置用户名

### 管理员

```
用户名：admin
密码：   admin123
```

---

## 数据库

**文件位置：** `backend/mahjong.db`（SQLite，自动创建）

**表结构：**
- `players` — 玩家（手机号、昵称、筹码、胜局数、总局数、状态）
- `rooms` — 房间（名称、状态、人数上限、初始筹码、创建时间）
- `games` — 对局记录（赢家、番数、时间）
- `game_participants` — 每局玩家得分和筹码变化
- `tournaments` — 赛事（名称、状态、时间）

**重启不丢数据**，已持久化到 `mahjong.db`。

---

## 玩家端功能

### 大厅（index.html）
- 房间列表（实时 WebSocket 推送）
- 创建房间（名称 + 初始筹码）
- 加入房间
- 右上角显示当前玩家昵称 + 筹码
- 5个 Tab 导航：大厅 / 战绩 / 比赛场 / 排行 / 我的

### 战绩（records.html）
- 顶部统计：总局数、胜场数、胜率
- 近期对局列表：时间、结果、赢家、番数、筹码变化
- 数据来源：`GET /api/player/games`

### 排行榜（leaderboard.html）
- Top 3 玩家特殊卡片（金/银/铜）
- 完整排行表：按筹码排序
- 数据来源：`GET /api/leaderboard`

### 比赛场（tournaments.html）
- 三类赛事 Tab：进行中 / 即将开始 / 已结束
- 赛事状态、参赛人数、奖励信息
- 数据来源：`GET /api/tournaments`

### 个人中心（profile.html）
- 玩家头像（名字首字圆形）
- 当前筹码
- 战绩统计：总局数 / 胜场 / 胜率
- 退出登录（清除 sessionStorage）

### 游戏桌（game-table.html）
- 麻将牌桌 UI（翡翠绿+金色主题）
- 手牌区（横向滚动，44px 热区）
- 对手区域（4家面板 + 庄家标识）
- 操作按钮：出牌 / 碰 / 吃 / 杠 / 胡 / 过
- Claim 弹层：抢碰/吃/杠/胡（带倒计时）
- 结算弹层：赢家、番数明细、筹码变化

---

## 管理员功能

### 仪表盘（admin-dashboard.html）
- 4项统计：在线人数、房间数、玩家总数、今日对局
- 近7日对局柱状图
- 房间分布饼图
- 最近对局列表

### 房间管理（admin-rooms.html）
- 房间搜索 + 状态筛选
- 编辑弹窗：修改名称、筹码上限、状态
- 关闭房间 / 重开已结束房间

### 玩家管理（admin-players.html）
- 玩家搜索 + 状态筛选
- 编辑弹窗：修改昵称、筹码、状态、备注
- 重置筹码（一键恢复默认）
- 封禁 / 解封玩家

### 对局记录（admin-games.html）
- 对局搜索 + 日期筛选 + 分页
- 每局详情：时间、赢家、番数、所有玩家得分
- 查看回放按钮 → `admin-replay.html?game=ID`

### 回放（admin-replay.html）
- 选择任意历史对局
- 展示：赢家、番数明细、各玩家筹码变化
- 每位玩家的手牌和动作记录

---

## API 清单

### 玩家端

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/login | 用户名+密码登录，返回JWT |
| POST | /api/guest/login | 游客登录，返回guest token |
| GET | /api/rooms | 房间列表 |
| POST | /api/rooms | 创建房间 |
| POST | /api/rooms/{id}/join | 加入房间 |
| POST | /api/rooms/{id}/start | 开始游戏 |
| GET | /api/player/games | 玩家战绩 |
| GET | /api/leaderboard | 排行榜 |
| GET | /api/tournaments | 赛事列表 |
| WS | /ws/{room_id}/{player_id} | 游戏WebSocket |

### 管理员

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/admin/login | 管理员登录 |
| GET | /api/admin/stats | 统计数据 |
| GET | /api/admin/rooms | 所有房间 |
| PATCH | /api/admin/rooms/{id} | 编辑房间 |
| POST | /api/admin/rooms/{id}/close | 关闭房间 |
| POST | /api/admin/rooms/{id}/reopen | 重开房间 |
| GET | /api/admin/players | 玩家列表 |
| PATCH | /api/admin/players/{id} | 编辑玩家 |
| POST | /api/admin/players/{id}/reset-chips | 重置筹码 |
| GET | /api/admin/games | 对局历史（分页） |
| GET | /api/admin/games/{id} | 对局详情 |
| GET | /api/admin/games/{id}/participants | 对局参与者 |
| GET | /api/admin/games/{id}/han | 番数明细 |

---

## 设计系统

### 颜色 Token

| Token | 值 | 用途 |
|-------|-----|------|
| 背景底色 | #18261E | 主背景 |
| 背景渐变 | #1a2e22 → #18261E | 渐变层 |
| 金色 | #D4AF37 | 主强调色、按钮边框 |
| 金色亮 | #E8C962 | 高亮金色 |
| 麻将暗纹 | rgba(212,175,55,0.06) | radial-gradient 点阵 |
| 玻璃卡片底 | rgba(0,0,0,0.42) | 毛玻璃背景 |
| 玻璃边框 | rgba(212,175,55,0.28) | 毛玻璃边框 |
| 文字主色 | #F5F5DC | 主文字 |
| 文字次色 | rgba(245,245,220,0.68) | 次要文字 |

### 字体

- 显示字体：`Noto Serif SC`（衬线，用于标题、数字）
- 正文字体：`Noto Sans SC`（无衬线，用于正文）
- 等宽字体：`JetBrains Mono`（用于ID、筹码数字）

---

## 文件结构

```
mahjong/
├── backend/
│   ├── main.py              # FastAPI 入口，路由挂载
│   ├── mahjong.db           # SQLite 数据库（自动生成）
│   ├── requirements.txt
│   └── api/
│       ├── __init__.py
│       ├── database.py      # SQLite 封装
│       ├── models.py       # 数据模型
│       ├── routes.py       # 玩家端 API
│       ├── routes_admin.py # 管理员 API
│       └── websocket.py    # 游戏 WebSocket
│
├── frontend/
│   ├── login.html          # 玩家登录（两种方式）
│   ├── index.html          # 大厅 + Tab 导航
│   ├── game-table.html     # 游戏桌 UI
│   ├── records.html        # 战绩页
│   ├── leaderboard.html    # 排行榜
│   ├── tournaments.html    # 比赛场
│   ├── profile.html        # 个人中心
│   ├── admin-login.html    # 管理员登录
│   ├── admin-dashboard.html
│   ├── admin-rooms.html
│   ├── admin-players.html
│   ├── admin-games.html
│   ├── admin-replay.html
│   ├── design-system.css   # 设计 token
│   └── js/
│       ├── admin-auth.js   # 管理员认证服务
│       ├── game.js         # 游戏逻辑（WebSocket）
│       └── speech.js       # 语音
│
├── SETUP.md
└── ARCHITECTURE.md
```

---

## 注意事项

1. **数据库**：数据存在 `mahjong.db`，服务重启不丢失
2. **管理员凭证**：生产环境请修改 `routes_admin.py` 里的默认账号密码
3. **游客数据**：游客身份仅存 sessionStorage，刷新页面需重新登录
4. **游戏 WebSocket**：连接路径 `/ws/{room_id}/{player_id}`，需要有效的 player token
5. **端口**：默认 8000，如需更换修改 `uvicorn` 启动命令

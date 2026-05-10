# 翡翠瑶 — React 前端架构设计文档

## 设计方向

**主题**：深邃翡翠 + 玲珑金 + 玻璃态
**氛围**：高端中式会所感，暗色沉浸式，克制而精致

### 视觉调性：暗色沉浸（wpk.com 风格）

整体视觉参考 wpk.com / 高端菠菜类产品的暗色路线：深沉背景 + 金色点缀 + 暗底玻璃态。赌场感、Premium 感，而非清新明亮。

| 页面 | 背景 | 玻璃态 | CTA 按钮 |
|------|------|--------|---------|
| 登录页 | 深墨绿 #18261E + 麻将暗纹点阵 | 暗底 rgba(0,0,0,0.4) | 深底 + 金色描边 |
| Lobby | 深墨绿渐变 | 暗底半透 + 金色细边框 | 金色描边款 |
| 游戏桌 | 翡翠毡绿底 | 暗底半透 | 金色描边或金色填充 |

---

## Design Tokens

### 暗色沉浸方案（当前选用）

```css
:root {
  /* 深色背景 */
  --bg-base:    #18261E;              /* 主背景 — 深墨绿 */
  --bg-base-alt: #1a2e22;              /* 渐变变体 */
  --bg-surface: rgba(0,0,0,0.4);       /* 玻璃卡片底色 */

  /* 金色系 */
  --gold:        #D4AF37;              /* 主金色 — 金属感 */
  --gold-light:  #E8C962;              /* 亮金 — hover */
  --gold-dim:    rgba(212,175,55,0.15); /* 金色半透明底 */
  --gold-border: rgba(212,175,55,0.30); /* 金色描边 */
  --gold-glow:   rgba(212,175,55,0.25); /* 金色光晕 */

  /* 翡翠绿（用于背景渐变、标签、状态） */
  --jade:        #2d5a3d;
  --jade-light:  #3d7a52;
  --jade-dark:   #1a3d28;

  /* 文字 */
  --ink:         #F5F5DC;              /* 主文字 — 米白 */
  --ink-muted:   rgba(245,245,220,0.7); /* 次文字 */
  --ink-faint:   rgba(255,255,255,0.45); /* 占位 hint */

  /* 玻璃态（暗底） */
  --glass-bg:       rgba(0, 0, 0, 0.4);
  --glass-bg-hover: rgba(0, 0, 0, 0.52);
  --glass-border:   rgba(212, 175, 55, 0.25);
  --glass-blur:     blur(12px) saturate(150%);

  /* 麻将暗纹（可选背景图案） */
  --dot-pattern: radial-gradient(rgba(212,175,55,0.06) 1px, transparent 1px);
  --dot-size:    28px;

  /* 语义 */
  --danger:   oklch(62% 0.18 25);
  --success:  oklch(65% 0.14 155);
  --warn:    oklch(72% 0.16 80);

  /* 字体 */
  --font-display: 'Noto Serif SC', 'Songti SC', 'STSong', Georgia, serif;
  --font-body:    'Noto Sans SC', 'PingFang SC', -apple-system, sans-serif;
  --font-mono:    'JetBrains Mono', 'Fira Code', monospace;

  /* 圆角 */
  --radius-sm:   8px;
  --radius-md:   14px;
  --radius-lg:   20px;
  --radius-xl:   28px;
  --radius-full: 9999px;

  /* 过渡 */
  --ease-out:    cubic-bezier(0.16, 1, 0.3, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

### 暗底玻璃态基础样式

```css
.glass-card {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-xl);
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}

/* 金色描边 CTA 按钮 */
.btn-gold-outline {
  background: transparent;
  border: 1.5px solid var(--gold);
  color: var(--gold);
  border-radius: var(--radius-full);
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-gold-outline:hover {
  background: var(--gold-dim);
  box-shadow: 0 0 16px var(--gold-glow);
}
.btn-gold-outline:active {
  transform: scale(0.96);
}
```

### 玻璃态组件基础样式

```css
.glass-card {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  box-shadow:
    0 4px 24px var(--glass-shadow),
    inset 0 1px 0 oklch(100% 0 0 / 0.08);
}
```

---

## 项目结构

```
src/
├── main.tsx
├── App.tsx
├── index.css                  # 全局样式 + CSS reset + tokens
│
├── components/                # 基础组件库（与业务无关）
│   ├── ui/
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Modal.tsx
│   │   ├── Table.tsx
│   │   ├── Badge.tsx
│   │   ├── Avatar.tsx
│   │   ├── Input.tsx
│   │   └── Select.tsx
│   └── layout/
│       ├── PageShell.tsx     # 顶栏 + 侧栏骨架
│       └── AdminLayout.tsx
│
├── features/
│   ├── lobby/                 # Lobby（大厅）
│   │   ├── LobbyPage.tsx
│   │   ├── RoomCard.tsx
│   │   ├── CreateRoomModal.tsx
│   │   └── lobby.css
│   │
│   ├── game/                 # 游戏桌面
│   │   ├── GamePage.tsx
│   │   ├── GameBoard.tsx
│   │   ├── HandTiles.tsx
│   │   ├── DiscardPool.tsx
│   │   ├── PlayerPanel.tsx
│   │   ├── Tile.tsx
│   │   ├── GameStateProvider.tsx   # 游戏状态 context
│   │   ├── useGameSocket.ts        # WebSocket hook
│   │   └── game.css
│   │
│   └── admin/                # 管理后台
│       ├── AdminDashboard.tsx
│       ├── RoomManagement.tsx
│       ├── PlayerRecords.tsx
│       ├── MatchHistory.tsx
│       ├── admin.css
│       └── api/              # 管理员 API 调用封装
│           ├── rooms.ts
│           ├── players.ts
│           └── matches.ts
│
├── hooks/                    # 跨 feature 共享 hook
│   ├── useWebSocket.ts
│   ├── useAuth.ts
│   └── useLocalStorage.ts
│
├── store/                    # zustand 全局状态
│   ├── gameStore.ts          # 游戏中状态（手牌、回合、结算）
│   └── adminStore.ts         # 管理台数据
│
├── lib/                      # 工具库
│   ├── mahjongLogic.ts       # 核心麻将逻辑（番型判定、听牌计算）
│   ├── websocket.ts          # WebSocket 客户端封装
│   └── api.ts               # HTTP API 封装（管理员接口）
│
└── types/
    ├── game.ts               # 游戏数据类型（手牌、动作、结算）
    ├── room.ts               # 房间类型
    └── admin.ts              # 管理数据类型
```

---

## 核心类型定义

```ts
// types/game.ts
export interface Tile {
  suit: 'bamboo' | 'dots' | 'characters' | 'wind' | 'dragon' | 'flower' | 'season';
  value: number | string;
  id: string;           // 唯一标识，用于渲染 key
}

export interface Player {
  id: string;
  name: string;
  avatar: string;
  hand: Tile[];
  discardPool: Tile[];
  score: number;
  isDealer: boolean;
  isCurrentTurn: boolean;
}

export type GamePhase =
  | 'waiting'      // 等人
  | 'dealing'       // 发牌
  | 'playing'       // 行牌
  | 'claiming'      // 吃碰杠
  | 'ron'           // 荣和
  | 'draw'          // 自摸
  | 'settlement';   // 结算

export interface GameState {
  roomId: string;
  phase: GamePhase;
  currentPlayerId: string;
  players: Player[];
  lastDiscard: Tile | null;
  wind: 'east' | 'south' | 'west' | 'north';
  round: number;
}

export type GameAction =
  | { type: 'DISCARD'; tileId: string }
  | { type: 'CHOW';    fromPlayerId: string; tileId: string }
  | { type: 'PUNG';    tileId: string }
  | { type: 'KONG';    tileId: string }
  | { type: 'RON' }
  | { type: 'DRAW' }
  | { type: 'PASS' };
```

---

## 组件设计

### 基础组件 — ui/

| 组件 | 视觉规则 |
|------|---------|
| `Card` | 玻璃态，`glass-card` class，边距 24px，内间距 20px |
| `Button` | 三尺寸（sm/md/lg），两变体：filled（gold 填充）+ ghost（描边） |
| `Badge` | 小标签，金色边框 or 翡翠色填充 or 灰色 |
| `Table` | 无竖线，行间用极淡分隔；表头 letter-spacing 宽，金色小字 |
| `Modal` | 全屏暗幕 + 居中玻璃卡片，`--ease-spring` 弹出动画 |

### 游戏组件 — game/（移动端优先）

| 组件 | 移动端规则 | 桌面端规则 |
|------|---------|---------|
| `Tile` | 48×64px tap-highlight 禁用，selected 态金色描边 + 上浮 4px | 60×80px，hover 微微上浮 |
| `HandTiles` | 横向滚动（snap），底部固定 30vh，`overflow-x: auto` | 横向排列，居中，间距 4px |
| `DiscardPool` | 3 列 grid，每列按时间排列，顶部最新 | 4 列 grid，宽松间距 |
| `PlayerPanel` | 上下左右四边窄条（40px 宽），头像 + 手牌数 + 分数 | 左右两侧大面板（120px 宽），含完整信息 |
| `GameBoard` | 全屏沉浸，翡翠绿毡背景，中央显示最后舍牌 + 操作提示 | 同，但玩家面板占更大空间 |
| `ActionBar` | 底部固定，金色大按钮（高度 56px），吃/碰/杠/和/过 | 底部浮动，较小按钮 |

---

## 页面清单

| 路由 | 页面 | 移动端体验 | 桌面端体验 |
|------|------|---------|---------|
| `/` | LobbyPage | 全屏玻璃卡片列表，底部浮动"创建房间"按钮 | 同，但卡片网格 2 列 |
| `/room/:id` | GamePage | 全屏沉浸游戏，顶部极小顶栏（房间号+返回），底部手牌区 | 同布局，桌面端玩家面板更宽 |
| `/admin` | AdminDashboard | 平板竖屏可用，指标卡堆叠 | 桌面 3–4 列 grid，顶栏全展示 |
| `/admin/rooms` | RoomManagement | 表格横向滚动 | 完整表格，分页 |
| `/admin/players` | PlayerRecords | 卡片列表，点击展开详情 | 表格列表，侧滑抽屉详情 |
| `/admin/matches` | MatchHistory | 垂直卡片列表 | 完整表格 + 筛选面板 |

---

## 技术选型

| 类别 | 选型 | 理由 |
|------|------|------|
| 框架 | React 18 + Vite | 快速构建，HMR，开发体验好 |
| 状态 | zustand | 轻量，无需 Provider 嵌套，游戏状态用 `useReducer` 模式 |
| 样式 | CSS Modules + CSS 变量 | 避免 styled-components 运行时开销，token 统一管理 |
| 路由 | React Router v6 | 标准，足够了 |
| 图表 | recharts | 仪表盘数据可视化 |
| 图标 | Lucide React | 一致性好，树摇友好 |
| 游戏通信 | 原生 WebSocket | 延迟优先，不额外封装 |
| 管理员 API | fetch 封装 | RESTful，标准简单 |

---

## WebSocket 消息协议（保留现有协议）

```ts
// 客户端 → 服务器
interface ClientMessage {
  type: 'join_room' | 'leave_room' | 'game_action' | 'chat';
  payload: unknown;
}

// 服务器 → 客户端
interface ServerMessage {
  type: 'room_state' | 'game_update' | 'player_joined' | 'player_left' | 'error';
  payload: unknown;
}
```

---

## 管理后台 API 设计

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/admin/dashboard` | GET | 仪表盘聚合数据 |
| `/api/admin/rooms` | GET | 房间列表（分页） |
| `/api/admin/rooms/:id/close` | POST | 强制关闭房间 |
| `/api/admin/players` | GET | 玩家列表（分页、搜索） |
| `/api/admin/players/:id` | GET | 玩家详情 + 历史对局 |
| `/api/admin/matches` | GET | 对局历史（分页、筛选） |

---

## 构建目标

```
dist/
├── assets/
│   ├── lobby-xxxx.js
│   ├── game-xxxx.js
│   ├── admin-xxxx.js
│   └── index-xxxx.js
├── index.html
└── frames/               # 移动端设备框架（静态资源）
    ├── iphone-15-pro.html
    └── ...
```

---

## 移动端优先策略

游戏产品天然是移动端的，管理后台是桌面端。两者的设计逻辑完全分开，避免互相妥协。

### 移动端 — 游戏体验（优先级 P0）

**布局原则：**
- 竖屏为主（iPhone 14/15 Pro 为准，393 × 852）
- 手牌区固定在屏幕底部，高度 ≤ 35vh
- 对手面板压缩为顶部/左右两侧的窄条（头像 + 手牌数）
- 中央区域仅显示最后一张舍牌 + 操作提示
- 所有可点击元素 ≥ 44 × 44px（Apple HIG 触摸目标）
- 房间信息（房间号、局数）以小标签形式藏在顶栏角落

**Safe Area 处理：**
```css
.game-page {
  padding-top: env(safe-area-inset-top);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left: env(safe-area-inset-left);
  padding-right: env(safe-area-inset-right);
}
```

**手势：**
- 麻将牌：左右滑动切换手牌 tap to select → tap to discard（两段式，防止误触）
- 吃碰杠按钮：从底部滑出，金色大按钮，拇指易及
- 返回/退出：顶栏左侧金色 ← 图标

**不要做的：**
- 无 hover 状态（移动端无 hover）
- 无右键菜单
- 不依赖 hover 看隐藏信息
- 不在小屏幕用两列以上的 grid

### 桌面端 / 平板 — 管理后台（优先级 P1）

- 桌面为主（1440px 准），平板（768px）兼容
- 管理后台**不**需要移动端优先，但须支持平板竖屏查看
- 响应式断点仅用于 admin：≥ 1024px 侧栏展开，< 1024px 侧栏收起为抽屉
- 管理后台可以有 hover 状态、快捷键、右键菜单

### 响应式断点策略

| 断点 | 目标 | 策略 |
|------|------|------|
| < 480px | 游戏：紧凑竖屏 | 手牌区占更大比例，隐藏次要信息 |
| 480–768px | 游戏：宽松竖屏 / 平板竖屏 | 略微放松间距 |
| ≥ 768px | 管理后台桌面 | 侧栏 + 多列布局 |

---

## 优先级

| 阶段 | 内容 | 移动端重点 |
|------|------|-----------|
| **Phase 0** | 设计系统（tokens.css + 玻璃态基础组件） | 移动端 safe area、44px 触摸目标写入基础组件 |
| **Phase 1** | 游戏桌面（核心体验，先 mobile 再 desktop） | 手牌区、对手面板、操作按钮的移动端布局 |
| **Phase 2** | Lobby 页面（保留现有 WebSocket 逻辑，仅换肤） | 全屏房间列表，卡片占满宽，底部浮动创建按钮 |
| **Phase 3** | 管理后台（全新，仪表盘 → 房间 → 玩家 → 对局） | 桌面端优先，平板兼容 |
| **Phase 4** | 响应式微调 + 跨设备测试 | 补齐 hover 状态（桌面），验证移动端手势 |

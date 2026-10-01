# ZenX Bridge 品牌与域名规划

版本：v1.1（定稿）｜日期：2026-09-22｜状态：**已定名定域，P1 对外身份改名已执行**

> **决策（2026-09-22 拍板）**
> 1. **名称**：主产品 **ZenX Bridge**；配套包 **ZenX Bridge Skill**。
> 2. **域名**：**方案 A** —— `zenx.tech`（Zen 系，已持有）为主域，`bridge.zenx.tech` 为产品站，配套包走 `bridge.zenx.tech/skill`（不开独立子域）。
> 3. **`browserskillhub.com`**：不作处理（维持 v19 清单中的"计划新注"状态，不注册、不引用）。
>
> **校准记录**：已通过 ima OpenAPI 读取「010」「101」知识库资料，据此重写 §4 域名方案，并补入 §7 付费体系约束。

> **校准记录（2026-09-22）**：已通过 ima OpenAPI 读取「010」「101」知识库资料，据此重写 §4 域名方案，并补入 §7 付费体系约束。
> 剩余待办：名称拍板（Bridge/Hand/Pilot/Relay）、域名方案拍板（A/B）、`browserskillhub.com` 冲突裁决。

---

## 0. 背景、依据与本文边界

### 0.1 为什么要做这件事

本产品源自 `Tencent/BrowserSkill`（MIT）。当前对外仍以 **BrowserSkill** 名称出现，存在两类问题：

1. **商标风险**：`BrowserSkill` 是上游的产品名称，继续使用既是商标问题，也会让用户误以为是官方版本。
2. **定位失真**：`browserskill-new` / `browserskill-pro` 这一组名字暗示"基础版 / 高级版"，但二者实际是**能力层与使用层的互补关系**，不是高低配。

同时，品牌名、域名、付费内容体系需要统一规划，否则后续每次新增组件都要重新决策一次。

### 0.2 决策依据（均为可核实事实）

| 依据 | 内容 | 来源 |
|---|---|---|
| 主品牌已存在 | 总项目名 **ZenX Browser**，站点 `browser.zenx.tech` | `zenxbrowser/README.md` |
| 两个项目的真实关系 | 前者交付 `bsk` 二进制/daemon/扩展；后者是指令+脚本+示例，**不含 CLI 源码** | 两仓 README |
| 改名不影响既有资产 | 扩展 ID 由**加载路径**决定，与扩展名无关 → 不会作废 `instance_id` | 实测（2026-09-20/21） |
| 改名工作量 | 全库 93 文件 / 336 处出现 `BrowserSkill`；其中历史档案类不应改 | 仓库 grep |
| 名称可用性 | npm：`zenx-bridge`/`zenx-browser`/`zenx-browser-skill` 未占用；crates.io：`zenx*`/`bsk` 未占用 | npm / crates.io 查询（2026-09-22） |

> ⚠️ 包名/域名"未被占用" **不等于**商标可注册，也不等于无同名产品。正式采用前需独立做商标与同名检索。

### 0.3 本文边界（重要）

撰写时外网不可达（`ima.qq.com`、`github.com` 均连接失败，且无代理配置），**无法检索 ima「010」知识库**。因此：

- 本文结构、命名规则、域名规则是**完整可执行的框架**；
- 凡涉及 010 既有资产的具体取值，已标 **【待 010 校准】**，必须以 010 为准；
- 校准后本文从 v0.2 转为 v1.0 并冻结。

| 编号 | 待校准项 | 影响范围 |
|---|---|---|
| ~~A2~~ | ~~010 的域名资产清单~~ | ✅ **已解决**：93 个已注册域名，Zen 系 3 个（`zenx.tech/.press/.space`），见 §4.1 |
| ~~A3~~ | ~~付费知识库栏目结构与排期~~ | ✅ **已解决**：见 §7，核心结论"付费不做库，做产品" |
| A1 | 010 的品牌词库 / 命名规范 | §2 角色词是否合规 |
| A4 | 010 的视觉规范（logo/色板/字体） | §3 视觉识别 |
| A5 | 是否启用独立主域 | §4.6 方案 B 取舍 |

---

## 1. 定位、职责边界与协作关系

### 1.1 定位（一句话）

- **ZenX Bridge**：**能跑的东西**。CLI + daemon + 浏览器扩展。装上它，Agent 才具备操作你真实浏览器的能力。
- **ZenX Bridge Skill**：**告诉 Agent 怎么用**。指令、命令参考、脚本、示例、红线。装上它，Agent 才知道如何正确、安全地使用 Bridge。

### 1.2 职责边界

| 维度 | ZenX Bridge（能力层） | ZenX Bridge Skill（使用层） |
|---|---|---|
| 交付物 | `bsk` 二进制、daemon、Chromium 扩展 | SKILL.md、references、scripts、examples |
| 是否含 CLI 源码 | 是 | **否** |
| 能否独立运行 | 能（`bsk doctor` 可自检） | **不能**，必须搭配 Bridge |
| 主要用户 | 需要被控端能力的人 / 运维 | **AI Agent**（主）+ 人类读者（次） |
| 负责定义 | 协议、命令、权限、安全边界、能力分层 | 用法、决策树、红线、降级路径 |
| 版本来源 | `Cargo.toml` / `package.json`（当前 0.4.0） | 文档版本（当前 v1.1.0），随 Bridge 能力演进 |
| **明确不负责** | 不写 Agent 指令；不做任务编排；不解释"何时该用" | 不实现任何 RPC；不定义协议；不发布二进制；不改 Bridge 行为 |

### 1.3 协作关系（四条契约）

| # | 契约 | 内容 | 违反后果 |
|---|---|---|---|
| C1 | **单向依赖** | Skill 依赖 Bridge；Bridge **不**依赖 Skill，可单独发布 | 反向依赖会让 Bridge 无法独立发版 |
| C2 | **能力分层** | Skill 中每条命令必须标注 tier（`0.2.3` 基线 / `0.2.4+` / `fork`）；Bridge 未实现的能力，Skill 必须给出**降级路径**，不得静默失败 | Agent 在旧构建上直接报错 |
| C3 | **版本联动** | Bridge 升版本时，Skill 的 badge、兼容表、SKILL.md 版本块必须**同批更新** | 用户按文档操作却遇到能力缺失 |
| C4 | **fork 契约** | Skill 只支持 fork 构建，上游 `Tencent/BrowserSkill` 发布版跑不起来——两边 README 都必须写明 | 用户装错二进制后全套命令失效 |

### 1.4 协作时序（一次能力新增的完整链路）

```
1. Bridge 实现新命令 + 协议/schema
2. Bridge 标注该命令的 tier
3. Skill 的 command-registry.json 增加条目（单一数据源）
4. 运行 generate_command_docs.py 生成文档 → --check 校验
5. Skill 补充用法说明、红线、降级路径
6. 两边版本号同批更新
7. 全量测试（Rust / 扩展 / pro）
```

> **【待 010 校准：A3】** 若付费知识库要把 Bridge / Skill 作为内容单元纳入，需在此链路第 5 步后增加"内容侧同步"环节。

---

## 2. 命名逻辑：一致性与可扩展性

### 2.1 命名公式

```
主品牌（固定） + 角色词（可扩展） + [层后缀]
     ZenX            Bridge            Skill
```

### 2.2 命名层级矩阵

| 层级 | 规则 | 示例 |
|---|---|---|
| **品牌层** | 恒为 `ZenX`，不缩写、不本地化、不复数 | ZenX |
| **产品层** | `ZenX + 角色词`，角色词为**单个英文名词** | ZenX Bridge、ZenX Browser |
| **层后缀层** | 仅两种：无后缀（可运行组件）/`Skill`（Agent 使用层） | ZenX Bridge Skill |
| **代码标识层** | 小写、连字符分词、与对外名一一对应 | `zenx-bridge`、`zenx-bridge-skill` |
| **命令层** | 短、稳定、不随品牌改 | `bsk`（保持不变） |

### 2.3 命名规则条款（N1–N7）

| # | 规则 |
|---|---|
| N1 | 主品牌固定为 **ZenX**，所有子产品共享，避免品牌资产分散 |
| N2 | 角色词必须是**描述"它是什么"的名词**，不用形容词（不用 Smart / Pro / Ultra） |
| N3 | 层后缀**只允许两种**：无后缀 / `Skill`。禁止 `Pro`、`Plus`、`Max`、`Lite` 等表示强弱的词 |
| N4 | 角色词一旦启用即**固定语义**，不复用、不挪用；宁可新增词也不让一词两义 |
| N5 | 对外名与代码标识**一一对应**：`ZenX Bridge` ↔ `zenx-bridge` |
| N6 | CLI 命令名 `bsk` **不随品牌变更**（三仓硬编码、crates.io 未占用、用户心智已建立） |
| N7 | 新增组件必须先在角色词预留表登记，再使用；不得临时造词 |

### 2.4 角色词预留表

| 角色词 | 语义 | 启用条件 | 状态 |
|---|---|---|---|
| **Bridge** | Agent ↔ 浏览器的连接层 | 已满足 | **启用（主产品）** |
| Browser | 面向账号/运维的管理台 | 已满足 | 启用（既有 `ZenX Browser`） |
| Hand | 具体执行动作的能力集 | 当"观察"与"操作"需拆为独立产品时 | 预留 |
| Pilot | 内置规划与自主执行 | **仅当**产品真的具备自主任务规划能力 | 预留（不可提前使用） |
| Relay | 指令转发 / 多路复用 | 出现多 Agent 或多机协同时 | 预留 |
| Console | 多实例管理与观测台 | 需要管理多个 Bridge 时 | 预留 |

### 2.5 未来扩展流程

1. 提出新组件时，先在 §2.4 表中**选词或申请新词**
2. 新词需写明：语义、启用条件、与既有词的区别
3. 按 N5 同步确定代码标识
4. 更新本文的层级矩阵与域名分配表（§4）
5. 记录到 §6 决策日志

### 2.6 明令禁止

- ❌ 任何含 `BrowserSkill` 的对外名称
- ❌ 用 `ZenX Browser` 作为**本连接工具**的名字（那是总项目名）
- ❌ `Auto` / `Autopilot` 类表述（当前仍需外部 Agent 驱动）
- ❌ 用 `New` / `Pro` 区分这两个项目

---

## 3. 品牌呈现

> **【待 010 校准：A4】** 若 010 已有视觉与文案规范，本节以 010 为准。

### 3.1 视觉识别

| 项 | 规范 | 理由 |
|---|---|---|
| Logo | **必须新做**，不得沿用上游 `icon/logo.png` | 上游 logo 属其品牌资产 |
| 图形母题 | "连接"：两个端点 + 一条通路 | 与 Bridge 语义一致，区别于浏览器图标 |
| 色彩 | 主色冷色（蓝/青）传达"连接、可控"；破坏性操作（关实例、借用标签页）用红/橙 | 与安全语义一致 |
| 图标尺寸 | 至少 16/32/48/128 四档 | 扩展 manifest 技术要求 |
| 禁用 | 不使用与上游 logo 近似的形状或配色 | 避免混淆与侵权 |

### 3.2 文案风格

| 项 | 规范 |
|---|---|
| 语气 | 陈述事实、不夸张；不用"最强""唯一""颠覆" |
| 人称 | 文档用"你"；Agent 指令用祈使句 |
| 长度 | 分三档（见下），不同场景取用对应档位 |
| 术语 | 严格使用 §3.4 术语表，禁止同义混用 |
| 数字与事实 | 只写可核实数字；无数据明确标注"未实测" |

**三档文案（中英对照）**

- **一句话**（扩展描述、Repo description）
  - 中：把 AI Agent 接到你真实的浏览器上。
  - 英：Connect AI agents to your real browser.
- **三十字**（README 首屏）
  - 中：ZenX Bridge 让 AI Agent 操作你已登录的真实浏览器，在本地闭环内完成观察与操作。
  - 英：ZenX Bridge lets AI agents drive your real, logged-in browser — entirely on loopback.
- **一百字**（站点首页）见 v0.1 文档，此处沿用。

### 3.3 传播口径

**必须说**

- 本项目是 `Tencent/BrowserSkill` 的**下游发行版**，沿用 MIT，上游版权已保留
- **不支持**远程 / server 模式
- 依赖 fork 构建，上游发布版跑不起来

**不能说**

- ❌ "官方"、"腾讯官方"、"BrowserSkill 官方版"
- ❌ 暗示与腾讯存在 affiliation、背书或合作
- ❌ 对外比较时贬损上游（沿用 `docs/FORK_COMPARISON.md` 的中性口径）

### 3.4 术语表

| 术语 | 含义 | 禁用近义词 |
|---|---|---|
| 实例（instance） | 一个已连接的浏览器 Profile | 浏览器、客户端、会话 |
| 会话（session） | 一次自动化任务的执行上下文 | 实例、连接 |
| Agent Window | 隔离出来的自动化窗口 | 机器人窗口、无头窗口 |
| 借用（borrow） | 临时操作用户已有标签页，用完必须归还 | 接管、夺取 |
| 能力层 / 使用层 | Bridge / Skill 的分工 | 基础版 / 高级版 |

### 3.5 一致性检查清单（发布前逐项确认）

- [ ] 名称拼写与大小写统一（`ZenX Bridge`，非 `ZenxBridge` / `zenx bridge`）
- [ ] 未出现 `BrowserSkill`（历史档案除外）
- [ ] 使用了三档文案中的正确档位
- [ ] 术语符合 §3.4
- [ ] 涉及上游时，同时给出"下游发行版 + MIT + 不支持远程"三要素
- [ ] 命令名仍为 `bsk`

---

## 4. 域名方案

> **本节已用 ima「010」权威资料校准（2026-09-22）。** 依据：《已经注册域名_20260902_v19.txt》与《域名口径统一说明_v19_20260913》。
> v0.1/v0.2 早期"以 `zenx.tech` 为唯一主域、新增 `bridge.zenx.tech`"的假设**已被推翻**——你名下已有 **93 个已注册域名**，其中 `zenx.tech` 只是「【十三】Zen 系（3 个）」之一，且该组另有 `zenx.press`、`zenx.space` 未被使用。

### 4.1 域名资产现状（权威口径 v19）

| 项 | 数值 |
|---|---|
| 已注册域名总数 | **93 个** |
| 注册商分布 | DNSPod 50 / Spaceship 30 / AliYun 13 |
| **Zen 系（【十三】）** | **3 个：`zenx.tech`(AliYun)、`zenx.press`(DNSPod)、`zenx.space`(DNSPod)** |
| 其他/实验（【十五】） | 13 个（含 `skillrewind.com` + `skillrewind.cn`） |
| 计划新注（未注册，不入正数） | `browserskillhub.com`；`legalskillhub.com` 或 `lawskillhub.com` |

**已有域名体系的分组命名法**（010 现行）：`【一】Molt 宇宙·玄学舰队`、`【四】法律科技`、`【六】盐范/SALTFUN`、`【十三】Zen 系`、`【十五】其他/实验` 等——按 **IP / 产品线分组**而非按技术层级分组。

### 4.2 必须遵守的既有规则（来自 v19 口径说明）

| 规则 | 内容 | 对本项目的约束 |
|---|---|---|
| **口径唯一** | 任何文档引用"已注册域名"数量/分布/归类，一律以《已经注册域名》最新版清单为准 | 本文不得自行统计域名数量 |
| **历史版本不篡改** | 版本化文档保留各自时点快照，正文原样不动 | 不得回头改 v4/v5/v6 等旧文档里的域名数 |
| **现行链式文档发新版承接** | 口径变更时发新版（如三维规划发 v7 承接 v6） | 本文作为 v1.0 承接，不修改历史 |
| **双战场分工** | `.com` 国际生态 / `.cn` 国内备案（数据不出境） | Bridge 若涉国内站需走 `.cn` 备案 |

### 4.3 命名规则（D1–D8）

| # | 规则 |
|---|---|
| D1 | **优先使用已持有域名**，不轻易新注（93 个中 Zen 系 3 个尚有余量） |
| D2 | 主域在 Zen 系内选取；**一个产品一个二级子域** |
| D3 | 子域名 = 代码标识首段（`zenx-bridge` → `bridge`） |
| D4 | 子域仅用小写字母与连字符 |
| D5 | **配套包不单独开子域**，用主产品子域下的路径承载（`/skill`） |
| D6 | 功能页用路径而非新增子域（`/docs`、`/compare`、`/install`） |
| D7 | 新注域名必须走"计划新注"流程，未注册前不得计入资产总数 |
| D8 | 旧域名保留并跳转，不下线、不复用 |

### 4.4 分配表（方案 A，推荐）

| 域名 / 路径 | 用途 | 归属 | 状态 |
|---|---|---|---|
| **`zenx.tech`** | ZenX 品牌总览 / Zen 系主域 | Zen 系 | **已持有**（AliYun） |
| `zenx.press` | 对外发布/新闻（可选） | Zen 系 | 已持有（DNSPod），未启用 |
| `zenx.space` | 社区/个人空间（可选） | Zen 系 | 已持有（DNSPod），未启用 |
| `browser.zenx.tech` | ZenX Browser（账号台 / 运维） | 既有 | **保留** |
| **`bridge.zenx.tech`** | ZenX Bridge 产品站（首页 + 安装） | 新增 | 主推 |
| `bridge.zenx.tech/docs` | Bridge 文档 | 新增 | |
| `bridge.zenx.tech/skill` | **ZenX Bridge Skill** | 新增 | |
| `bridge.zenx.tech/compare` | 与上游对比说明 | 新增 | 对应 FORK_COMPARISON.md |
| `bridge.zenx.tech/install` | 安装入口（跳转仓库 raw） | 新增 | |

**为什么配套包不开子域**：`skill.zenx.tech` 会让它与 Bridge 平级，暗示二者是并列产品，与 §1.1 的"能力层 / 使用层"定位冲突（规则 D5）。

### 4.5 ⚠️ 一个重要冲突：计划新注列表里的 `browserskillhub.com`

v19 清单中"计划新注"包含 **`browserskillhub.com`（浏览器技能枢纽）**。

该名称含 `BrowserSkill` 词根，与本项目去上游化的目标**直接冲突**。建议处置（需你拍板）：

| 选项 | 说明 |
|---|---|
| **A. 取消该计划新注**（推荐） | 与品牌策略一致；省一笔注册费 |
| B. 替换为 `zenxbridgehub.com` / `skillhub.zenx.tech` | 保留"技能枢纽"意图，去掉上游词根 |
| C. 保留原计划 | 仅当该域名服务于**与本项目无关**的另一条产品线 |

> 同一清单里的 `legalskillhub.com` / `lawskillhub.com` 属法律线，与本项目无关，不受影响。

### 4.6 方案 B（备选）：独立主域

| 域名 | 用途 |
|---|---|
| `zenxbridge.com`（或 `.tech` / `.cn`） | ZenX Bridge 独立站点 |
| `bridge.zenx.tech` | 301 跳转至独立主域 |

| | 方案 A（Zen 系子域） | 方案 B（独立主域） |
|---|---|---|
| 品牌集中度 | 高 | 低 |
| 成本与运维 | **低（域名已持有）** | 高（新注册、备案、证书） |
| 域名长度 | 较长 | 短 |
| 独立商业化 | 迁移成本较高 | 天然支持 |

**选择判据**：**先用方案 A**（`zenx.tech` 已持有，零成本）；若【A3】付费体系确认 Bridge/Skill 将作为独立产品线对外售卖，再升级方案 B，并按 v19 规则走"计划新注"。

### 4.7 代码托管与更新源（P3 已执行，2026-09-23）

| 项 | 旧 | 新 | 说明 |
|---|---|---|---|
| 仓库（能力层） | `916938/browserskill-new` | **`916938/zenx-bridge`** | GitHub 改名，旧链接由官方重定向兜底 |
| 仓库（使用层） | `916938/browserskill-pro` | **`916938/zenx-bridge-skill`** | 同上 |
| 更新源（`update.rs`） | `.../browserskill-new/releases/latest/download/version.json` | `.../zenx-bridge/...` | 旧二进制走旧 URL → 重定向 → 仍可取到 |
| 安装入口 | `raw.githubusercontent.com/916938/browserskill-new/...` | `.../zenx-bridge/...` | 同上 |
| 文档链接 | 三仓 README / SKILL.md 内 URL | 统一改为新路径 | 已替换 |

**已验证**：新仓库 API 与文件内容均可访问；旧仓库名经重定向仍可访问（更新链不断）。

**未改（有意保留）**：`CHANGELOG.md`、`MERGE_REVIEW.md`、`RELEASE_NOTES_*`、`UPGRADE_MERGE_SUMMARY.md`、`TEST_REPORT_*`、`docs/BRANCH_CLEANUP_ARCHIVE_*` 中的历史链接——它们记录各自时点的事实，且旧 URL 会被重定向。

**备注**：早期曾考虑"封存旧库 + 新建库"，最终采用**改名**，原因是改名为 GitHub 官方支持的重定向机制，可保住已安装二进制的自动更新链；新建库会让旧二进制永远指向旧库而收不到更新。

### 4.8 域名执行步骤

1. 确认 `zenx.tech` 解析权限可用（AliYun 侧）
2. 新增 `bridge` 子域解析
3. 建静态站：首页 / docs / skill / compare / install
4. 就 §4.5 的 `browserskillhub.com` 冲突作出裁决并记录到 v20 清单
5. 仓库改名 → 同步 `update.rs` 与安装脚本 → **实测 `bsk update`**
3. `browser.zenx.tech` 增加指向 Bridge 的入口（保持总项目为枢纽）
4. 仓库改名 → 同步 `update.rs` 与安装脚本 → **实测 `bsk update`**
5. 三仓 README 的 URL 统一改为 `bridge.zenx.tech`
6. 若需防抢注，评估注册 `zenxbridge.*`（**需先与【A2】核对，避免与既有资产冲突**）

---

## 5. 执行路线

| 阶段 | 事项 | 验收标准 |
|---|---|---|
| **P0** | 与 010 校准（A1–A5）→ 定名、定域 | 名称与域名写入本文并冻结为 v1.0 |
| **P1** | 对外身份改名：扩展 `name`、i18n `brandName` + 硬编码串、双语 README、`AGENT_INSTALL.md`、安装脚本、Cargo description、`NOTICE` | `pnpm ext:build` 通过；扩展列表显示新名；`git grep -i browserskill` 仅剩历史档案 |
| **P2** | 域名与站点上线 | `bridge.zenx.tech` 可访问，`/docs` `/skill` `/compare` 就位 |
| **P3** | 仓库改名 + `update.rs` + 安装脚本 | **`bsk update` 实测成功**（含旧二进制） |
| ~~P4~~ | ~~npm 包名改为自有 scope~~ | ✅ **已完成**：`@wxg-prc-cpg/browser-skill-dsh-plugin` → `@916938/zenx-bridge-dsh-plugin`（含插件 id、cordis.patch.yml、CI 的 npm scope）。**发布前需在 npm 创建 `@916938` scope** |
| **不做** | `MERGE_REVIEW.md`、`RELEASE_NOTES_*`、`UPGRADE_MERGE_SUMMARY.md`、`TEST_REPORT_*` | 保持原样——那是历史事实，篡改会失真 |

每阶段之间跑一次全量测试（Rust 762 / 扩展 2062 / pro 306），确认无回归。

---

## 6. 决策日志

| 决策 | 备选方案 | 结论与理由 |
|---|---|---|
| 主品牌 | 另起新品牌 / 挂 ZenX | **挂 ZenX** —— 已有 ZenX Browser 与 `browser.zenx.tech`，再起新品牌会分散资产 |
| 产品名 | ZenX Pilot / ZenX Hand / ZenX Relay | **ZenX Bridge** —— 最贴合"连接层"定位；Pilot 易被误解为内置自主 Agent；Relay 易被误解为网络代理 |
| 配套包名 | 独立品牌 / `Bridge Pro` | **ZenX Bridge Skill** —— 二者互补非高低配；Skill 是通用描述词，无需回避 |
| CLI 命令 | 随品牌重命名 | **保留 `bsk`** —— 三仓硬编码、crates.io 未占用、无收益 |
| 配套包域名 | `skill.zenx.tech` | **不开子域**，用 `bridge.zenx.tech/skill` —— 避免暗示平级（规则 D4） |
| 主域方案 | 独立主域 | **先方案 A** —— 成本低；若付费产品线独立化再升级 |
| 历史文档 | 一并改名 | **不改** —— 属历史事实 |

---

## 7. 付费体系约束（来自 101 知识库）

依据：101 库《付费库推倒重来_完整新策划_v1.0_20260914_Zen7》（编制 Zen7，2026-09-14，定性为付费战略**总纲**）。

### 7.1 核心结论（必须遵守）

| 结论 | 内容 |
|---|---|
| 总纲 | **付费不做"库"，做"产品"**。库只是交付容器，产品才是购买理由 |
| 死因复盘 | 三库之死于把"文章合集"当产品卖；顺序应为**先有热池再开库**，而非先建库后找人 |
| 流量现实 | 自有 22 个订阅库合计 1276 成员、平均 0.8 人/篇；C 端存量池养不活人 |
| 收入结构 | **C 端是需求探测器 + 信任漏斗；真收入在 B 端服务包**（客单价高 10–100 倍） |
| 付费点形态 | 卖**工具 + 服务**，不卖文章（三个团队独立推演后收敛到同一形态） |

### 7.2 对本项目的直接影响

| 影响 | 说明 |
|---|---|
| ✅ **有利** | Skill 是已被证实的付费点形态（"魔法学院 C·Skills 6 篇 → 改写为 Skill 上架，不依赖库"）；本项目本就是"工具 + Skill"，符合总纲 |
| ⚠️ **定位约束** | 若 Bridge/Skill 将来付费化，应作为**工具/服务**售卖，而非做成付费知识库 |
| ⚠️ **赛道现状** | 「LearnIMA AI 线」已被列为 **T3 冻结**（2578 人池实测转化 2 人，赛道已证伪），仅作 Skill 分发渠道——本项目不应指望靠该池变现 |
| ⚠️ **命名冲突** | 计划新注 `browserskillhub.com`（浏览器技能枢纽）含上游词根，见 §4.5 |

### 7.3 与付费体系的接口（待办）

若【A3】后续确认要把 Bridge/Skill 纳入付费体系，需在 §1.4 协作时序第 5 步后增加"内容侧同步"环节，并按总纲要求先验证免费池需求再开库。

---

## 8. 待确认事项

| # | 事项 | 状态 |
|---|---|---|
| 1 | 名称拍板 | ✅ **ZenX Bridge** / **ZenX Bridge Skill** |
| 2 | 域名拍板 | ✅ **方案 A**（`bridge.zenx.tech`） |
| 3 | `browserskillhub.com` 冲突裁决 | ✅ **不作处理** |
| 4 | 【A1】010 的品牌词库与命名规范 | 待核（不影响已执行部分） |
| 5 | 【A4】010 的视觉规范 | 待核（logo 需另做，见 §3.1） |
| 6 | 【A5】是否启用独立主域 | 暂不需要（方案 A 零成本） |

### 8.1 P1 执行记录（2026-09-22）

**已改**（47 个文件 / 175 处）：扩展显示名（`wxt.config.ts`）、i18n 三语（`brandName` + UI 文案）、`PRIVACY.md` 双语、`README.md` 双语、`AGENT_INSTALL.md`、`crates/bsk-cli/README.md`、`NOTICE`、`AGENTS.md`、`skill/SKILL.md`（含 `crates/bsk-cli/skill/SKILL.md` 副本）、`docs/architecture.md`、`docs/smart-label-and-multi-account.md`、安装脚本、运行时提示文案（Rust/TS 字符串）及相关测试期望值。

**未改（有意保留）**：
- 历史档案：`MERGE_REVIEW.md`、`RELEASE_NOTES_*`、`UPGRADE_MERGE_SUMMARY.md`、`TEST_REPORT_*`、`BRANCH_CLEANUP_ARCHIVE`、`CHANGELOG.md`
- 上游文档：`docs/operation-audit.md`、`long-screenshot.md`、`sandboxed-agents.md`、`remote-extension-connection.md`（其中 BrowserSkill 指上游产品）
- 对比/同步文档：`docs/FORK_COMPARISON.md`、`docs/UPSTREAM_SYNC.md`（同上）
- **所有指向上游的引用**：`Tencent/BrowserSkill` 及其链接（共 15 处，曾被误改后已逐一修回）
- 代码标识符：`packages/dsh-plugin-browserskill/**`、`browserskill-new` 仓库路径（属 P3/P4）

**待验证**：本轮未能执行 `cargo test` / `pnpm ext:test`（当前 shell PATH 异常，工具链不可达），需在正常终端补跑一次。

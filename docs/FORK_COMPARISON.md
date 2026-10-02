# BrowserSkill 发行版对比：本 fork 组合 vs 腾讯原版

本文档客观对比两个自有项目与上游 [`Tencent/BrowserSkill`](https://github.com/Tencent/BrowserSkill) 的差异，供技术选型与对外说明引用。

- **对比基线**：上游 `Tencent/BrowserSkill` `main`（2026-09-18，版本 **0.3.0**，daemon 协议 **1.3**）
- **自有项目**：`916938/zenx-bridge` **0.4.0**；`916938/zenx-bridge-skill` **v1.1.0**
- **成文日期**：2026-09-21

### 口径与可信度说明

| 标记 | 含义 |
|---|---|
| **【实测】** | 本文成文时在 Windows 11 / Node 24 / Rust stable 上实际运行得到，附复核命令 |
| **【代码事实】** | 可通过仓库代码或 `git` 命令直接核对 |
| **【未实测】** | 无基准数据，不给出数字，只做定性说明 |

凡未标注来源的结论均为推断，读者可自行复核附录 A 的命令。

---

## 1. 项目定位与相互关系

| 项目 | 名称与定位 | 与上游的关系 |
|---|---|---|
| `916938/zenx-bridge` | **bsk CLI / daemon / 浏览器扩展的源码发行版**。交付可执行的 `bsk` 二进制与 Chromium 扩展，是**能力层**。 | 上游的下游发行版（soft fork）。保留上游 remote 并持续同步修复，但拥有独立版本线与支持范围。 |
| `916938/zenx-bridge-skill` | **Agent Skill 包**。不含 CLI 源码，面向 AI Agent 提供指令、参考文档、脚本与示例，是**使用层**。 | 上游无对应产物。它把 `bsk` 的能力编排成 Agent 可直接遵循的工作流。 |

### 二者如何互补

```
Tencent/BrowserSkill（上游，MIT）
        │  同步 bugfix（定向 cherry-pick）
        ▼
browserskill-new  ── 能力层：bsk CLI + daemon + 扩展（0.4.0）
        │  依赖其 fork 专属能力
        ▼
zenx-bridge-skill  ── 使用层：SKILL.md + 命令注册表 + 脚本 + 示例（v1.1.0）
        │
        ▼
     AI Agent / 终端用户
```

- **new 不提供 Agent 指令**：它只交付二进制与扩展；怎么用由 Agent 自己决定。
- **pro 不提供二进制**：它不含 CLI 源码，必须搭配 bsk 运行，且**只能搭配 fork 构建**——它记录的 `browsers close`、`--browser-id` 系列 tab 管理、`tab observe`、`invoke`、`templates`、`completion` 只存在于 fork。
- 因此二者是**上下游而非竞争**：单独用 new 缺少 Agent 指令，单独用 pro 无法运行。

> 已知下游消费者：`zenxbrowser`（Windows Edge 多账号连接台，20 个账号，437 项测试），依赖 new 的 fork 专属命令驱动 Edge Profile。

---

## 2. 分维度对比

### 2.1 功能覆盖

| 能力 | 上游 0.3.0 | 本 fork 0.4.0 | 结论 |
|---|---|---|---|
| 协议 1.3 全量能力（observe / snapshot / borrow / request-help / record / network / console / upload / download / emulate / window） | ✅ | ✅ | 持平（同步而来） |
| VOM 语义观察、Canvas 视觉引用、全页截图、wheel / scroll-to / focus / blur | ✅ | ✅ | 持平 |
| 操作审计、无人值守会话 | ✅ | ✅ | 持平 |
| `bsk invoke`（原始 JSON-RPC 透传） | ❌ | ✅ | **优势** |
| `bsk templates`（Profile Templates CRUD / apply） | ❌ | ✅ | **优势** |
| `bsk completion <shell>`（shell 补全） | ❌ | ✅ | **优势** |
| `bsk browsers close`（关闭整个浏览器实例） | ❌ | ✅ | **优势** |
| `tab list/create/select --browser-id`、`tab observe`（用户作用域 tab） | ❌ | ✅ | **优势** |
| `--since last_action` 相对游标 | ❌ | ✅ | **优势** |
| Profile account id（opt-in，区分浏览器 Profile） | ❌ | ✅ | **优势** |
| 实例 smart label（可编辑别名） | ❌ | ✅ | **优势** |
| **remote / server 模式**（公网监听 + 设备配对 + TLS） | ✅（受支持） | ⚠️ 代码在树中但**不支持** | **劣势**（有意不支持，见 §2.5） |

**【代码事实】** fork 专属代码量约 **2024 行**：`cli/invoke.rs` 671 + `cli/templates.rs` 670 + `daemon/templates.rs` 344 + `protocol/template.rs` 276 + `cli/completion.rs` 63。

### 2.2 技术架构

| 项 | 上游 | 本 fork | 结论 |
|---|---|---|---|
| 工作区形态 | Cargo + pnpm 双工作区 | 同 | 持平 |
| 协议层 | `bsk-protocol`（schema 由 `dump-schema` 生成并提交） | 同，**握手逻辑与上游零差异** | 持平（刻意为之，见 §2.6） |
| 扩展 | WXT + React + Tailwind v4，MV3 | 同 | 持平 |
| 分层 | CLI / daemon / 扩展 三层 | 同 + **pro 的 Skill 层**（第四层） | **优势**（多了使用层） |
| 文档结构 | `docs/` + `skill/SKILL.md` | new：`docs/` 含同步策略与不变量清单；pro：`skill/`（65 文件）+ `references`(10) + `examples`(7) + `scripts`(20) | **优势**（更厚的使用层文档） |
| 命令事实管理 | 分散在文档与代码中 | pro：**单一数据源** `command-registry.json`（56 条）+ 生成器 + `--check` 漂移校验 | **优势**（防漂移） |

**【代码事实】** `zenx-bridge-skill` 的注册表按能力分层：0.2.3 基线 43 条 / 0.2.4+ 8 条 / fork 专属 5 条；生成区块 4 个（`skill-action-map` 12、`skill-additional` 44、`protocol-actions` 17、`protocol-additional` 32）。

### 2.3 性能表现

**【未实测】** 两端都**没有公开的系统基准测试数据**（页面观察耗时、截图延迟、内存占用曲线等）。本文不给出性能对比数字。

可引用的间接观察（非基准，仅供参考）：

| 观察 | 数据 | 来源 |
|---|---|---|
| 扩展测试套件规模 | 127 文件 / 2062 通过 / 103 跳过 / 0 失败，耗时约 37 s | 【实测】`pnpm ext:test` |
| Rust 测试规模 | 44 个 target / 762 通过 | 【实测】`cargo test --workspace --locked --no-fail-fast` |
| pro 测试规模 | 306 通过 / 1 跳过 | 【实测】`python -m unittest discover -s tests` |
| 多账号批量 | 20 账号，单账号约 25 s；并发窗口上限默认 8 | 【实测】`daily-checkin.ps1` 单次运行日志 |

**结论：性能维度持平，且我方无基准数据支撑任何性能主张。** 唯一可说的是内存控制策略：批量签到按窗口分组、签完即关，把**峰值**压在窗口大小而非账号总数上——这是架构选择，不是性能优势。

### 2.4 扩展能力

| 项 | 上游 | 本 fork | 结论 |
|---|---|---|---|
| 新增协议方法的成本 | 标准流程 | 同 + 需同步 schema 与 pro 注册表 | 略高（多了下游要同步） |
| 二次开发入口 | CLI 子命令 | CLI 子命令 + `invoke` 透传任意 `tool.*` RPC | **优势** |
| Shell 集成 | 无 | `bsk completion bash/zsh/fish/powershell` | **优势** |
| 多实例/多 Profile 操作 | 无 | `--browser-id` 指定实例、`browsers close` 关闭实例、smart label 别名 | **优势** |
| 第三方集成 | DSH Plugin | 同 + pro 的 20 个脚本（Python / PowerShell） | **优势** |
| 远程扩展能力 | 官方支持 | **明确不支持，且不接纳其后续变更** | **劣势** |

### 2.5 安全机制

| 机制 | 上游 | 本 fork | 结论 |
|---|---|---|---|
| 只绑 loopback（默认） | 是 | 是（**默认且唯一受支持的模式**） | 持平 |
| 无遥测/无埋点 | 是（`PRIVACY.md` 声明） | 是（继承） | 持平 |
| 用户标签页保护 / borrow 显式确认且失败 fail-closed | 是 | 是（继承，写入不变量清单） | 持平 |
| 会话边界（Agent Window 隔离） | 是 | 是 | 持平 |
| 公网监听面 | 存在（remote/server 模式，官方支持） | **代码在树中但不支持、不启用、不文档化** | **劣势（风险）**：树里带着未使用的公网监听代码 |
| `identity` 权限（读取 Profile 账号 ID） | 无 | 有，**默认关闭**，opt-in 才调用 | 中性偏劣势：新增了一个可选权限面 |
| 关闭浏览器实例的破坏性 | 无此命令 | `browsers close` 需 `--confirm`，且**只关本轮拉起的实例** | 持平（有守卫） |

**必须直面的短板**：fork 树中包含上游 remote/server 模式的完整实现（`daemon/remote/**`、`transport/remote-*`）。我们不支持它，但**代码在、且不在我们的测试与审计范围内**。若将来有人误用或该代码被间接触发，会增加暴露面。这是"为保持可合并而携带"付出的代价，见 §5。

### 2.6 兼容性

| 项 | 结论 |
|---|---|
| 协议握手 | **持平且刻意保持**：`bsk-protocol/src/system.rs` 握手逻辑与上游零差异。这是低成本同步的前提，也是既定策略。 |
| CLI ↔ 扩展版本 | 双方都要求匹配（不匹配退出码 5）；我方 CLI 与扩展同为 0.4.0 |
| 版本号可比性 | **我方版本线独立**：号码始终大于最后同步的上游版本（上游 0.3.0 → 我方 0.4.0）。好处是"看版本号就知道跑的是哪个发行版"；代价是与上游文档、教程的版本号不一致，引用时需换算。 |
| 上游脚本/教程 | 上游安装脚本与文档指向 `Tencent/BrowserSkill`；我方 README / `AGENT_INSTALL.md` / 安装 URL 已全部改为 `916938/zenx-bridge`。**上游教程不能直接照抄**。 |
| pro 与 bsk 版本 | pro 向后兼容 bsk 0.1.0+，但 fork 专属能力需要 fork 构建；能力按三层标注，缺失时自动降级 |

### 2.7 社区生态

| 项 | 上游 | 本 fork | 结论 |
|---|---|---|---|
| 分发渠道 | Chrome Web Store、Edge Add-ons 官方上架 | **无商店分发**，只能解压加载（`apps/extension/dist/chrome-mv3`） | **明显劣势** |
| 安装体验 | 商店一键安装 | 需本地构建 + 解压加载 + 手动 Reload | **明显劣势** |
| 品牌与商标 | 官方 `BrowserSkill` 商标 | 不能对外使用该商标 | **劣势**（身份步骤尚未完成） |
| 用户规模 / issue 活跃度 | 官方项目，规模更大 | 小众 | **劣势** |
| 自动更新 | 官方 release 通道 | 自建 release（`update.rs` 指向我方仓库），需自行维护 | 持平（有实现，但规模小） |

> 说明：我方扩展加载路径固定，换路径会改变扩展 ID 并使所有 `instance_id` 失效——这进一步限制了分发方式的灵活性。

### 2.8 维护成本

| 项 | 上游 | 本 fork | 结论 |
|---|---|---|---|
| 同步负担 | 无 | 需持续跟进上游并裁决冲突 | **劣势** |
| 上次全量合并成本 | — | 上游 49 提交 / 我方 50 提交；**双方都改过的文件 28 个**；实际冲突 19 文件 / 30 冲突块 | **劣势**（量化） |
| 后续同步方式 | — | 已改为**定向 cherry-pick**（每次冲突面降到 2–3 文件），并有 `docs/UPSTREAM_SYNC.md` 记录已移植/不移植清单 | 劣势但已收敛 |
| 需维护的版本号 | 1 套 | 3 处（new 的 Cargo.toml / 扩展 / DSH plugin）+ pro 文档 + 下游文档 | **劣势** |
| 测试资产 | 上游自带 | Rust 762 + 扩展 2062 + pro 306（合计约 3000 项） | 优势（有可回归的网） |
| 架构约束文档化 | 部分 | `AGENTS.md` 11 条设计不变量 + 同步策略文档 | 优势 |

---

## 3. 适用场景

### 3.1 我方组合更合适的条件

| 场景 | 原因 |
|---|---|
| **需要在同一台机器上区分/操作多个浏览器 Profile** | `--browser-id`、用户作用域 tab、`browsers close`、profile account id、smart label —— 上游没有对应能力 |
| **任务必须跨出会话边界**（例如签到结束后要关掉整个 Edge 实例释放内存） | `browsers close` 是唯一的此类命令 |
| **Agent 需要调用尚未封装成子命令的 RPC** | `bsk invoke` 透传，不必等上游新增子命令 |
| **需要可复用/可迁移的 Profile 状态** | `bsk templates`（注意：只保存模板元数据与受控条目，不是账号备份） |
| **需要人机协作之外的自动化外壳**：shell 补全、脚本编排、批量任务 | `bsk completion` + pro 的 20 个脚本 + 示例 |
| **要交付给 AI Agent 直接使用** | pro 提供 SKILL.md、命令注册表（单一数据源）、决策树、红线与示例；上游只提供 CLI |
| **重视命令文档不漂移** | pro 的注册表 + 生成器 + `--check`，漂移时 CI 可拦截 |
| **只在本机 loopback 内使用，且不需要远程浏览器** | 与我们的支持范围一致 |

### 3.2 上游原版仍占优的条件

| 场景 | 原因 |
|---|---|
| **需要远程/云端部署浏览器**（Agent 在服务器、浏览器在用户机器） | 上游官方支持 remote/server 模式与设备配对；**我们明确不支持** |
| **希望通过应用商店安装/分发扩展** | 上游已上架 Chrome Web Store 与 Edge Add-ons；我方只能解压加载 |
| **需要官方品牌背书或合规审计口径** | 上游是腾讯官方项目；我们是社区衍生作品，不能用其商标 |
| **组织内希望跟随上游长期路线** | 上游有官方维护与路线图；我方是下游，存在同步滞后与潜在分歧 |
| **不想承担同步与多版本维护成本** | 我方需持续 cherry-pick、维护三条版本号与下游文档 |
| **需要官方 issue / 讨论支持** | 上游社区规模更大 |

---

## 4. 客观结论

### 4.1 优势（有事实支撑）

1. **能力超集**：上游 0.3.0 的全量能力 + 7 类 fork 专属能力（约 2024 行 fork 专属代码）。
2. **多了一层"使用层"**：pro 把 CLI 能力编排为 Agent 可直接遵循的指令、脚本与示例，并提供单一数据源的命令注册表防文档漂移。
3. **可回归验证**：约 3000 项测试（Rust 762 / 扩展 2062 / pro 306），且本次上游合并后全部通过。
4. **架构约束被显式文档化**：11 条设计不变量 + 上游同步策略与不移植清单，降低了长期漂移风险。
5. **协议层与上游零差异**，这是可持续同步的基础。

### 4.2 短板（不回避）

1. **无商店分发**：只能本地构建 + 解压加载，安装体验明显劣于上游。
2. **不支持远程/server 模式**：这是与上游最大的功能性缺口，且是主动选择，不适用相关场景时直接出局。
3. **树中包含未支持的公网监听代码**：增加审计面，是"为保持可合并"付出的代价。
4. **维护成本更高**：28 个双方都改过的文件、19 文件/30 冲突块的合并成本、三处版本号与下游文档的联动。
5. **无性能基准**：不能对性能做任何量化主张。
6. **版本号与上游不可比**：引用上游文档/教程时需要换算，容易混淆。
7. **身份与合规工作未完成**：对外品牌仍沿用上游名称，LICENSE 虽已补充我方版权与 NOTICE，但品牌去上游化尚未落地。

### 4.3 可改进方向（按优先级）

| 优先级 | 方向 |
|---|---|
| 高 | **完成身份去上游化**：对外名称与商标不再使用 `BrowserSkill`（CLI 二进制名 `bsk` 建议保留，下游三仓硬编码依赖） |
| 高 | **明确 remote 代码的处置**：要么从树中移除（代价：与上游合并成本上升），要么加编译/启动期开关使其不可达并写入审计说明 |
| 中 | **建立性能基准**（观察耗时、截图延迟、批量内存曲线），让性能维度从【未实测】变为可比较 |
| 中 | **降低同步成本**：把 fork 专属改动收敛到更少、更独立的文件，减少与上游的重叠面 |
| 中 | **提供分发方案**：至少给出可复现的构建与加载脚本，降低非开发者的使用门槛 |
| 低 | 补齐英文文档与对外说明，便于他人引用 |

### 4.4 风险

| 风险 | 说明 | 缓解 |
|---|---|---|
| 上游协议不兼容变更 | 会让我方的低成本同步失效 | 已将其列为"考虑切断 upstream"的触发条件之一（见 `docs/UPSTREAM_SYNC.md`） |
| 上游强制默认走 server 模式 | 与我们的安全模型冲突 | 同上，已列为切断触发条件 |
| fork 专属能力无人继承 | 目前维护高度集中 | 测试网 + 文档化不变量是主要缓解手段 |
| 下游三仓版本联动出错 | pro 与 zenx 都依赖 fork 专属命令 | 三方文档已声明依赖关系；版本升级需同步 |
| 未支持的 remote 代码被误用 | 树中存在但未测试 | 已在 `AGENTS.md`、`NOTICE`、`docs/UPSTREAM_SYNC.md` 三处标记为不支持 |

---

## 5. 一句话结论

**本 fork 组合 = 上游能力 + 多实例/透传/模板等 fork 专属能力 + 一层面向 Agent 的使用层，代价是更高的维护成本、无商店分发、以及主动放弃远程模式。** 适合本机、多 Profile、Agent 驱动、可自维护的场景；需要远程浏览器、商店分发或官方背书时，上游原版仍是更合适的选择。

---

## 附录 A：复核命令

```bash
# 版本
bsk --version                      # 期望 0.4.0

# 协议层与上游是否有差异
git fetch Tencent
git diff Tencent/main -- crates/bsk-protocol/src/system.rs    # 期望：无输出

# 分歧规模
git rev-list --left-right --count Tencent/main...main         # 我方独有 / 上游独有
git merge-base Tencent/main main | xargs -I{} sh -c 'git diff --name-only {} main; git diff --name-only {} Tencent/main' | sort | uniq -d | wc -l   # 双方都改过的文件数

# fork 专属代码量
git diff --stat $(git merge-base Tencent/main main) main -- crates/bsk-cli/src/cli/invoke.rs crates/bsk-cli/src/cli/templates.rs crates/bsk-cli/src/daemon/templates.rs crates/bsk-protocol/src/template.rs crates/bsk-cli/src/cli/completion.rs

# 测试
cargo test --workspace --locked --no-fail-fast
pnpm --filter @browser-skill/extension compile
pnpm ext:test
python -m unittest discover -s tests        # 在 zenx-bridge-skill 下
```

## 附录 B：本文引用的实测数据来源

| 数据 | 采集命令 | 采集时间 |
|---|---|---|
| Rust 762 通过 / 44 targets | `cargo test --workspace --locked --no-fail-fast` | 2026-09-21 |
| 扩展 2062 通过 / 103 跳过 / 0 失败 / 127 文件 | `pnpm ext:test` | 2026-09-21 |
| pro 306 通过 / 1 跳过 | `python -m unittest discover -s tests` | 2026-09-21 |
| 注册表 56 条（43 / 8 / 5） | 解析 `skill/references/command-registry.json` | 2026-09-21 |
| 上游 0.3.0 / 我方 0.4.0 | `git show Tencent/main:Cargo.toml`、仓库 `Cargo.toml` | 2026-09-21 |

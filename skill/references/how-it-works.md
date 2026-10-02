# ZenX Bridge Skill 的工作原理

> **仅供人类维护者阅读。高度耗费上下文，不推荐 agent 在正常任务中查看。**
>
> Agent 执行浏览器任务时只需要阅读 `SKILL.md`，并按需查看
> `protocol.md` 或 `operations.md`。本文解释设计原因，而不是提供操作步骤。

## 它解决的是什么问题

普通网页搜索面对的是公开互联网。BrowserSkill 面对的是用户正在使用的真实浏览器：

- 已登录的网站
- 用户现有的 Cookie 和会话
- 已打开的标签页
- 浏览器扩展提供的页面控制能力

因此，它不是搜索引擎，也不是一个独立浏览器。它是一条连接 agent、电脑上的本地
daemon、浏览器扩展和真实标签页的桥。

```text
Agent
  |
  | bsk CLI commands
  v
Local daemon :52800 (WebSocket)
  |
  | extension connection
  v
Browser extension
  |
  v
Real browser tabs and logged-in sessions
```

## 为什么需要本地 daemon

Agent 不直接调用浏览器扩展。它通过 `bsk` CLI 发送结构化命令，本地 daemon
负责转发、维护 session，并统一返回结果。

这样做有几个好处：

- agent 不需要理解浏览器扩展内部通信协议
- 浏览器和 agent 可以独立升级
- 同一个任务可以通过 session 持续控制同一组标签页
- daemon 可以把截图等大数据先落到本地文件，避免塞满上下文
- Agent Window 提供隔离的浏览环境，保护用户隐私

代价是系统存在三个需要同时健康的部分：daemon、扩展、浏览器。`bsk doctor` 只能证明
前两者是否连接，不能保证具体网站一定接受自动化操作。

当多个浏览器连接时，daemon 维护独立的客户端列表。每个浏览器扩展建立自己的
WebSocket 连接，daemon 通过 `browser_list` RPC 追踪所有实例。`bsk session start`
默认选择唯一连接的浏览器；当多个浏览器在线时，必须用 `--browser` 指定目标，
否则会返回错误并列出可用实例。每个浏览器的 Agent Window 和会话完全独立，互不干扰。

## Session 不是浏览器登录会话

BrowserSkill 的 session 是 agent 侧的任务标识，用来关联一个 Agent Window。它不是网站的
登录 session，也不会创建新的浏览器用户配置。

同一个 BrowserSkill session 应在一个任务中复用，因为动作通常隐式依赖“当前选中的
标签页”。不同任务使用不同 session，可以降低串页和误操作风险。

## Agent Window 的隔离模型

BrowserSkill 使用 Agent Window 作为隔离环境：

- 任务所有的标签页在 Agent Window 中创建和管理
- 用户所有的标签页在普通浏览器窗口中，需要显式借用
- Agent Window 随 session 停止而关闭，不会影响用户的普通浏览

这一模型比 Kimi WebBridge 的 session 模型更严格，提供更好的隔离性。

## 标签页所有权为什么重要

标签页分成两类：

- 用户所有：任务开始前已经存在，通过 `bsk tab borrow` 借用
- 任务所有：agent 使用 `bsk navigate` 或 `bsk tab create` 创建

这一区分直接决定清理策略。关闭任务创建的标签页通常是合理的；关闭用户原本打开的
页面可能丢失输入内容、阅读位置或其他临时状态。

`bsk session stop` 会关闭 Agent Window 并归还所有借用的标签页，所以只有确认其中全部是任务所有时才适合使用。

## Snapshot 为什么优先于 CSS

`snapshot` 返回页面的可访问性树，并为可交互元素分配 `@e` 引用。它比手写 CSS
选择器更适合 agent：

- 不依赖经常变化的哈希类名
- 带有角色和可读名称，较容易理解页面语义
- 生成的命令更短

这些引用不是永久 ID。页面导航、重新渲染或大幅 DOM 更新后，旧引用可能失效，所以
需要重新 snapshot。

## 为什么点击后页面可能“没有变化”

常见原因并不相同：

- SPA 只替换了页面内容，没有传统整页跳转
- 网站在后台标签页打开了目标
- 浏览器拦截了弹窗或新窗口
- 点中了卡片内部的非主链接区域
- 网站拒绝了合成事件

因此恢复顺序是先检查 URL 和 snapshot，再看标签页列表，最后才判断是否被浏览器
阻止。盲目重复点击可能打开多个页面或产生重复提交。

## 合成事件的边界

`click` 和 `fill` 通常通过页面内 JavaScript 触发 DOM 事件。它们不是操作系统产生的
真实鼠标和键盘事件，因此 `event.isTrusted` 为 false。

大多数内容站点接受这种方式，但银行、验证码、安全确认和部分富文本编辑器可能拒绝。
这是浏览器安全模型的边界，不应该通过伪造或绕过网站保护来解决。

跨域 iframe 也是类似边界。顶层页面脚本不能直接读取另一个来源的 iframe 内容。
合适时可以导航到 iframe 自己的 URL，否则只能说明限制。

## 为什么使用 helper scripts

直接在命令行中手写 bsk 命令参数很容易遇到引号、换行和中文编码问题。
`invoke.ps1` 和 `invoke.sh` 使用对象构造请求并显式发送 UTF-8，减少协议格式错误。

截图数据可能很大。`screenshot.py` 兼容 bsk 返回的路径响应，并统一给 agent 一个本地
文件路径。

`snapshot` 的问题不同：它返回 JSON，但复杂页面可能有数万字。daemon 当前没有提供
服务端过滤参数，因此 `snapshot.py` 在客户端提供两种选择：

- `compact` 只保留 URL、标题、语义地标和可操作引用
- `file` 原样保存完整响应，Agent 再按任务需要读取局部

这不是丢弃协议能力，而是避免无关页面内容一次性进入上下文。

Python helper 共用 `bsk_client.py`，因此 UTF-8 输出、命令错误和 daemon 错误
只在一处处理。`wait_for.py` 也只重复观察页面状态，不会替 Agent 重复点击或提交。

## 隐私边界

BrowserSkill 使用真实浏览器，意味着它可能接触到普通公开网页工具看不到的信息。隐私
风险不只来自"是否上传文件"，还来自读取页面本身：

- snapshot 可能包含私信、订单、地址或内部页面文字
- screenshot 可能保留页面上的个人信息
- evaluate 理论上能够读取页面脚本可访问的存储和表单内容

这些能力不应该被默认使用到最大范围。Pro 版采用最小化原则：只读取完成任务所需的
页面部分，不读取认证材料，不把无关私人内容带回 agent 上下文，不为"以后可能有用"
而保存截图。

本地 daemon 位于 loopback 地址，但"本地通信"不代表页面内容永远只停留在电脑上。
当 snapshot、截图文字或结果返回给 agent 后，它们会进入当前 AI 会话的处理
范围。因此，敏感程度应按"会被 AI 处理"来判断，而不是仅按 daemon 是否监听本地
端口来判断。

临时截图也是隐私数据。正常做法是任务完成后删除；只有用户明确要求保留时，
才把它们当作交付文件保存。

## BrowserSkill 的独有能力

相比 Kimi WebBridge，BrowserSkill 提供了更多高级功能：

- `bsk request-help`: 请求人工介入处理验证码、登录等场景
- `bsk tab borrow/return`: 显式的标签页借用/归还机制
- `bsk browsers`: 列出所有已连接的浏览器实例
- `bsk session start --browser`: 多浏览器环境下指定目标浏览器
- `bsk press`: 键盘事件支持
- `bsk select`: 下拉菜单选择
- `bsk navigate-back/forward`: 浏览器前进后退
- `system.ping`: MV3 service-worker 保活心跳，daemon 自动回复 pong

这些能力使得 BrowserSkill 更适合复杂的浏览器自动化场景。

## 维护原则

- `SKILL.md` 只放 agent 完成任务必须知道的内容
- `protocol.md` 记录动作参数和协议约束
- `operations.md` 记录安装、状态和故障恢复
- `scripts/` 保持小而确定，只写必要注释
- 本文只解释原理和取舍，不参与日常执行

当 daemon 行为变化时，先通过真实请求验证响应，再更新协议和脚本。不要只依据旧文档
猜测当前实现。
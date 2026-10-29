# 最小运行方式

需要 Python 3.10 或更新版本；生成的本地服务只用标准库。缩略图制作由 Agent 根据实际格式使用 Pillow／RAW 工具完成，不随服务偷偷启动模型或扫描目录。

1. 按 SKILL.md 先与使用者确认目标、来源、留存、分类、审核、更新与权限。
2. 建立本地 profile.json：purpose、source_roots、stages、review_kinds、update_trigger="manual_message"、collections（id/title/description 数组）、confirmed_by_user=true。路径用使用者自己的实际位置；示例占位值不能直接套用。
3. 运行：`python <Skill目录>/scripts/bootstrap.py --profile <确认后的profile.json> --destination <新工作台目录>`。目标已存在会拒绝覆盖。
4. 在新目录运行 `python start.py --port 8932`，打开终端给出的本地地址。需要桌面独立窗口时，按使用者系统现有的应用窗口方式实现并实际验收。
5. Agent 按授权盘点、真实看图和核验后更新 data/ 中的文件。空工作台不会假装已筛选完。

数据格式：
- catalog.json：照片数组，含 id（内容身份）、name、description、theme、month、equipment、has_preview、preview（工作台内缓存相对路径）、preview_sha256、places（path/location/state 数组）。同内容可有多个位置。
- collections.json：照片集数组，含 id、section（对应 profile.collections 的 id）、title、count、preview_ids（封面照片 id）、members（照片 id）、paths。同照片允许属于多个集。
- review_tasks.json：事项数组，含 id、category、title、question、proposal、why、paths、asset_ids、owner、priority、choices、details。choices 按问题选择 accept／confirmed／needs_change／provide_clue／deferred／keep_unknown 等；不要让用户阅读内部编号才能做决定。

所附界面是可改造起点。交付前应根据已经确认的 profile 调整导航、用语、阶段和视觉，不要求所有使用者采用同一套家庭分类或主题。不要承诺未经实现的自动归档、实时监听或模型识别。

- projects.json：可选在途项目数组，含 id、name、photos、path；由实际批次证据更新。维护页只展示已连接的真实资料，未附带作者私人资源入口。

# 反馈闭环

事件账本只追加，保留原话与链式 SHA；并发写入用版本检查。具体决定不得在未执行时报告「已落实」。

状态：原反馈 → 个案落实／阻塞 → 可复用候选 → 用户采用 → 独立场景验证 → 生效／停用。不是每条反馈都需要成为规则。

`feedback.py` 命令均带 `--root <工作台目录>`：
- `context`：生成必须阅读的当前规则和未落实反馈上下文。
- `execution --file receipt.json`：`feedback_ids`、`result`（applied/needs_user/blocked/not_adopted）、`summary`、`evidence`（工作台内实际文件相对路径）。
- `propose --file rule.json`：`source_feedback_ids`、`text`、`scope`（workflow/taste/skill/album）、`boundary`、`rationale`、`generalization`、`counterexample`、`conflicts_with`。
- `validate --file case.json`：`rule_id`、`case_id`、`context_key`、`passed:true`、`summary`、`evidence`。同一轮、同一证据不重复计数。
- `activate --rule-id ID`：需要用户采用、至少两类场景验证和无冲突；证据变更则停止沿用。

原始个案、候选和生效规则分开；保留每个版本和来源。新增规则不能因一条否定意见就自动覆盖用户其他目标。用户需要能看到落实结果、未采用的原因，并可要求修改或停用。

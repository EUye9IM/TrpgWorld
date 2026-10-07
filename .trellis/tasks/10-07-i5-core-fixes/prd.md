# I5: 协议 core 缺陷修复（mask/compact/投影泄漏/秘密骰）

## Goal

修复已确认的协议 core 缺陷：F1 mask fail-open（缺 visibility.json 时默认全公开）；F2 compact↔build 重放膨胀；F3 context build 输出泄漏 worldPaths；F4 dice 无 secret 模式。依赖 I2/I3 产物；应先于 I4 插件（插件依赖正确的 core）。

## Requirements

- TBD

## Acceptance Criteria

- [ ] TBD

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.

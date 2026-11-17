# 宠物喂水器 品类知识

2026-11-17 从私有知识库 `geoorood-beep/pet-supplies-amazon-ads` 迁入（狗、猫喂水器，美国站）。只做选词、架构和相关性参考，不作为否词、降价、暂停、加预算的依据（优先级见 `agents/knowledge-base.md`）。

| 文件 / 目录 | 内容 | 原位置 |
|---|---|---|
| `初版广告架构_狗猫_20261114.md` | 狗、猫两个品类的初版 SP 广告架构设计 | `categories/` |
| `首推词表_狗不锈钢无线大容量.md` | 狗不锈钢无线大容量喂水器首推词表，总日预算 $200 | `docs/08` |
| `词表同步摘要.md` | Notion 词表同步摘要 | `docs/06` |
| `notion/` | 狗、猫准词表（得分、搜索量、竞品排名）、投放词池、历史出单词、原件 xlsx、处理脚本 | `data/notion/` |
| `keyword-weekly/` | 西柚每周一关键词扫描（每 ISO 周一份 md + csv）和词库修正记录 | `data/keyword-weekly/` |

## 以后怎么更新

- 西柚每周扫描：新增 `keyword-weekly/<年>-W<周数>_<狗/猫>喂水器.md` 和 `.csv`，修正追加到 `keyword-weekly/词库修正记录.md`。字段见 `keyword-weekly/README.md`。
- Notion 准词表静态字段不在这里覆盖；原件仍以 Notion「词库」页面为准，重新导出后替换 `notion/raw/` 并运行 `notion/scripts/build.py`。

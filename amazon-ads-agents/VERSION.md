# lulu 广告智能体版本

当前版本：`V1.1`

版本日期：`2026-07-07`

V1.1 固定范围：

- 广告组统一命名：`SPU-广告产品-定向维度-匹配方式-场景分类-尺寸-运营名`。
- 单关键词广告组名称支持 ABA 大致排名标记，例如 `runner rug(4k)`、`area rug(1.8w)`。
- 新广告标准最低日预算按类目 CPA 正常线上限计算，不按 CPC 推算。
- Rug 新品输入字段按 `新品基础信息输入模版_Rug类目` 收敛。
- Rug ABA 关键词库替换为 `reference/rug-aba/` 下 4 个场景文件，调用时只读取每个文件的 `广告词库` sheet。
- Rug 动物图案关键词按 `图案动物类型` 强匹配。
- Rug 历史出单词库固定到 `reference/category-history/rug/`。
- Rug 新品 Auto / Broad / Phrase 支持高流量核心隔离否词：`推荐层级=P1/P2 + ABA排名<=11000`，默认 `Negative Exact`。
- 老品优质出单词支持跨广告产品拓量：SP 表现稳定后，可复制验证 SPV / SB / SBV。

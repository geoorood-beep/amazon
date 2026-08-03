# V2 SP标准优化安全基础模块

该模块实现不依赖类目阈值、也不依赖唯一规则源选择的稳定合同和安全门：

- 标准决策数据包；
- AdContext；
- Rug-only Category 与 `SP_STANDARD_OPTIMIZATION` 能力路由；
- 3/7/14/30天事实指标及确定性派生指标；
- Campaign、Ad Group、Target和搜索词不可变ID校验；
- `1 Campaign = 1 Ad Group`硬校验；
- `O<2`观察与唯一停止例外；
- 整体广告唯一状态和广告位路由；
- 趋势混合信号阻断；
- 候选动作合同；
- 动作去重与冲突仲裁；
- 独立Validator；
- 人工执行确认；
- 复盘资格判断。

## 当前边界

- 状态：`TEST_ONLY`
- V2.0 人工规则：保持为文档规则，不转换为机器 ACTIVE
- 类目阈值：Rug 门垫、长条、小区域和大区域已确认；圆形和 O<2 可执行 Threshold ID 仍缺失
- 唯一规则源：未选择
- 真实报表解析器：等待实际样表
- 跨报表对账容差：等待实际样表和业务确认
- Amazon API自动执行：未启用

Validator要求规则包同时保存规则文件 SHA-256、阈值文件 SHA-256 和组合校验值。生产模式还要求规则源和阈值源均为`ACTIVE`，并通过代码内不可由请求参数覆盖的生产保险。当前生产保险固定关闭，因此即使调用方伪造两项 `ACTIVE`，仍会得到 `PRODUCTION_EXECUTION_DISABLED`；`AUTO_PASS`只表示结构测试通过，不代表可调用 Amazon API。

# Rug 历史数据阈值校准资格

本文件定义“什么时候可以生成候选阈值”，不直接替代 CVR、CPA、ACOS 正式标准。所有输出固定为 `CANDIDATE`，人工批准并通过回归前不得写入正式阈值。

## THR-CAL-001：具有参考意义的候选阈值

- 状态：`CONFIRMED_HUMAN / CANDIDATE_ONLY`。
- `applicable_grain`：`CALIBRATION_SEGMENT`。
- 有效点击：`>= 2,000`。
- 广告订单：`>= 50`。
- 独立完整自然日：`>= 14`。
- 归因：全部成熟。
- 数据质量：不得为 `DQ_BLOCKED`。
- 输出权限：`REFERENCE_CANDIDATE`，必须人工确认。

## THR-CAL-002：较高置信候选阈值

- 状态：`CONFIRMED_HUMAN / CANDIDATE_ONLY`。
- `applicable_grain`：`CALIBRATION_SEGMENT`。
- 有效点击：`>= 5,000`。
- 广告订单：`>= 100`。
- 独立完整自然日：`>= 30`。
- 独立历史验证窗口：`>= 3`。
- 归因：全部成熟。
- 数据质量：必须为 `DQ_PASS`。
- 输出权限：`HIGH_CONFIDENCE_CANDIDATE`，仍必须人工确认。

## THR-CAL-003：零订单高风险候选

- 状态：`CONFIRMED_HUMAN / RISK_CANDIDATE_ONLY`。
- `applicable_grain`：`CALIBRATION_SEGMENT`。
- 有效点击：`>= 300`。
- 广告订单：`= 0`。
- 独立完整自然日：`>= 14`。
- 归因：全部成熟。
- 数据质量：不得为 `DQ_BLOCKED`。
- 输出权限：只允许 `ZERO_ORDER_RISK_CANDIDATE`；不得生成正式性能阈值、暂停、否词或其他后台动作。

## 有效点击定义

有效点击必须同时满足：

1. `category=rug`；
2. Marketplace、币种、归因窗口一致；
3. 7/14/30 天重叠文件没有重复累计；
4. ASIN、SKU、尺寸档、广告类型、策略阶段和对象粒度可追溯；
5. Bid、预算、Placement、状态、价格、促销或库存变化已经切段；
6. 点击、订单、花费和销售额通过漏斗及非负校验；
7. 归因窗口已经结束。

`CALIBRATION_SEGMENT` 固定由 `rug_type + size_profile + ad_product_type + strategy_stage + object_grain` 组成。不同分组不得为了凑点击量直接合并。

## THR-CAL-004：历史留出“更优候选”证明门

这组数值是模型验证门，不是 CVR、CPA 或 ACOS 业务标准。只有先命中 `THR-CAL-001` 或 `THR-CAL-002` 才运行。

- 适用粒度：只允许与当前性能阈值一致的 `SKU_SIZE`；其他粒度输出 `INCONCLUSIVE_GRAIN_MISMATCH`。
- 时间切分：按日期前 `70%` 拟合候选，后 `30%` 完全留出；留出期至少 `4` 个独立日。
- 生成候选边界：训练期至少 `7` 个独立对象。
- 证明样本：至少 `20` 个同时存在训练期和留出期的独立对象。
- 可比较对象对：至少 `100` 对。
- 单对象点击：训练期 `>=30`，留出期 `>=10`。
- CPA 单对象订单：训练期 `>=2`，留出期 `>=1`。
- 候选边界：只用训练期对象分布的 `P25 / P50 / P75` 生成，不读取留出期结果。
- 比较方法：当前阈值和候选阈值分别按训练期给对象分层，再比较它们对留出期连续表现的对象对一致率。
- 显著性：对象级固定种子 Bootstrap `1,000` 次；一致率提升 `>=5` 个百分点，且提升的 95% 区间下界 `>0`，单项才记为 `BETTER`。
- 总体通过：CVR、CPA、ACOS 至少 `2` 项为 `BETTER`，且没有任何一项为 `WORSE`。
- 结果枚举：`HISTORICALLY_BETTER_CANDIDATE / NOT_BETTER / INCONCLUSIVE`。

`HISTORICALLY_BETTER_CANDIDATE` 只证明候选在未参与拟合的历史留出期中分层能力更强，不证明未来因果收益；仍需人工批准和上线后复盘。

## 候选更新边界

- 达标只表示允许生成候选阈值包，不代表候选值优于当前标准。
- 候选包必须保存样本量、来源 SHA-256、指标分布、时间切分结果、适用粒度和缺失项。
- 人工决定只允许 `APPROVED / REVISED / REJECTED / INSUFFICIENT_DATA`。
- 批准记录完成后状态只能进入 `HUMAN_APPROVED_PENDING_REGRESSION`。
- 只有回归、压力测试、来源登记和版本清单全部通过，才可由人工维护为 `CONFIRMED_HUMAN`。
- 程序、复盘 Agent、监控任务或外部连接器均不得自动覆盖正式阈值。

机器派生配置：[阈值校准配置](../../config/threshold_calibration.json)。人工维护时以本文件为准，修改数字后必须同步派生配置并运行 `scripts/validate_threshold_calibration.py`。

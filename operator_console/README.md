# 陆遥广告运营台 V1.2

这是陆遥广告智能体 V2.0 的本地操作入口。网页负责收集任务和展示结果，本地 Python 负责确定性预处理，Codex Worker 只读分析，独立 Validator 阻断越权结果。

界面采用陆遥绿色品牌系统：桌面端为左侧业务导航、顶部状态栏、浅灰工作区和白色任务卡；关键操作使用品牌绿，错误和 Validator 阻断仍使用独立警示色。移动端自动收起侧栏并重排表单和处理结果。

已提供可在其他电脑打开的公开演示版。远程页面会自动进入 `PUBLIC DEMO`：允许浏览四个入口和操作流程，但关闭上传、Python 聚合、Codex 分析和结果下载。真实报表仍只能在安装完整 V2.0 的本地电脑处理，公开网页不接收或保存广告数据。

## 四个入口

1. 新品推广：从本地属性库手动选择，或上传一张产品表自动识别字段 → 新品模块 → Codex 分析 → 候选方案；
2. 老品优化：上传/拖拽报表 → 本地 Python 聚合 → 人工点击生成建议 → 单/多 ASIN 候选动作；
3. 更新广告数据：多报表去重并生成 JSON/XLSX 决策包；
4. 查看本周建议：运行每周阈值候选检查，不覆盖当前阈值。

## 最简单的启动方式

双击项目根目录的 `运行广告运营台.command`。首次启动会安装前端依赖并构建页面，之后自动打开：

```text
http://localhost:3000/
```

关闭启动命令的终端窗口会同时停止网页和后台。

## 手动启动

终端 1：

```bash
.venv/bin/python scripts/run_operator_console_backend.py
```

终端 2：

```bash
cd operator_console
npm install
npm run dev
```

## 数据与安全边界

- 网页可上传 XLSX、XLSM、CSV、TSV；单文件上限 200 MB。原文件只保存到本机 `runtime/operator-uploads/`，不进入 Git，也不会上传到云端。
- 新品尺寸、类型、风格、颜色、材质和场景从 `config/operator_catalog.json` 读取；该属性库必须与新品规则配置保持一致，不在网页中复制业务阈值。
- 老品不再上传单独的“老品数据工作簿”。ASIN 可不填并从广告商品报表识别；填写一个或多个 ASIN 时只处理指定对象。识别超过 100 个 ASIN 时必须人工指定，防止误跑超大任务。
- 开始日和结束日不再人工输入，由 Python 从上传报表日期列自动识别。
- 任务仍兼容项目目录、`Downloads`、`Documents`、`Desktop` 中的合法本机路径，但普通网页操作不再要求用户填写路径。
- 任务记录保存在 `runtime/operator-jobs/`，该目录不进入 Git。
- 后台只监听 `127.0.0.1:8766`，网页只在本机访问。
- Codex 使用只读沙箱，输出必须通过 `operator-result.schema.json` 和独立 Validator。
- 仅允许 `rug`；不会连接或操作 Amazon 后台；所有建议都需要人工确认。

## 老品两步操作

1. 把亚马逊或广告系统导出的搜索词、投放对象、广告位、广告商品、Campaign/Ad Group 设置等原始报表一次上传、拖入或选择整个文件夹，然后点击“聚合数据报表”。这一步只运行本地 Python，不调用 Codex。
2. 聚合成功后检查 ASIN、日期和结果文件，再点击“生成广告建议方案”。这一步复用已经生成的数据包，不重复聚合，之后才调用 Codex 和独立 Validator。

完整的 7/14/30 天成套报表走 `REPORT_ONLY_OVERLAP_SAFE_MULTI_ASIN`：30 天每日明细是事实基线，7/14 天及汇总表只校验，不重复相加。缺 Amazon 不可变 ID 时可生成分析包，但执行权限继续阻断。

## 验证

```bash
cd operator_console
npm run lint
npm test
npm audit --omit=dev

cd ..
.venv/bin/python -m pytest operator_console/backend/tests -q
```

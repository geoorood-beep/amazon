# 陆遥广告运营台 V1

这是陆遥广告智能体 V2.0 的本地操作入口。网页负责收集任务和展示结果，本地 Python 负责确定性预处理，Codex Worker 只读分析，独立 Validator 阻断越权结果。

## 四个入口

1. 新品推广：产品信息 → 新品模块 → Codex 分析 → 候选方案；
2. 老品优化：报表聚合 → 诊断 → 候选动作；
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

- 第一版使用本机绝对路径，不上传广告报表；允许读取项目目录、`Downloads`、`Documents`、`Desktop`。
- 任务记录保存在 `runtime/operator-jobs/`，该目录不进入 Git。
- 后台只监听 `127.0.0.1:8766`，网页只在本机访问。
- Codex 使用只读沙箱，输出必须通过 `operator-result.schema.json` 和独立 Validator。
- 仅允许 `rug`；不会连接或操作 Amazon 后台；所有建议都需要人工确认。

## 验证

```bash
cd operator_console
npm test
npm audit --omit=dev

cd ..
.venv/bin/python -m unittest discover operator_console/backend/tests -v
```

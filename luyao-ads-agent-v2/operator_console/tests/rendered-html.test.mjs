import assert from "node:assert/strict";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request("http://localhost/", { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("server-renders the Luyao operator console", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>陆遥广告运营台<\/title>/i);
  assert.match(html, /广告运营驾驶舱/);
  assert.match(html, /广告架构设计/);
  assert.match(html, /SP广告优化/);
  assert.match(html, /更新广告数据/);
  assert.match(html, /查看本周建议/);
  assert.match(html, /智能补货/);
  assert.match(html, /所有结果需人工确认/);
  assert.doesNotMatch(html, /Your site is taking shape|SkeletonPreview|codex-preview/);
});

test("client source keeps the local safety boundary visible", async () => {
  const page = await import("node:fs/promises").then(({ readFile }) =>
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
  );
  assert.match(page, /http:\/\/127\.0\.0\.1:8766/);
  assert.match(page, /公开演示版只展示操作流程/);
  assert.match(page, /LOCAL_HOSTNAMES/);
  assert.match(page, /本地执行关闭/);
  assert.match(page, /本地主版本/);
  assert.match(page, /分享演示版/);
  assert.match(page, /PUBLIC_DEMO_URL/);
  assert.match(page, /LOCAL_REPLENISHMENT_URL\s*=\s*"http:\/\/localhost:3000\/"/);
  assert.match(page, /luyao-replenishment-v2-20260804\.louie847918852\.chatgpt\.site/);
  assert.match(page, /SystemSwitcher/);
  assert.match(page, /只生成建议/);
  assert.match(page, /Amazon 自动执行关闭/);
  assert.match(page, /Rug 专用/);
  assert.match(page, /type="file"/);
  assert.match(page, /导入产品表格/);
  assert.match(page, /添加到产品清单/);
  assert.match(page, /待设计产品清单/);
  assert.match(page, /手动录入已达到10个ASIN上限/);
  assert.match(page, /采用表格上传/);
  assert.match(page, /products_json/);
  assert.match(page, /从表格清单中修改/);
  assert.match(page, /识别产品清单/);
  assert.match(page, /showProductFields/);
  assert.match(page, /选择整个文件夹/);
  assert.match(page, /拖拽广告报表到这里/);
  assert.match(page, /聚合数据报表/);
  assert.match(page, /生成 SP 广告优化方案/);
  assert.match(page, /广告架构预览/);
  assert.match(page, /问题提示/);
  assert.match(page, /SP 广告优化方案/);
  assert.match(page, /当前没有可用架构/);
  assert.match(page, /Campaign ID/);
  assert.match(page, /7 \/ 14 \/ 30 天重复窗口/);
  assert.match(page, /DATA PROCESSING/);
  assert.match(page, /问题提示/);
  assert.match(page, /下载结果/);
  assert.match(page, /建议分析 ASIN/);
  assert.match(page, /不需要填写开始日或结束日/);
  assert.match(page, /api\/catalog/);
  assert.doesNotMatch(page, /这次希望解决什么/);
  assert.doesNotMatch(page, /老品数据工作簿/);
  assert.doesNotMatch(page, /title: "新品推广"/);
  assert.doesNotMatch(page, /title: "老品优化"/);
  assert.doesNotMatch(page, /type="date"/);
  assert.doesNotMatch(page, /AGENTS KNOWLEDGE TRACE/);
  assert.doesNotMatch(page, /本次分析实际调用/);
  assert.doesNotMatch(page, /Validator：/);
  assert.doesNotMatch(page, /Codex \+ AGENTS/);

  const styles = await import("node:fs/promises").then(({ readFile }) =>
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  );
  assert.match(styles, /--brand:\s*#3f8f34/i);
  assert.match(styles, /\.side-nav/);
  assert.match(styles, /\.intent-card/);
  assert.match(styles, /\.demo-notice/);
  assert.match(styles, /\.system-switcher/);
  assert.match(styles, /\.product-queue/);
  assert.match(styles, /\.manual-limit-notice/);
  assert.doesNotMatch(styles, /\.replenishment-module-grid/);
});

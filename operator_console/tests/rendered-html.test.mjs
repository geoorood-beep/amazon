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
  assert.match(html, /新品推广/);
  assert.match(html, /老品优化/);
  assert.match(html, /更新广告数据/);
  assert.match(html, /查看本周建议/);
  assert.match(html, /HUMAN_EXECUTION_ONLY/);
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
  assert.match(page, /只生成建议/);
  assert.match(page, /Amazon 自动执行关闭/);
  assert.match(page, /Rug 专用/);
  assert.match(page, /type="file"/);
  assert.match(page, /导入产品表格/);
  assert.match(page, /已根据表格生成，可人工修正/);
  assert.match(page, /showProductFields/);
  assert.match(page, /选择整个文件夹/);
  assert.match(page, /拖拽广告报表到这里/);
  assert.match(page, /聚合数据报表/);
  assert.match(page, /生成广告建议方案/);
  assert.match(page, /LOCAL DATA ENGINE/);
  assert.match(page, /建议分析 ASIN/);
  assert.match(page, /不需要填写开始日或结束日/);
  assert.match(page, /api\/catalog/);
  assert.doesNotMatch(page, /这次希望解决什么/);
  assert.doesNotMatch(page, /老品数据工作簿/);
  assert.doesNotMatch(page, /type="date"/);

  const styles = await import("node:fs/promises").then(({ readFile }) =>
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  );
  assert.match(styles, /--brand:\s*#3f8f34/i);
  assert.match(styles, /\.side-nav/);
  assert.match(styles, /\.intent-card/);
  assert.match(styles, /\.demo-notice/);
});

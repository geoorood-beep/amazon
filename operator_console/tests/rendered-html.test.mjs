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
  assert.match(html, /今天要处理哪类广告任务/);
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
  assert.match(page, /只生成建议 · 人工执行/);
  assert.match(page, /不连接亚马逊执行/);
  assert.match(page, /Rug 专用/);
});

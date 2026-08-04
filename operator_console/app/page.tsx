"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import SystemSwitcher from "./system-switcher";

const API = "http://127.0.0.1:8766";
const PUBLIC_DEMO_URL = "https://luyao-rug-ads-v2-20260804.louie847918852.chatgpt.site";
const LOCAL_REPLENISHMENT_URL = "http://localhost:3000/";
const PUBLIC_REPLENISHMENT_URL = "https://luyao-replenishment-v2-20260804.louie847918852.chatgpt.site";

type Intent =
  | "NEW_PRODUCT_PROMOTION"
  | "OLD_PRODUCT_OPTIMIZATION"
  | "AGGREGATE_REPORTS"
  | "WEEKLY_REVIEW";

type Job = {
  job_id: string;
  intent: Intent;
  status: string;
  stage: string;
  created_at: string;
  updated_at: string;
  error?: string;
  request?: { fields: Record<string, string> };
  preprocessing?: {
    status: string;
    mode?: string;
    analysis_asins?: string[];
    auto_period?: { start?: string; end?: string };
    issues?: string[];
    workbook_summary?: {
      path: string;
      sheets: Array<{
        name: string;
        max_row: number;
        data_row_count?: number;
        preview: Array<Array<string | number | boolean | null>>;
        notes?: Array<{ asin: string; title: string; content: string }>;
      }>;
    };
  };
  result?: Result;
  validation?: { outcome: string; findings: Array<{ level: string; code: string; message: string }> };
};

type Result = {
  status: string;
  executive_summary: string;
  recommendations: Array<{ priority: string; action: string; reason: string; evidence: string; risk?: string }>;
  new_product_architecture: Array<{
    campaign_name: string;
    ad_group_name: string;
    asin: string;
    structure_mode: string;
    operation: string;
    match_type: string;
    daily_budget: string | number | null;
    bid: string | number | null;
    bidding_strategy: string;
    placement: string;
    role: string;
    target: string;
    negative_exact: string;
  }>;
  missing_inputs: string[];
  artifacts: string[];
  safety: {
    human_approval_required: boolean;
    execution_allowed: boolean;
    auto_apply: boolean;
    validator_status: string;
  };
};

type CatalogOption = { value: string; label: string };
type Catalog = {
  version: string;
  category: string;
  fields: Record<string, CatalogOption[]>;
};

type ProductInfo = Record<string, string> & {
  asin: string;
  marketplace: string;
  size_spec: string;
  rug_type: string;
  order_target_daily: string;
};

type UploadSummary = {
  upload_id: string;
  files: Array<{ role: string; name: string; size: number; error?: string }>;
  detected_asins: string[];
  report_asins: string[];
  suggested_asins: string[];
  period_start: string | null;
  period_end: string | null;
  recognized_product: {
    source_file: string;
    sheet: string | null;
    fields: Record<string, string>;
    products: ProductInfo[];
    warnings: string[];
  } | null;
  paths: { reports: string | null };
  warnings: string[];
};

const INTENTS: Array<{
  id: Intent;
  number: string;
  title: string;
  subtitle: string;
  description: string;
  accent: string;
}> = [
  {
    id: "NEW_PRODUCT_PROMOTION",
    number: "01",
    title: "广告架构设计",
    subtitle: "输入 ASIN 与产品属性",
    description: "填写产品信息，预览并下载广告架构",
    accent: "orange",
  },
  {
    id: "OLD_PRODUCT_OPTIMIZATION",
    number: "02",
    title: "SP广告优化",
    subtitle: "上传报表，诊断并重构 SP 广告",
    description: "上传广告报表，预览并下载 SP 优化方案",
    accent: "teal",
  },
  {
    id: "AGGREGATE_REPORTS",
    number: "03",
    title: "更新广告数据",
    subtitle: "多张报表合并为决策包",
    description: "上传多张报表，生成一份可下载的聚合结果",
    accent: "blue",
  },
  {
    id: "WEEKLY_REVIEW",
    number: "04",
    title: "查看本周建议",
    subtitle: "检查阈值候选与证据",
    description: "查看本周需关注的候选更新和问题",
    accent: "violet",
  },
];

const STAGES = [
  ["QUEUED", "已接收"],
  ["PREPROCESSING", "处理数据"],
  ["ANALYZING", "生成结果"],
  ["VALIDATING", "检查结果"],
  ["COMPLETED", "已完成"],
] as const;

const AGGREGATION_STAGES = [
  ["QUEUED", "已接收"],
  ["PREPROCESSING", "处理数据"],
  ["VALIDATING", "检查结果"],
] as const;

const FINAL_STATES = new Set(["COMPLETED", "BLOCKED", "FAILED"]);
const LOCAL_HOSTNAMES = new Set(["localhost", "127.0.0.1", "::1"]);

function subscribeToHostname() {
  return () => undefined;
}

function readPublicDemo() {
  return !LOCAL_HOSTNAMES.has(window.location.hostname);
}

function intentTitle(intent: Intent) {
  return INTENTS.find((item) => item.id === intent)?.title ?? intent;
}

function jobStatusLabel(status: string) {
  return ({
    QUEUED: "等待处理",
    PREPROCESSING: "处理数据",
    ANALYZING: "生成方案",
    VALIDATING: "检查结果",
    COMPLETED: "已完成",
    BLOCKED: "需补数据",
    FAILED: "处理失败",
  } as Record<string, string>)[status] ?? status;
}

function artifactHref(jobId: string, path: string) {
  const marker = "/artifacts/";
  const relative = path.includes(marker) ? path.split(marker)[1] : path.split("/").pop() ?? path;
  return `${API}/api/jobs/${jobId}/artifacts/${relative.split("/").map(encodeURIComponent).join("/")}`;
}

function formatTime(raw: string) {
  try {
    return new Intl.DateTimeFormat("zh-CN", {
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(raw));
  } catch {
    return raw;
  }
}

function formatBytes(value: number) {
  if (value < 1024 * 1024) return `${Math.max(1, Math.round(value / 1024))} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

export default function Home() {
  const [activeIntent, setActiveIntent] = useState<Intent | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({ marketplace: "US" });
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [uploadId, setUploadId] = useState("");
  const [uploadSummary, setUploadSummary] = useState<UploadSummary | null>(null);
  const [uploading, setUploading] = useState(false);
  const [newInputMode, setNewInputMode] = useState<"manual" | "import">("manual");
  const [newProducts, setNewProducts] = useState<ProductInfo[]>([]);
  const publicDemo = useSyncExternalStore(subscribeToHostname, readPublicDemo, () => false);

  const loadJobs = useCallback(async () => {
    try {
      const response = await fetch(`${API}/api/jobs`, { cache: "no-store" });
      if (!response.ok) throw new Error("后台未响应");
      const payload = await response.json();
      setJobs(payload.jobs ?? []);
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }, []);

  const loadJob = useCallback(async (jobId: string) => {
    const response = await fetch(`${API}/api/jobs/${jobId}`, { cache: "no-store" });
    if (!response.ok) throw new Error("任务读取失败");
    const payload = await response.json();
    setActiveIntent(payload.intent);
    setActiveJob(payload);
    return payload as Job;
  }, []);

  useEffect(() => {
    if (publicDemo) return;
    Promise.all([
      fetch(`${API}/api/health`, { cache: "no-store" }),
      fetch(`${API}/api/catalog`, { cache: "no-store" }),
      fetch(`${API}/api/jobs`, { cache: "no-store" }),
    ])
      .then(async ([health, catalogResponse, jobsResponse]) => {
        if (!health.ok || !catalogResponse.ok || !jobsResponse.ok) throw new Error("后台未响应");
        setCatalog(await catalogResponse.json());
        const payload = await jobsResponse.json();
        setJobs(payload.jobs ?? []);
        setBackendOnline(true);
      })
      .catch(() => setBackendOnline(false));
  }, [publicDemo]);

  useEffect(() => {
    if (!activeJob || FINAL_STATES.has(activeJob.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const updated = await loadJob(activeJob.job_id);
        if (FINAL_STATES.has(updated.status)) loadJobs();
      } catch {
        setMessage("任务仍在本机运行，但暂时无法刷新状态。");
      }
    }, 1800);
    return () => window.clearInterval(timer);
  }, [activeJob, loadJob, loadJobs]);

  const currentIntent = useMemo(
    () => INTENTS.find((item) => item.id === activeIntent),
    [activeIntent],
  );

  function resetUpload() {
    setUploadId("");
    setUploadSummary(null);
    setNewProducts([]);
    setFields((current) => {
      const next = { ...current };
      delete next.report_source_path;
      delete next.upload_id;
      delete next.product_source_file;
      return next;
    });
  }

  function chooseIntent(intent: Intent) {
    setActiveIntent(intent);
    setFields({ marketplace: "US" });
    setActiveJob(null);
    setMessage("");
    setUploadId("");
    setUploadSummary(null);
    setNewInputMode("manual");
    setNewProducts([]);
    window.setTimeout(() => document.getElementById("work-panel")?.scrollIntoView({ block: "start" }), 20);
  }

  async function refreshUploadSummary(currentUploadId: string) {
    const response = await fetch(`${API}/api/uploads/${currentUploadId}/summary`, { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "表格识别失败");
    const summary = payload as UploadSummary;
    setUploadSummary(summary);
    setFields((current) => {
      const next = { ...current, upload_id: currentUploadId };
      if (summary.paths.reports) next.report_source_path = summary.paths.reports;
      if (summary.recognized_product?.fields) {
        next.product_source_file = summary.recognized_product.source_file;
      }
      return next;
    });
    if (summary.recognized_product?.products?.length) {
      setNewProducts(summary.recognized_product.products);
      setFields((current) => ({
        marketplace: summary.recognized_product?.products[0]?.marketplace || current.marketplace || "US",
        upload_id: currentUploadId,
        product_source_file: summary.recognized_product?.source_file || "",
      }));
    }
    return summary;
  }

  async function uploadFiles(fileList: FileList | null, role: "new_product" | "reports") {
    if (!fileList?.length) return;
    const selectedFiles = Array.from(fileList).filter((file) => /\.(xlsx|xlsm|csv|tsv)$/i.test(file.name));
    if (!selectedFiles.length) {
      setMessage("所选内容中没有 XLSX、XLSM、CSV 或 TSV 表格。");
      return;
    }
    setUploading(true);
    setMessage("");
    let currentUploadId = uploadId;
    try {
      for (const file of selectedFiles) {
        const headers: Record<string, string> = {
          "Content-Type": "application/octet-stream",
          "X-Upload-Role": role,
          "X-File-Name": encodeURIComponent(file.name),
        };
        if (currentUploadId) headers["X-Upload-Id"] = currentUploadId;
        const response = await fetch(`${API}/api/uploads`, { method: "POST", headers, body: file });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || `上传失败: ${file.name}`);
        currentUploadId = payload.upload_id;
        setUploadId(currentUploadId);
      }
      await refreshUploadSummary(currentUploadId);
    } catch (error) {
      if (currentUploadId) {
        try {
          await refreshUploadSummary(currentUploadId);
        } catch {
          // Preserve the original upload error; the task can be reset from the page.
        }
      }
      setMessage(error instanceof Error ? error.message : "上传失败");
    } finally {
      setUploading(false);
    }
  }

  async function submitJob(event: FormEvent) {
    event.preventDefault();
    if (!activeIntent) return;
    if (publicDemo) {
      setMessage("公开演示版只展示操作流程；请在安装了 V2.1 运行时的本地电脑上处理真实数据。");
      return;
    }
    if (["OLD_PRODUCT_OPTIMIZATION", "AGGREGATE_REPORTS"].includes(activeIntent) && !fields.report_source_path) {
      setMessage("请先上传广告报表文件。");
      return;
    }
    if (activeIntent === "NEW_PRODUCT_PROMOTION" && newProducts.length === 0) {
      setMessage(newInputMode === "manual" ? "请先点击“添加到产品清单”，至少保存一个ASIN。" : "请先上传并识别产品表格。");
      return;
    }
    setSubmitting(true);
    setMessage("");
    try {
      const submittedFields = activeIntent === "OLD_PRODUCT_OPTIMIZATION"
        ? { ...fields, workflow_phase: "AGGREGATE_ONLY" }
        : activeIntent === "NEW_PRODUCT_PROMOTION"
          ? {
              ...fields,
              ...newProducts[0],
              input_mode: uploadSummary?.recognized_product ? "import" : newInputMode,
              product_count: String(newProducts.length),
              products_json: JSON.stringify(newProducts),
            }
          : fields;
      const response = await fetch(`${API}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ intent: activeIntent, fields: submittedFields }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "任务提交失败");
      const job = await loadJob(payload.job_id);
      setActiveJob(job);
      loadJobs();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "任务提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  async function generateRecommendations(jobId: string) {
    setSubmitting(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/api/jobs/${jobId}/recommendations`, { method: "POST" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "广告建议任务创建失败");
      setActiveJob(payload);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "广告建议任务创建失败");
    } finally {
      setSubmitting(false);
    }
  }

  const workflowPhase = activeJob?.request?.fields?.workflow_phase;
  const stageIndex = activeJob
    ? workflowPhase === "AGGREGATED" || workflowPhase === "AGGREGATION_BLOCKED"
      ? 1
      : FINAL_STATES.has(activeJob.status)
        ? STAGES.length - 1
        : Math.max(0, STAGES.findIndex(([status]) => status === activeJob.stage || status === activeJob.status))
    : 0;

  return (
    <main className="app-shell">
      <aside className="side-nav" aria-label="广告运营导航">
        <a className="brand" href="#top" aria-label="返回广告运营台顶部">
          <span className="brand-mark">L</span>
          <span><strong>陆遥广告智能体</strong><small>RUG AD OPERATIONS</small></span>
          <b>V2.1</b>
        </a>

        <div className="nav-context">
          <span>运营空间</span>
          <strong>Amazon · 美国站</strong>
          <small>Rugs · 本机工作区</small>
        </div>

        <nav>
          <p>广告工作台</p>
          <a className={!activeIntent ? "active" : ""} href="#top"><span>⌂</span>运营总览</a>
          {INTENTS.map((intent) => (
            <button className={activeIntent === intent.id ? "active" : ""} key={intent.id} onClick={() => chooseIntent(intent.id)} type="button">
              <span>{intent.number}</span>{intent.title}
            </button>
          ))}
        </nav>

        <div className="nav-footer">
          <div><span className={`online-dot ${backendOnline === false ? "offline" : ""}`} /><strong>{publicDemo ? "公开演示模式" : backendOnline ? "本机服务正常" : backendOnline === false ? "后台未启动" : "正在连接"}</strong></div>
          <small>所有结果需人工确认</small>
        </div>
      </aside>

      <div className="app-content">
        <header className="topbar">
          <div className="breadcrumb"><span>广告运营系统</span><i>›</i><strong>{currentIntent?.title ?? "运营驾驶舱"}</strong></div>
          <div className="mobile-brand"><span className="brand-mark">L</span><strong>陆遥广告智能体</strong></div>
          <SystemSwitcher replenishmentHref={publicDemo ? PUBLIC_REPLENISHMENT_URL : LOCAL_REPLENISHMENT_URL} />
          <div className="system-state">
            <span className={`online-dot ${backendOnline === false ? "offline" : ""}`} />
            {publicDemo ? "公开演示版" : backendOnline === null ? "正在连接" : backendOnline ? "本机已连接" : "后台未启动"}
            <span className="system-badge">{publicDemo ? "本地执行关闭" : "只生成建议"}</span>
          </div>
        </header>

        <div className="page-content">
          <section className="hero" id="top">
            <div className="hero-copy">
              <div className="hero-title-line"><h1>广告运营驾驶舱</h1><span>Amazon US · Rugs</span></div>
              <p>输入产品信息或上传广告报表，直接查看广告架构、优化方案和可下载结果。</p>
            </div>
            <div className="guardrails"><span>Rug 专用</span><span>数据仅在本机</span><span>Amazon 自动执行关闭</span></div>
          </section>

          {publicDemo && (
            <section className="demo-notice" role="status">
              <span>PUBLIC DEMO</span>
              <div><strong>这是可分享的流程演示版</strong><p>其他电脑可以浏览全部入口和操作界面；真实数据上传、分析和结果下载只在安装了 V2.1 运行时的本地电脑上开放。</p></div>
            </section>
          )}

          <section className="intent-section" aria-labelledby="intent-heading">
            <div className="section-heading">
              <div><p className="eyebrow">今日工作入口</p><h2 id="intent-heading">选择要处理的广告任务</h2></div>
              <p>选择一个任务，填写或上传页面要求的数据即可。</p>
            </div>
            <div className="intent-grid">
              {INTENTS.map((intent) => (
                <button
                  className={`intent-card ${intent.accent} ${activeIntent === intent.id ? "selected" : ""}`}
                  key={intent.id}
                  onClick={() => chooseIntent(intent.id)}
                  type="button"
                >
                  <div><span className="intent-number">{intent.number}</span><span className="intent-arrow">→</span></div>
                  <strong>{intent.title}</strong><em>{intent.subtitle}</em><small>{intent.description}</small>
                </button>
              ))}
            </div>
          </section>

          {activeIntent && currentIntent && (
            <section className="work-shell" id="work-panel">
              <div className="work-main">
                <div className="work-title">
                  <span>{currentIntent.number}</span>
                  <div><p className="eyebrow">当前任务</p><h2>{currentIntent.title}</h2><small>{currentIntent.description}</small></div>
                </div>

                {!activeJob ? (
                  <form onSubmit={submitJob} className="job-form">
                    {activeIntent === "NEW_PRODUCT_PROMOTION" && (
                      <NewProductForm
                        key={`${newInputMode}-${uploadId}`}
                        catalog={catalog}
                        fields={fields}
                        setFields={setFields}
                        mode={newInputMode}
                        setMode={setNewInputMode}
                        uploadSummary={uploadSummary}
                        uploading={uploading}
                        uploadFiles={uploadFiles}
                        resetUpload={resetUpload}
                        readOnly={publicDemo}
                        products={newProducts}
                        setProducts={setNewProducts}
                      />
                    )}
                    {(activeIntent === "OLD_PRODUCT_OPTIMIZATION" || activeIntent === "AGGREGATE_REPORTS") && (
                      <ReportForm
                        fields={fields}
                        setFields={setFields}
                        uploadSummary={uploadSummary}
                        uploading={uploading}
                        uploadFiles={uploadFiles}
                        resetUpload={resetUpload}
                        aggregateOnly={activeIntent === "AGGREGATE_REPORTS"}
                        readOnly={publicDemo}
                      />
                    )}
                    {activeIntent === "WEEKLY_REVIEW" && (
                      <div className="weekly-ready">
                        <span>W</span><div><strong>读取本周阈值检查结果</strong><p>检查历史数据是否达到候选阈值生成门槛；不会直接修改当前阈值。</p></div>
                      </div>
                    )}
                    {message && <p className="form-error">{message}</p>}
                    <div className="form-actions">
                      <button className="secondary-button" type="button" onClick={() => setActiveIntent(null)}>取消</button>
                      <button className="primary-button" type="submit" disabled={submitting || uploading || backendOnline === false || publicDemo}>
                        {submitting
                          ? "正在创建任务…"
                          : activeIntent === "WEEKLY_REVIEW"
                            ? "检查本周建议"
                            : activeIntent === "OLD_PRODUCT_OPTIMIZATION" || activeIntent === "AGGREGATE_REPORTS"
                              ? "聚合数据报表"
                              : `生成 ${newProducts.length || 1} 个ASIN广告架构`}
                      </button>
                    </div>
                  </form>
                ) : (
                  <JobResult
                    job={activeJob}
                    stageIndex={stageIndex}
                    generating={submitting}
                    onGenerateRecommendations={() => generateRecommendations(activeJob.job_id)}
                    onNew={() => { setActiveJob(null); setMessage(""); }}
                  />
                )}
              </div>

              <aside className="recent-panel">
                <div className="recent-heading"><div><p className="eyebrow">任务记录</p><h3>最近任务</h3></div><button onClick={loadJobs} type="button" disabled={publicDemo}>刷新</button></div>
                {jobs.length === 0 ? <p className="empty-copy">还没有任务记录。</p> : jobs.slice(0, 8).map((job) => (
                  <button className="recent-job" key={job.job_id} onClick={() => loadJob(job.job_id)} type="button">
                    <span className={`job-state ${job.status.toLowerCase()}`}>{jobStatusLabel(job.status)}</span>
                    <strong>{intentTitle(job.intent)}</strong><small>{formatTime(job.created_at)}</small>
                  </button>
                ))}
                <div className="safety-note"><strong>使用提示</strong><p>所有方案只供人工确认，不会自动修改亚马逊广告。</p></div>
              </aside>
            </section>
          )}

          <footer>
            <span>陆遥广告智能体 V2.1 · V2.0规则集</span>
            <span>{publicDemo ? "公开演示版 · 本地数据能力未开放" : "本地主版本 · 数据保存在本机 · 结果需人工确认"}</span>
            {!publicDemo && <a href={PUBLIC_DEMO_URL} target="_blank" rel="noreferrer">分享演示版 ↗</a>}
          </footer>
        </div>
      </div>
    </main>
  );
}

function NewProductForm({
  catalog,
  fields,
  setFields,
  mode,
  setMode,
  uploadSummary,
  uploading,
  uploadFiles,
  resetUpload,
  readOnly,
  products,
  setProducts,
}: {
  catalog: Catalog | null;
  fields: Record<string, string>;
  setFields: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  mode: "manual" | "import";
  setMode: (mode: "manual" | "import") => void;
  uploadSummary: UploadSummary | null;
  uploading: boolean;
  uploadFiles: (files: FileList | null, role: "new_product" | "reports") => Promise<void>;
  resetUpload: () => void;
  readOnly: boolean;
  products: ProductInfo[];
  setProducts: React.Dispatch<React.SetStateAction<ProductInfo[]>>;
}) {
  const update = (name: string, value: string) => setFields((current) => ({ ...current, [name]: value }));
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [draftError, setDraftError] = useState("");
  const selectedScenes = (fields.scene_tags || "").split(",").filter(Boolean);
  const showProductFields = mode === "manual" || editingIndex !== null;
  const manualLimitReached = mode === "manual" && products.length >= 10 && editingIndex === null;
  const optionLabel = (field: string, value: string) => (
    catalog?.fields[field]?.find((option) => option.value === value)?.label || value || "未填写"
  );
  const toggleScene = (value: string) => {
    const next = selectedScenes.includes(value)
      ? selectedScenes.filter((item) => item !== value)
      : [...selectedScenes, value];
    update("scene_tags", next.join(","));
  };

  const clearDraft = (marketplace = "US") => {
    setFields((current) => ({
      marketplace,
      ...(current.upload_id ? { upload_id: current.upload_id } : {}),
      ...(current.product_source_file ? { product_source_file: current.product_source_file } : {}),
    }));
  };

  const saveProduct = () => {
    const asin = String(fields.asin || "").trim().toUpperCase();
    const required = [
      ["ASIN", asin],
      ["站点", fields.marketplace],
      ["尺寸", fields.size_spec],
      ["地毯类型", fields.rug_type],
      ["日订单目标", fields.order_target_daily],
    ];
    const missing = required.filter(([, value]) => !String(value || "").trim()).map(([label]) => label);
    if (missing.length) {
      setDraftError(`请补齐：${missing.join("、")}`);
      return;
    }
    if (!/^B0[A-Z0-9]{8}$/.test(asin)) {
      setDraftError("ASIN必须是10位并以B0开头，例如 B0ABC12345。");
      return;
    }
    if (!(Number(fields.order_target_daily) > 0)) {
      setDraftError("日订单目标必须大于0。");
      return;
    }
    if (manualLimitReached) {
      setDraftError("手动录入最多10个ASIN；超过10个请使用表格上传。");
      return;
    }
    const duplicateIndex = products.findIndex((product, index) => product.asin === asin && index !== editingIndex);
    if (duplicateIndex >= 0) {
      setDraftError(`ASIN ${asin} 已在第${duplicateIndex + 1}条产品信息中，请直接编辑原记录。`);
      return;
    }
    const product: ProductInfo = {
      asin,
      marketplace: String(fields.marketplace || "US").trim().toUpperCase(),
      size_spec: String(fields.size_spec || ""),
      rug_type: String(fields.rug_type || ""),
      order_target_daily: String(fields.order_target_daily || ""),
      sku: String(fields.sku || "").trim(),
      style: String(fields.style || ""),
      color: String(fields.color || ""),
      material: String(fields.material || ""),
      scene_tags: String(fields.scene_tags || ""),
      target_cpa: String(fields.target_cpa || ""),
      daily_budget: String(fields.daily_budget || ""),
    };
    setProducts((current) => {
      if (editingIndex === null) return [...current, product];
      return current.map((item, index) => index === editingIndex ? product : item);
    });
    setEditingIndex(null);
    setDraftError("");
    clearDraft(product.marketplace);
  };

  const editProduct = (index: number) => {
    setFields((current) => ({
      ...products[index],
      ...(current.upload_id ? { upload_id: current.upload_id } : {}),
      ...(current.product_source_file ? { product_source_file: current.product_source_file } : {}),
    }));
    setEditingIndex(index);
    setDraftError("");
  };

  const removeProduct = (index: number) => {
    setProducts((current) => current.filter((_, itemIndex) => itemIndex !== index));
    if (editingIndex === index) {
      setEditingIndex(null);
      clearDraft();
    } else if (editingIndex !== null && editingIndex > index) {
      setEditingIndex(editingIndex - 1);
    }
  };

  return (
    <>
      <div className="mode-switch" aria-label="新品信息录入方式">
        <button className={mode === "manual" ? "active" : ""} type="button" onClick={() => setMode("manual")}>手动选择</button>
        <button className={mode === "import" ? "active" : ""} type="button" onClick={() => setMode("import")}>导入产品表格</button>
      </div>

      {mode === "import" && (
        <div className="upload-card product-upload">
          <div><span className="upload-kicker">产品字段识别</span><h3>上传一张新品表格</h3><p>超过10个ASIN请使用此入口，单次最多100个。支持 XLSX、XLSM、CSV、TSV；系统逐行识别 ASIN、SKU、尺寸、类型、风格、颜色、材质、场景和目标数据。</p></div>
          <label className="upload-button">
            {uploading ? "正在识别…" : uploadSummary?.recognized_product ? "已识别产品表" : "选择产品表格"}
            <input type="file" accept=".xlsx,.xlsm,.csv,.tsv" onChange={(event) => uploadFiles(event.target.files, "new_product")} disabled={readOnly || uploading || Boolean(uploadSummary?.recognized_product)} />
          </label>
          {uploadSummary?.recognized_product && (
            <div className="recognition-result">
              <strong>已从 {uploadSummary.recognized_product.source_file} 识别产品清单</strong>
              <span>{uploadSummary.recognized_product.products.length} 个ASIN</span>
              <button type="button" onClick={resetUpload}>换一张表</button>
            </div>
          )}
          {uploadSummary?.warnings.map((warning) => <p className="inline-warning" key={warning}>{warning}</p>)}
        </div>
      )}

      {showProductFields && <>
      <div className="form-section-heading"><span>{editingIndex === null ? "添加产品基础信息" : `编辑第 ${editingIndex + 1} 条产品信息`}</span><small>{mode === "import" ? "从表格清单中修改" : `手动录入 · 已添加 ${products.length}/10`}</small></div>
      <div className={`field-grid ${mode === "import" ? "generated-product-fields" : ""}`}>
        <TextField label="ASIN" value={fields.asin} required={products.length === 0} placeholder="例如 B0XXXXXXXX" onChange={(value) => update("asin", value.toUpperCase())} />
        <TextField label="SKU" value={fields.sku} placeholder="内部 SKU，可不填" onChange={(value) => update("sku", value)} />
        <TextField label="站点" value={fields.marketplace} required={products.length === 0} placeholder="US" onChange={(value) => update("marketplace", value.toUpperCase())} />
        <CatalogSelect label="尺寸" field="size_spec" value={fields.size_spec} catalog={catalog} required={products.length === 0} onChange={(value) => update("size_spec", value)} />
        <CatalogSelect label="地毯类型" field="rug_type" value={fields.rug_type} catalog={catalog} required={products.length === 0} onChange={(value) => update("rug_type", value)} />
        <CatalogSelect label="风格" field="style" value={fields.style} catalog={catalog} onChange={(value) => update("style", value)} />
        <CatalogSelect label="颜色" field="color" value={fields.color} catalog={catalog} onChange={(value) => update("color", value)} />
        <CatalogSelect label="材质" field="material" value={fields.material} catalog={catalog} onChange={(value) => update("material", value)} />
        <TextField label="日订单目标" value={fields.order_target_daily} type="number" required={products.length === 0} placeholder="例如 3" onChange={(value) => update("order_target_daily", value)} />
        <TextField label="目标 CPA" value={fields.target_cpa} type="number" placeholder="例如 12.5" onChange={(value) => update("target_cpa", value)} />
        <TextField label="期望日预算" value={fields.daily_budget} type="number" placeholder="例如 50" onChange={(value) => update("daily_budget", value)} />
        <div className="wide scene-field">
          <span>场景标签</span>
          <div className="choice-chips">
            {(catalog?.fields.scene_tags ?? []).map((option) => (
              <button className={selectedScenes.includes(option.value) ? "selected" : ""} key={option.value} type="button" onClick={() => toggleScene(option.value)}>
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </div>
      {draftError && <p className="inline-form-error" role="alert">{draftError}</p>}
      <div className="product-draft-actions">
        {editingIndex !== null && <button className="secondary-button" type="button" onClick={() => { setEditingIndex(null); setDraftError(""); clearDraft(); }}>取消编辑</button>}
        <button className="add-product-button" type="button" onClick={saveProduct} disabled={readOnly || manualLimitReached}>
          {editingIndex === null ? `＋ 添加到产品清单（${products.length}/10）` : "保存修改"}
        </button>
      </div>
      </>}

      {products.length > 0 && (
        <section className="product-queue" aria-label="待设计产品清单">
          <div className="product-queue-heading">
            <div><span>PRODUCT QUEUE</span><h3>待设计产品清单</h3><p>本次任务会按每个ASIN的独立属性分别生成架构，再合并到同一份两表工作簿。</p></div>
            <strong>{products.length}<small>个 ASIN</small></strong>
          </div>
          <div className="product-queue-list">
            {products.map((product, index) => (
              <article className={editingIndex === index ? "editing" : ""} key={`${product.asin}-${index}`}>
                <span className="product-index">{String(index + 1).padStart(2, "0")}</span>
                <div className="product-identity"><strong>{product.asin}</strong><small>{product.sku || "未填写SKU"}</small></div>
                <div className="product-attributes">
                  <span>{optionLabel("size_spec", product.size_spec)}</span>
                  <span>{optionLabel("rug_type", product.rug_type)}</span>
                  {product.material && <span>{optionLabel("material", product.material)}</span>}
                  {product.style && <span>{optionLabel("style", product.style)}</span>}
                  {product.color && <span>{optionLabel("color", product.color)}</span>}
                </div>
                <div className="product-row-actions">
                  <button type="button" onClick={() => editProduct(index)}>编辑</button>
                  <button className="danger" type="button" onClick={() => removeProduct(index)}>删除</button>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {mode === "manual" && products.length >= 10 && (
        <div className="manual-limit-notice" role="status">
          <span>10 / 10</span>
          <div><strong>手动录入已达到10个ASIN上限</strong><p>如果还要继续添加，请整理到产品表格中批量上传；系统会逐行识别，不需要重复手动填写。</p></div>
          <button type="button" onClick={() => setMode("import")}>采用表格上传</button>
        </div>
      )}
    </>
  );
}

function ReportForm({
  fields,
  setFields,
  uploadSummary,
  uploading,
  uploadFiles,
  resetUpload,
  aggregateOnly,
  readOnly,
}: {
  fields: Record<string, string>;
  setFields: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  uploadSummary: UploadSummary | null;
  uploading: boolean;
  uploadFiles: (files: FileList | null, role: "new_product" | "reports") => Promise<void>;
  resetUpload: () => void;
  aggregateOnly: boolean;
  readOnly: boolean;
}) {
  const update = (name: string, value: string) => setFields((current) => ({ ...current, [name]: value }));
  const [dragging, setDragging] = useState(false);
  const reportFiles = uploadSummary?.files.filter((file) => file.role === "reports") ?? [];
  const suggestedAsins = uploadSummary?.suggested_asins ?? [];
  const asinSummary = suggestedAsins.length > 8
    ? `${suggestedAsins.slice(0, 8).join("、")} 等 ${suggestedAsins.length} 个`
    : suggestedAsins.join("、");
  return (
    <>
      <div className="field-grid compact-fields">
        <TextField
          label={aggregateOnly ? "指定 ASIN（可选）" : "要分析的 ASIN（可选）"}
          value={fields.asin}
          wide
          placeholder="留空＝自动处理报表中全部ASIN；多个ASIN用逗号分隔"
          help="填写一个ASIN只分析该商品；填写多个则分别生成多个ASIN方案。"
          onChange={(value) => update("asin", value.toUpperCase())}
        />
        <TextField label="站点" value={fields.marketplace} required placeholder="US" onChange={(value) => update("marketplace", value.toUpperCase())} />
      </div>

      {!aggregateOnly && (
        <section className="data-requirements" aria-label="SP广告优化数据要求">
          <div className="requirements-heading">
          <div><span>需要上传</span><h3>一次上传这些报表</h3></div>
            <small>报表不必每类只有一张；7 / 14 / 30 天重复窗口会在本地去重。</small>
          </div>
          <div className="requirements-grid">
            <div><b>01</b><span>SP 搜索词报告</span><small>汇总 + 每日明细</small></div>
            <div><b>02</b><span>SP 投放对象报告</span><small>关键词 / ASIN Target</small></div>
            <div><b>03</b><span>SP 广告商品报告</span><small>广告 ASIN 层</small></div>
            <div><b>04</b><span>SP 广告位报告</span><small>TOS / ROS / PP</small></div>
            <div><b>05</b><span>Campaign / Ad Group 设置表</span><small>预算、状态、投放类型</small></div>
            <div><b>06</b><span>小时预算与花费</span><small>可选，用于断流诊断</small></div>
          </div>
          <p><strong>要生成可直接定位后台的修改行，还需：</strong>Campaign ID、Ad Group ID、Target ID、当前库存/利润和本次经营目标。缺少时仍可生成诊断与架构候选，但不会伪造 ID 或可执行值。</p>
        </section>
      )}

      <div
        className={`report-drop-zone ${dragging ? "dragging" : ""} ${reportFiles.length ? "has-files" : ""}`}
        onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
        onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
        onDragLeave={(event) => { event.preventDefault(); if (event.currentTarget === event.target) setDragging(false); }}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!readOnly && !uploading && !reportFiles.length) uploadFiles(event.dataTransfer.files, "reports");
        }}
      >
        <div className="drop-orbit" aria-hidden="true"><span /><i /><b /></div>
        <div className="drop-copy">
          <span className="upload-kicker">广告报表上传</span>
          <h3>{dragging ? "松开即可载入报表" : reportFiles.length ? `已载入 ${reportFiles.length} 个广告报表` : "拖拽广告报表到这里"}</h3>
          <p>支持一次拖入多个 XLSX、XLSM、CSV、TSV，也可以通过按钮选择文件或整个文件夹。原始报表只保存在本机。</p>
        </div>
        <div className="upload-actions">
          <label className="upload-button">
            {uploading ? "正在上传…" : reportFiles.length ? "报表已就绪" : "选择多个报表文件"}
            <input type="file" multiple accept=".xlsx,.xlsm,.csv,.tsv" onChange={(event) => uploadFiles(event.target.files, "reports")} disabled={readOnly || uploading || reportFiles.length > 0} />
          </label>
          <label className="upload-button secondary-upload">
            选择整个文件夹
            <input type="file" multiple {...{ webkitdirectory: "", directory: "" }} onChange={(event) => uploadFiles(event.target.files, "reports")} disabled={readOnly || uploading || reportFiles.length > 0} />
          </label>
        </div>
      </div>

      {uploadSummary && (
        <div className="detected-panel">
          <div><span>上传文件</span><strong>{uploadSummary.files.length} 个</strong></div>
          <div><span>建议分析 ASIN</span><strong>{asinSummary || "暂未识别"}</strong></div>
          <div><span>自动数据周期</span><strong>{uploadSummary.period_start && uploadSummary.period_end ? `${uploadSummary.period_start} 至 ${uploadSummary.period_end}` : "暂未识别"}</strong></div>
          <button type="button" onClick={resetUpload}>重新选择全部文件</button>
          <ul>{uploadSummary.files.map((file) => <li key={`${file.role}-${file.name}`}><span>{file.name}</span><small>{formatBytes(file.size)}</small></li>)}</ul>
          {uploadSummary.warnings.map((warning) => <p className="inline-warning" key={warning}>{warning}</p>)}
        </div>
      )}
      <p className="auto-note">不需要填写开始日或结束日；后台只按上传表格中的日期列自动确定分析周期。</p>
    </>
  );
}

function TextField({
  label,
  value,
  onChange,
  placeholder,
  required = false,
  type = "text",
  wide = false,
  help,
}: {
  label: string;
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  type?: string;
  wide?: boolean;
  help?: string;
}) {
  return (
    <label className={wide ? "wide" : ""}>
      <span>{label}{required && <b> *</b>}</span>
      <input type={type} value={value ?? ""} placeholder={placeholder} required={required} step={type === "number" ? "any" : undefined} onChange={(event) => onChange(event.target.value)} />
      {help && <small>{help}</small>}
    </label>
  );
}

function CatalogSelect({
  label,
  field,
  value,
  catalog,
  required = false,
  onChange,
}: {
  label: string;
  field: string;
  value?: string;
  catalog: Catalog | null;
  required?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label>
      <span>{label}{required && <b> *</b>}</span>
      <select value={value ?? ""} required={required} disabled={!catalog} onChange={(event) => onChange(event.target.value)}>
        <option value="">{catalog ? `请选择${label}` : "正在读取本地属性库…"}</option>
        {(catalog?.fields[field] ?? []).map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}
      </select>
    </label>
  );
}

function DataProcessingWindow({ job }: { job: Job }) {
  const queued = job.status === "QUEUED";
  return (
    <div className="data-processing-window" role="status" aria-live="polite">
      <div className="processing-visual" aria-hidden="true">
        <div className="processing-grid" />
        <div className="data-core"><span>•••</span><i /><b /></div>
        <div className="scan-beam" />
      </div>
      <div className="processing-console">
        <div className="console-heading"><span>DATA PROCESSING</span><strong>{queued ? "已接收文件" : "正在聚合广告报表"}</strong></div>
        <p className="processing-note">请稍候。完成后会显示分析 ASIN、数据周期、问题提示和结果下载。</p>
      </div>
    </div>
  );
}

function ArtifactList({ job }: { job: Job }) {
  const phase = job.request?.fields?.workflow_phase;
  const artifacts = (job.result?.artifacts ?? []).filter((path) => {
    const name = path.split("/").pop() ?? path;
    if (/agents_context|preprocess|request|status|validation|\.log$/i.test(name)) return false;
    if (job.intent === "NEW_PRODUCT_PROMOTION") return /\.(xlsx|xlsm)$/i.test(name) && name.includes("广告架构");
    if (job.intent === "OLD_PRODUCT_OPTIMIZATION" && phase !== "AGGREGATED") return name.includes("SP广告优化方案") && /\.xlsx$/i.test(name);
    return true;
  });
  if (!artifacts.length) return null;
  return (
    <section className="result-section"><h3>下载结果</h3><div className="artifact-list">
      {artifacts.map((path) => <a href={artifactHref(job.job_id, path)} key={path} target="_blank" rel="noreferrer"><span>↓</span><div><strong>{path.split("/").pop()}</strong><small>点击下载完整结果</small></div></a>)}
    </div></section>
  );
}

function NewProductArchitecturePreview({ result }: { result: Result }) {
  const rows = result.new_product_architecture ?? [];
  return (
    <section className="result-section workbook-preview">
      <div className="preview-heading"><div><span>RESULT PREVIEW</span><h3>广告架构预览</h3></div><small>页面显示主要结果；完整内容请下载表格。</small></div>
      {rows.length ? (
        <div className="sheet-preview">
          <div className="sheet-title"><strong>新广告设置表</strong><span>{rows.length} 行有效数据</span></div>
          <div className="table-scroll"><table><thead><tr>
            <th>Campaign 名称</th><th>广告组名称</th><th>ASIN</th><th>匹配方式</th><th>预算</th><th>Bid</th><th>投放策略</th><th>广告位</th><th>角色</th><th>投放对象</th><th>精准否定</th>
          </tr></thead><tbody>
            {rows.map((row, index) => <tr key={`${row.asin}-${row.ad_group_name}-${index}`}>
              <td>{row.campaign_name}</td><td>{row.ad_group_name}</td><td>{row.asin}</td><td>{row.match_type}</td><td>{String(row.daily_budget ?? "待人工配置")}</td><td>{String(row.bid ?? "待人工配置")}</td><td>{row.bidding_strategy}</td><td>{row.placement}</td><td>{row.role}</td><td>{row.target}</td><td>{row.negative_exact}</td>
            </tr>)}
          </tbody></table></div>
        </div>
      ) : (
        <div className="empty-sheet-state"><strong>当前没有可用架构</strong><p>请查看“问题提示”并补充所需数据。</p></div>
      )}
    </section>
  );
}

function recommendationAsin(recommendation: Result["recommendations"][number]) {
  const match = `${recommendation.action} ${recommendation.reason} ${recommendation.evidence}`.toUpperCase().match(/B0[A-Z0-9]{8}/);
  return match?.[0] ?? "待定位";
}

function SPOptimizationPreview({ result }: { result: Result }) {
  if (!result.recommendations?.length) return null;
  return (
    <section className="result-section sp-plan-preview">
      <div className="preview-heading"><div><span>RESULT PREVIEW</span><h3>SP 广告优化方案</h3></div><small>页面显示主要结果；完整方案请下载表格。</small></div>
      <div className="table-scroll"><table><thead><tr><th>优先级</th><th>ASIN</th><th>优化动作</th><th>需要关注</th></tr></thead><tbody>
        {result.recommendations.map((item, index) => <tr key={`${item.action}-${index}`}><td>{item.priority}</td><td>{recommendationAsin(item)}</td><td>{item.action}</td><td>{item.risk || "需人工确认"}</td></tr>)}
      </tbody></table></div>
    </section>
  );
}

function ProblemPanel({ job, result }: { job: Job; result: Result }) {
  const validatorProblems = (job.validation?.findings ?? [])
    .filter((item) => item.level === "BLOCK")
    .map((item) => {
      if (item.code === "MATCH_TYPE_DATA_PENDING") return "相关性表或搜索词月搜索量表尚未补充，当前不会生成词组或广泛投放。";
      if (item.code === "RESULT_NOT_READY") return "当前结果尚未达到可确认状态，请按提示补充数据后重新生成。";
      if (["PREPROCESSING_DATA_BLOCKED", "BLOCKED_DATA_PROMOTED"].includes(item.code)) return "上传数据未通过检查，请按提示修正后重新处理。";
      return "系统结果检查未通过，请重新生成；如仍失败，请联系维护人员。";
    });
  const problems = Array.from(new Set([
    ...(job.preprocessing?.issues ?? []),
    ...(result.missing_inputs ?? []),
    ...validatorProblems,
    ...(job.error ? [job.error] : []),
  ].map((item) => String(item || "").trim()).filter(Boolean)));
  if (!problems.length) return null;
  return (
    <section className="result-section warning-list" aria-label="问题提示">
      <h3>问题提示</h3>
      <ul>{problems.map((item) => <li key={item}>{item}</li>)}</ul>
    </section>
  );
}

function JobResult({
  job,
  stageIndex,
  generating,
  onGenerateRecommendations,
  onNew,
}: {
  job: Job;
  stageIndex: number;
  generating: boolean;
  onGenerateRecommendations: () => void;
  onNew: () => void;
}) {
  const result = job.result;
  const phase = job.request?.fields?.workflow_phase;
  const isOldProduct = job.intent === "OLD_PRODUCT_OPTIMIZATION";
  const aggregationRunning = isOldProduct && !FINAL_STATES.has(job.status) && phase === "AGGREGATE_ONLY";
  const aggregationReady = isOldProduct && job.status === "COMPLETED" && phase === "AGGREGATED";
  const aggregationPhase = isOldProduct && ["AGGREGATE_ONLY", "AGGREGATED", "AGGREGATION_BLOCKED"].includes(phase ?? "");
  const progressStages = aggregationPhase ? AGGREGATION_STAGES : STAGES;
  const progressIndex = aggregationPhase
    ? phase === "AGGREGATED" || phase === "AGGREGATION_BLOCKED"
      ? AGGREGATION_STAGES.length - 1
      : Math.max(0, AGGREGATION_STAGES.findIndex(([status]) => status === job.status))
    : stageIndex;
  const failed = job.status === "FAILED" || job.status === "BLOCKED" || result?.status !== "READY_FOR_HUMAN_REVIEW";
  return (
    <div className="job-result">
      <div className={`progress-row ${aggregationPhase ? "three-stage" : ""}`}>
        {progressStages.map(([status, label], index) => (
          <div className={`progress-step ${index <= progressIndex ? "done" : ""}`} key={status}>
            <span>{index < progressIndex ? "✓" : index + 1}</span><small>{label}</small>
          </div>
        ))}
      </div>

      {aggregationRunning ? (
        <DataProcessingWindow job={job} />
      ) : !FINAL_STATES.has(job.status) ? (
        <div className="processing-card"><span className="spinner" /><div><h3>{phase === "ANALYSIS_REQUESTED" ? "正在生成 SP 广告优化方案" : STAGES[stageIndex]?.[1] ?? "正在处理"}</h3><p>请留在此页等待，完成后会自动显示结果。</p></div></div>
      ) : aggregationReady && result ? (
        <>
          <div className="aggregation-ready">
            <div className="aggregation-check">✓</div>
            <div className="aggregation-copy">
              <span>REPORTS READY</span>
              <h3>数据报表已经聚合完成</h3>
              <p>{result.executive_summary}</p>
            </div>
          </div>
          <div className="aggregation-metrics">
            <div><span>分析对象</span><strong>{job.preprocessing?.analysis_asins?.length ?? 0} 个 ASIN</strong></div>
            <div><span>数据周期</span><strong>{job.preprocessing?.auto_period?.start && job.preprocessing?.auto_period?.end ? `${job.preprocessing.auto_period.start} 至 ${job.preprocessing.auto_period.end}` : "由报表自动识别"}</strong></div>
          </div>
          <ProblemPanel job={job} result={result} />
          <ArtifactList job={job} />
          <div className="next-stage-panel">
            <div><span>下一步</span><h3>生成 SP 广告优化方案</h3><p>使用刚刚聚合的数据生成方案；不会重复聚合，也不会自动修改亚马逊广告。</p></div>
            <button className="primary-button next-stage-button" type="button" onClick={onGenerateRecommendations} disabled={generating}>
              {generating ? "正在启动分析…" : "生成 SP 广告优化方案"}
            </button>
          </div>
        </>
      ) : result ? (
        <>
          {job.intent === "NEW_PRODUCT_PROMOTION" ? (
            <>
              <NewProductArchitecturePreview result={result} />
              <ArtifactList job={job} />
              <ProblemPanel job={job} result={result} />
            </>
          ) : (
            <>
              <div className={`result-summary ${failed ? "warning" : ""}`}>
                <div><span className="result-status">结果</span><h3>{result.executive_summary}</h3></div>
                <div className="human-chip">需要人工确认</div>
              </div>
              {job.intent === "OLD_PRODUCT_OPTIMIZATION" && <SPOptimizationPreview result={result} />}
              {job.intent === "WEEKLY_REVIEW" && result.recommendations?.length > 0 && (
                <section className="result-section"><h3>本周建议</h3><div className="recommendation-list">
                  {result.recommendations.map((recommendation, index) => (
                    <article key={`${recommendation.action}-${index}`}><span>{recommendation.priority}</span><div><h4>{recommendation.action}</h4>{recommendation.risk && <p>{recommendation.risk}</p>}</div></article>
                  ))}
                </div></section>
              )}
              <ProblemPanel job={job} result={result} />
              <ArtifactList job={job} />
            </>
          )}
        </>
      ) : (
        <div className="processing-card error-card"><span>!</span><div><h3>任务未完成</h3><p>{job.error || "没有生成可用结果，请查看任务日志。"}</p></div></div>
      )}
      {FINAL_STATES.has(job.status) && !aggregationReady && <div className="form-actions"><button className="primary-button" type="button" onClick={onNew}>新建同类任务</button></div>}
      {aggregationReady && <div className="form-actions compact-action"><button className="secondary-button" type="button" onClick={onNew}>重新上传报表</button></div>}
    </div>
  );
}

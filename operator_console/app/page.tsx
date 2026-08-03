"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState, useSyncExternalStore } from "react";

const API = "http://127.0.0.1:8766";
const PUBLIC_DEMO_URL = "https://luyao-rug-ads-v2-20260804.louie847918852.chatgpt.site";

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
  };
  result?: Result;
  validation?: { outcome: string; findings: Array<{ level: string; code: string; message: string }> };
};

type Result = {
  status: string;
  executive_summary: string;
  recommendations: Array<{ priority: string; action: string; reason: string; evidence: string }>;
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
    title: "新品推广",
    subtitle: "选择属性或导入产品表",
    description: "属性识别 → 选词与结构 → Validator → 候选建议",
    accent: "orange",
  },
  {
    id: "OLD_PRODUCT_OPTIMIZATION",
    number: "02",
    title: "老品优化",
    subtitle: "上传报表，自动识别ASIN与日期",
    description: "本地聚合 → 多ASIN诊断 → 调整建议 → 人工确认",
    accent: "teal",
  },
  {
    id: "AGGREGATE_REPORTS",
    number: "03",
    title: "更新广告数据",
    subtitle: "多张报表合并为决策包",
    description: "自动识别报表、ASIN、周期并计算指标",
    accent: "blue",
  },
  {
    id: "WEEKLY_REVIEW",
    number: "04",
    title: "查看本周建议",
    subtitle: "检查阈值候选与证据",
    description: "只展示候选阈值，不会覆盖当前生效标准",
    accent: "violet",
  },
];

const STAGES = [
  ["QUEUED", "已接收"],
  ["PREPROCESSING", "本地聚合"],
  ["ANALYZING", "智能分析"],
  ["VALIDATING", "安全校验"],
  ["COMPLETED", "生成建议"],
] as const;

const AGGREGATION_STAGES = [
  ["QUEUED", "已接收"],
  ["PREPROCESSING", "本地聚合"],
  ["VALIDATING", "聚合校验"],
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
        Object.assign(next, summary.recognized_product.fields);
        next.product_source_file = summary.recognized_product.source_file;
      }
      return next;
    });
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
      setMessage("公开演示版只展示操作流程；请在安装了 V2.0 的本地电脑上处理真实数据。");
      return;
    }
    if (["OLD_PRODUCT_OPTIMIZATION", "AGGREGATE_REPORTS"].includes(activeIntent) && !fields.report_source_path) {
      setMessage("请先上传广告报表文件。");
      return;
    }
    setSubmitting(true);
    setMessage("");
    try {
      const submittedFields = activeIntent === "OLD_PRODUCT_OPTIMIZATION"
        ? { ...fields, workflow_phase: "AGGREGATE_ONLY" }
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
          <b>V2.0</b>
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
          <small>HUMAN_EXECUTION_ONLY</small>
        </div>
      </aside>

      <div className="app-content">
        <header className="topbar">
          <div className="breadcrumb"><span>广告运营系统</span><i>›</i><strong>{currentIntent?.title ?? "运营驾驶舱"}</strong></div>
          <div className="mobile-brand"><span className="brand-mark">L</span><strong>陆遥广告智能体</strong></div>
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
              <p>从产品资料与广告报表开始，本地 Python 负责确定性处理，Codex 按 V2.0 规则生成候选方案，最终由 Validator 和人工确认把关。</p>
            </div>
            <div className="guardrails"><span>Rug 专用</span><span>数据仅在本机</span><span>Amazon 自动执行关闭</span></div>
          </section>

          {publicDemo && (
            <section className="demo-notice" role="status">
              <span>PUBLIC DEMO</span>
              <div><strong>这是可分享的流程演示版</strong><p>其他电脑可以浏览全部入口和操作界面；报表上传、Python 聚合、Codex 分析与结果下载只在安装了 V2.0 的本地电脑运行。</p></div>
            </section>
          )}

          <section className="intent-section" aria-labelledby="intent-heading">
            <div className="section-heading">
              <div><p className="eyebrow">今日工作入口</p><h2 id="intent-heading">选择要处理的广告任务</h2></div>
              <p>每个入口会自动路由到对应规则、阈值和本地处理程序。</p>
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

          <section className="flow-card" aria-label="系统处理流程">
            <div><span>01</span><p><strong>网页输入</strong><small>选择属性或上传报表</small></p></div><i>→</i>
            <div><span>02</span><p><strong>本地 Python</strong><small>识别、去重与聚合</small></p></div><i>→</i>
            <div><span>03</span><p><strong>Codex + AGENTS</strong><small>按规则生成候选建议</small></p></div><i>→</i>
            <div><span>04</span><p><strong>Validator</strong><small>阻断越权并等待人工</small></p></div>
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
                              : "开始处理数据"}
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
                    <span className={`job-state ${job.status.toLowerCase()}`}>{job.status}</span>
                    <strong>{intentTitle(job.intent)}</strong><small>{formatTime(job.created_at)}</small>
                  </button>
                ))}
                <div className="safety-note"><strong>安全边界</strong><p>AUTO_PASS 只代表校验通过，不代表已在亚马逊后台执行。</p></div>
              </aside>
            </section>
          )}

          <footer>
            <span>陆遥广告智能体 V2.0</span>
            <span>{publicDemo ? "公开演示版 · 本地数据能力未开放" : "本地主版本 · 数据保存在本机 · HUMAN_EXECUTION_ONLY"}</span>
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
}) {
  const update = (name: string, value: string) => setFields((current) => ({ ...current, [name]: value }));
  const selectedScenes = (fields.scene_tags || "").split(",").filter(Boolean);
  const showProductFields = mode === "manual" || Boolean(uploadSummary?.recognized_product);
  const toggleScene = (value: string) => {
    const next = selectedScenes.includes(value)
      ? selectedScenes.filter((item) => item !== value)
      : [...selectedScenes, value];
    update("scene_tags", next.join(","));
  };

  return (
    <>
      <div className="mode-switch" aria-label="新品信息录入方式">
        <button className={mode === "manual" ? "active" : ""} type="button" onClick={() => setMode("manual")}>手动选择</button>
        <button className={mode === "import" ? "active" : ""} type="button" onClick={() => setMode("import")}>导入产品表格</button>
      </div>

      {mode === "import" && (
        <div className="upload-card product-upload">
          <div><span className="upload-kicker">产品字段识别</span><h3>上传一张新品表格</h3><p>支持 XLSX、XLSM、CSV、TSV。系统识别 ASIN、SKU、尺寸、类型、风格、颜色、材质、场景和目标数据，并自动填入下方选项。</p></div>
          <label className="upload-button">
            {uploading ? "正在识别…" : uploadSummary?.recognized_product ? "已识别产品表" : "选择产品表格"}
            <input type="file" accept=".xlsx,.xlsm,.csv,.tsv" onChange={(event) => uploadFiles(event.target.files, "new_product")} disabled={readOnly || uploading || Boolean(uploadSummary?.recognized_product)} />
          </label>
          {uploadSummary?.recognized_product && (
            <div className="recognition-result">
              <strong>已从 {uploadSummary.recognized_product.source_file} 自动填入</strong>
              <span>{Object.keys(uploadSummary.recognized_product.fields).length} 个字段</span>
              <button type="button" onClick={resetUpload}>换一张表</button>
            </div>
          )}
          {uploadSummary?.warnings.map((warning) => <p className="inline-warning" key={warning}>{warning}</p>)}
        </div>
      )}

      {showProductFields && <>
      <div className="form-section-heading"><span>产品基础信息</span><small>{mode === "import" ? "已根据表格生成，可人工修正" : "手动选择或填写"}</small></div>
      <div className={`field-grid ${mode === "import" ? "generated-product-fields" : ""}`}>
        <TextField label="ASIN" value={fields.asin} required placeholder="例如 B0XXXXXXXX" onChange={(value) => update("asin", value.toUpperCase())} />
        <TextField label="SKU" value={fields.sku} placeholder="内部 SKU，可不填" onChange={(value) => update("sku", value)} />
        <TextField label="站点" value={fields.marketplace} required placeholder="US" onChange={(value) => update("marketplace", value.toUpperCase())} />
        <CatalogSelect label="尺寸" field="size_spec" value={fields.size_spec} catalog={catalog} required onChange={(value) => update("size_spec", value)} />
        <CatalogSelect label="地毯类型" field="rug_type" value={fields.rug_type} catalog={catalog} required onChange={(value) => update("rug_type", value)} />
        <CatalogSelect label="风格" field="style" value={fields.style} catalog={catalog} onChange={(value) => update("style", value)} />
        <CatalogSelect label="颜色" field="color" value={fields.color} catalog={catalog} onChange={(value) => update("color", value)} />
        <CatalogSelect label="材质" field="material" value={fields.material} catalog={catalog} onChange={(value) => update("material", value)} />
        <TextField label="日订单目标" value={fields.order_target_daily} type="number" required placeholder="例如 3" onChange={(value) => update("order_target_daily", value)} />
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
      </>}
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
          <span className="upload-kicker">本地 Python 数据入口</span>
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
  const steps = [
    "校验文件完整性",
    "识别 ASIN 与日期窗口",
    "消除 7 / 14 / 30 天重叠",
    "计算 CTR · CPC · CVR · ACOS",
    "生成本地决策数据包",
  ];
  const activeStep = job.status === "QUEUED" ? 0 : job.status === "PREPROCESSING" ? 2 : 4;
  return (
    <div className="data-processing-window" role="status" aria-live="polite">
      <div className="processing-visual" aria-hidden="true">
        <div className="processing-grid" />
        <div className="data-core"><span>PY</span><i /><b /></div>
        <div className="scan-beam" />
      </div>
      <div className="processing-console">
        <div className="console-heading"><span>LOCAL DATA ENGINE</span><strong>本地 Python 正在聚合</strong></div>
        <div className="tech-lines">
          {steps.map((step, index) => (
            <div className={`tech-line ${index < activeStep ? "done" : index === activeStep ? "active" : ""}`} key={step}>
              <span>{index < activeStep ? "✓" : String(index + 1).padStart(2, "0")}</span>
              <p>{step}</p><i />
            </div>
          ))}
        </div>
        <p className="processing-note">处理状态来自本机后台；动画只用于展示处理阶段，不代表虚构进度。</p>
      </div>
    </div>
  );
}

function ArtifactList({ job }: { job: Job }) {
  const artifacts = job.result?.artifacts ?? [];
  if (!artifacts.length) return null;
  return (
    <section className="result-section"><h3>结果文件</h3><div className="artifact-list">
      {artifacts.map((path) => <a href={artifactHref(job.job_id, path)} key={path} target="_blank" rel="noreferrer"><span>↓</span><div><strong>{path.split("/").pop()}</strong><small>点击查看或下载</small></div></a>)}
    </div></section>
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
        <div className="processing-card"><span className="spinner" /><div><h3>{phase === "ANALYSIS_REQUESTED" ? "正在生成广告建议方案" : STAGES[stageIndex]?.[1] ?? "正在处理"}</h3><p>任务在本机后台运行。你可以留在此页等待，状态会自动刷新。</p></div></div>
      ) : aggregationReady && result ? (
        <>
          <div className="aggregation-ready">
            <div className="aggregation-check">✓</div>
            <div className="aggregation-copy">
              <span>PYTHON AGGREGATION COMPLETE</span>
              <h3>数据报表已经聚合完成</h3>
              <p>{result.executive_summary}</p>
            </div>
          </div>
          <div className="aggregation-metrics">
            <div><span>分析对象</span><strong>{job.preprocessing?.analysis_asins?.length ?? 0} 个 ASIN</strong></div>
            <div><span>数据周期</span><strong>{job.preprocessing?.auto_period?.start && job.preprocessing?.auto_period?.end ? `${job.preprocessing.auto_period.start} 至 ${job.preprocessing.auto_period.end}` : "由报表自动识别"}</strong></div>
            <div><span>聚合模式</span><strong>{job.preprocessing?.mode ?? "LOCAL_PYTHON"}</strong></div>
          </div>
          <ArtifactList job={job} />
          <div className="next-stage-panel">
            <div><span>下一步</span><h3>让 Codex 按 V2.0 规则生成建议</h3><p>点击后才会读取聚合结果进行智能分析；不会重新聚合，也不会自动修改亚马逊广告。</p></div>
            <button className="primary-button next-stage-button" type="button" onClick={onGenerateRecommendations} disabled={generating}>
              {generating ? "正在启动分析…" : "生成广告建议方案"}
            </button>
          </div>
        </>
      ) : result ? (
        <>
          <div className={`result-summary ${failed ? "warning" : ""}`}>
            <div><span className="result-status">{result.status}</span><h3>{result.executive_summary}</h3></div>
            <div className="human-chip">需要人工确认</div>
          </div>
          {result.recommendations?.length > 0 && (
            <section className="result-section"><h3>建议动作</h3><div className="recommendation-list">
              {result.recommendations.map((recommendation, index) => (
                <article key={`${recommendation.action}-${index}`}><span>{recommendation.priority}</span><div><h4>{recommendation.action}</h4><p>{recommendation.reason}</p>{recommendation.evidence?.length > 0 && <small>证据：{recommendation.evidence}</small>}</div></article>
              ))}
            </div></section>
          )}
          {result.missing_inputs?.length > 0 && <section className="result-section warning-list"><h3>还需要补充</h3><ul>{result.missing_inputs.map((item) => <li key={item}>{item}</li>)}</ul></section>}
          <ArtifactList job={job} />
          <section className="validator-box">
            <div><span className={`validator-icon ${job.validation?.outcome === "PASS_CANDIDATE_ONLY" ? "pass" : ""}`}>{job.validation?.outcome === "PASS_CANDIDATE_ONLY" ? "✓" : "!"}</span><div><h3>Validator：{job.validation?.outcome ?? result.safety.validator_status}</h3><p>{job.validation?.findings?.map((item) => item.message).join("；") || "未发现额外问题"}</p></div></div>
            <ul><li>亚马逊执行：{result.safety.execution_allowed ? "允许" : "禁止"}</li><li>自动应用：{result.safety.auto_apply ? "允许" : "禁止"}</li></ul>
          </section>
        </>
      ) : (
        <div className="processing-card error-card"><span>!</span><div><h3>任务未完成</h3><p>{job.error || "没有生成可用结果，请查看任务日志。"}</p></div></div>
      )}
      {FINAL_STATES.has(job.status) && !aggregationReady && <div className="form-actions"><button className="primary-button" type="button" onClick={onNew}>新建同类任务</button></div>}
      {aggregationReady && <div className="form-actions compact-action"><button className="secondary-button" type="button" onClick={onNew}>重新上传报表</button></div>}
    </div>
  );
}

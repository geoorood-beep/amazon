"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

const API = "http://127.0.0.1:8766";

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
  result?: Result;
  validation?: { outcome: string; findings: Array<{ level: string; code: string; message: string }> };
};

type Result = {
  status: string;
  executive_summary: string;
  recommendations: Array<{
    priority: string;
    action: string;
    reason: string;
    evidence: string;
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

type FieldDefinition = {
  name: string;
  label: string;
  placeholder?: string;
  type?: string;
  required?: boolean;
  wide?: boolean;
  help?: string;
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
    subtitle: "从产品信息生成测试方案",
    description: "产品资料 → 选词与结构 → Validator → 候选建议",
    accent: "orange",
  },
  {
    id: "OLD_PRODUCT_OPTIMIZATION",
    number: "02",
    title: "老品优化",
    subtitle: "用历史报表诊断广告",
    description: "本地聚合 → 异常诊断 → 调整建议 → 人工确认",
    accent: "teal",
  },
  {
    id: "AGGREGATE_REPORTS",
    number: "03",
    title: "更新广告数据",
    subtitle: "多张报表合并为决策包",
    description: "自动识别报表、去重并计算指标，减少重复读取",
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

const COMMON_FIELDS: FieldDefinition[] = [
  { name: "asin", label: "ASIN", placeholder: "例如 B0XXXXXXXX", required: true },
  { name: "marketplace", label: "站点", placeholder: "US", required: true },
  {
    name: "business_goal",
    label: "这次希望解决什么",
    placeholder: "例如：降低 ACOS，同时维持日均订单",
    required: true,
    wide: true,
  },
];

const FIELDS: Record<Intent, FieldDefinition[]> = {
  NEW_PRODUCT_PROMOTION: [
    { name: "asin", label: "ASIN", placeholder: "例如 B0XXXXXXXX", required: true },
    { name: "sku", label: "SKU", placeholder: "内部 SKU，可不填" },
    { name: "marketplace", label: "站点", placeholder: "US", required: true },
    { name: "size_spec", label: "尺寸", placeholder: "例如 5x7", required: true },
    { name: "rug_type", label: "地毯类型", placeholder: "例如 area rug" },
    { name: "order_target_daily", label: "日订单目标", placeholder: "例如 3", type: "number", required: true },
    { name: "target_cpa", label: "目标 CPA", placeholder: "例如 12.5", type: "number" },
    { name: "daily_budget", label: "期望日预算", placeholder: "例如 50", type: "number" },
    { name: "style", label: "风格", placeholder: "例如 boho" },
    { name: "color", label: "颜色", placeholder: "例如 beige" },
    { name: "material", label: "材质", placeholder: "例如 polyester" },
    { name: "scene_tags", label: "场景标签", placeholder: "living room, bedroom", wide: true },
    { ...COMMON_FIELDS[2] },
  ],
  OLD_PRODUCT_OPTIMIZATION: [
    ...COMMON_FIELDS,
    {
      name: "report_source_path",
      label: "广告报表文件夹",
      placeholder: "/Users/leo/Downloads/产品广告数据文件",
      required: true,
      wide: true,
      help: "第一版直接读取本机路径，不上传文件。支持 Downloads、Documents、Desktop。",
    },
    {
      name: "old_product_workbook",
      label: "老品数据工作簿",
      placeholder: "/Users/leo/Downloads/老品优化.xlsx",
      wide: true,
      help: "有老品工作簿时优先使用重叠安全聚合模式。",
    },
    { name: "period_start", label: "数据开始日", type: "date" },
    { name: "period_end", label: "数据结束日", type: "date" },
  ],
  AGGREGATE_REPORTS: [
    { name: "asin", label: "主 ASIN", placeholder: "例如 B0XXXXXXXX", required: true },
    { name: "marketplace", label: "站点", placeholder: "US", required: true },
    {
      name: "report_source_path",
      label: "广告报表文件夹",
      placeholder: "/Users/leo/Downloads/产品广告数据文件",
      required: true,
      wide: true,
    },
    {
      name: "old_product_workbook",
      label: "老品数据工作簿（可选）",
      placeholder: "/Users/leo/Downloads/老品优化.xlsx",
      wide: true,
    },
    { name: "period_start", label: "数据开始日", type: "date" },
    { name: "period_end", label: "数据结束日", type: "date" },
    {
      name: "business_goal",
      label: "聚合用途",
      placeholder: "例如：给本周老品优化使用",
      required: true,
      wide: true,
    },
  ],
  WEEKLY_REVIEW: [],
};

const STAGES = [
  ["QUEUED", "已接收"],
  ["PREPROCESSING", "本地聚合"],
  ["ANALYZING", "智能分析"],
  ["VALIDATING", "安全校验"],
  ["COMPLETED", "生成建议"],
] as const;

const FINAL_STATES = new Set(["COMPLETED", "BLOCKED", "FAILED"]);

function intentTitle(intent: Intent) {
  return INTENTS.find((item) => item.id === intent)?.title ?? intent;
}

function artifactHref(jobId: string, path: string) {
  const marker = "/artifacts/";
  const relative = path.includes(marker) ? path.split(marker)[1] : path.split("/").pop() ?? path;
  return `${API}/api/jobs/${jobId}/artifacts/${relative
    .split("/")
    .map(encodeURIComponent)
    .join("/")}`;
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

export default function Home() {
  const [activeIntent, setActiveIntent] = useState<Intent | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({ marketplace: "US" });
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");

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
    fetch(`${API}/api/health`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error();
        return response.json();
      })
      .then(() => setBackendOnline(true))
      .catch(() => setBackendOnline(false));
    fetch(`${API}/api/jobs`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("后台未响应");
        return response.json();
      })
      .then((payload) => setJobs(payload.jobs ?? []))
      .catch(() => setBackendOnline(false));
  }, []);

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

  function chooseIntent(intent: Intent) {
    setActiveIntent(intent);
    setFields({ marketplace: "US" });
    setActiveJob(null);
    setMessage("");
    window.setTimeout(() => document.getElementById("work-panel")?.scrollIntoView({ block: "start" }), 20);
  }

  async function submitJob(event: FormEvent) {
    event.preventDefault();
    if (!activeIntent) return;
    setSubmitting(true);
    setMessage("");
    try {
      const response = await fetch(`${API}/api/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ intent: activeIntent, fields }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "任务提交失败");
      const job = await loadJob(payload.job_id);
      setActiveJob(job);
      loadJobs();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "任务提交失败");
      setBackendOnline(false);
    } finally {
      setSubmitting(false);
    }
  }

  const stageIndex = activeJob
    ? FINAL_STATES.has(activeJob.status)
      ? STAGES.length - 1
      : Math.max(0, STAGES.findIndex(([status]) => status === activeJob.stage || status === activeJob.status))
    : 0;

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="返回顶部">
          <span className="brand-mark">LY</span>
          <span>
            <strong>陆遥广告运营台</strong>
            <small>RUG AD OPERATIONS · V2.0</small>
          </span>
        </a>
        <div className="system-state">
          <span className={`online-dot ${backendOnline === false ? "offline" : ""}`} />
          {backendOnline === null ? "正在连接" : backendOnline ? "本机已连接" : "后台未启动"}
          <span className="divider" />
          只生成建议 · 人工执行
        </div>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow">把复杂架构变成四个操作</p>
          <h1>今天要处理哪类广告任务？</h1>
          <p className="hero-subtitle">
            你负责选择任务和提供数据；本地 Python 先聚合，Codex 再按 V2.0 规则分析，Validator 最后拦截不安全输出。
          </p>
          <div className="guardrails">
            <span>Rug 专用</span>
            <span>本地数据</span>
            <span>不连接亚马逊执行</span>
          </div>
        </div>
        <div className="flow-card" aria-label="工作流程">
          <p>当前联动</p>
          <div><strong>网页</strong><span>收集任务</span></div>
          <i>↓</i>
          <div><strong>Python</strong><span>聚合报表</span></div>
          <i>↓</i>
          <div><strong>Codex + AGENTS</strong><span>规则分析</span></div>
          <i>↓</i>
          <div><strong>Validator</strong><span>安全放行</span></div>
        </div>
      </section>

      <section className="intent-section" aria-labelledby="intent-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">快速入口</p>
            <h2 id="intent-heading">选择一个动作开始</h2>
          </div>
          <p>每个入口自动找到对应的规则、阈值和数据处理程序。</p>
        </div>
        <div className="intent-grid">
          {INTENTS.map((intent) => (
            <button
              className={`intent-card ${intent.accent} ${activeIntent === intent.id ? "selected" : ""}`}
              key={intent.id}
              onClick={() => chooseIntent(intent.id)}
              type="button"
            >
              <span className="intent-number">{intent.number}</span>
              <span className="intent-arrow">↗</span>
              <strong>{intent.title}</strong>
              <em>{intent.subtitle}</em>
              <small>{intent.description}</small>
            </button>
          ))}
        </div>
      </section>

      {activeIntent && currentIntent && (
        <section className="work-shell" id="work-panel">
          <div className="work-main">
            <div className="work-title">
              <span>{currentIntent.number}</span>
              <div>
                <p className="eyebrow">当前任务</p>
                <h2>{currentIntent.title}</h2>
              </div>
            </div>

            {!activeJob ? (
              <form onSubmit={submitJob} className="job-form">
                {FIELDS[activeIntent].length > 0 ? (
                  <div className="field-grid">
                    {FIELDS[activeIntent].map((field) => (
                      <label className={field.wide ? "wide" : ""} key={field.name}>
                        <span>{field.label}{field.required && <b> *</b>}</span>
                        <input
                          name={field.name}
                          type={field.type ?? "text"}
                          value={fields[field.name] ?? ""}
                          placeholder={field.placeholder}
                          required={field.required}
                          step={field.type === "number" ? "any" : undefined}
                          onChange={(event) =>
                            setFields((current) => ({ ...current, [field.name]: event.target.value }))
                          }
                        />
                        {field.help && <small>{field.help}</small>}
                      </label>
                    ))}
                  </div>
                ) : (
                  <div className="weekly-ready">
                    <span>W</span>
                    <div>
                      <strong>读取本周阈值检查结果</strong>
                      <p>系统会检查现有历史数据是否达到候选阈值生成门槛；不会直接修改当前阈值。</p>
                    </div>
                  </div>
                )}
                {message && <p className="form-error">{message}</p>}
                <div className="form-actions">
                  <button className="secondary-button" type="button" onClick={() => setActiveIntent(null)}>
                    取消
                  </button>
                  <button className="primary-button" type="submit" disabled={submitting || backendOnline === false}>
                    {submitting ? "正在创建任务…" : activeIntent === "WEEKLY_REVIEW" ? "检查本周建议" : "开始处理"}
                  </button>
                </div>
              </form>
            ) : (
              <JobResult
                job={activeJob}
                stageIndex={stageIndex}
                onNew={() => {
                  setActiveJob(null);
                  setMessage("");
                }}
              />
            )}
          </div>

          <aside className="recent-panel">
            <div className="recent-heading">
              <h3>最近任务</h3>
              <button onClick={loadJobs} type="button">刷新</button>
            </div>
            {jobs.length === 0 ? (
              <p className="empty-copy">还没有任务记录。</p>
            ) : (
              jobs.slice(0, 8).map((job) => (
                <button className="recent-job" key={job.job_id} onClick={() => loadJob(job.job_id)} type="button">
                  <span className={`job-state ${job.status.toLowerCase()}`}>{job.status}</span>
                  <strong>{intentTitle(job.intent)}</strong>
                  <small>{formatTime(job.created_at)}</small>
                </button>
              ))
            )}
            <div className="safety-note">
              <strong>安全边界</strong>
              <p>AUTO_PASS 只代表校验通过，不代表已在亚马逊后台执行。</p>
            </div>
          </aside>
        </section>
      )}

      <footer>
        <span>陆遥广告智能体 V2.0</span>
        <span>数据保存在本机 · HUMAN_EXECUTION_ONLY</span>
      </footer>
    </main>
  );
}

function JobResult({ job, stageIndex, onNew }: { job: Job; stageIndex: number; onNew: () => void }) {
  const result = job.result;
  const failed = job.status === "FAILED" || job.status === "BLOCKED" || result?.status !== "READY_FOR_HUMAN_REVIEW";
  return (
    <div className="job-result">
      <div className="progress-row">
        {STAGES.map(([status, label], index) => (
          <div className={`progress-step ${index <= stageIndex ? "done" : ""}`} key={status}>
            <span>{index < stageIndex ? "✓" : index + 1}</span>
            <small>{label}</small>
          </div>
        ))}
      </div>

      {!FINAL_STATES.has(job.status) ? (
        <div className="processing-card">
          <span className="spinner" />
          <div>
            <h3>{STAGES[stageIndex]?.[1] ?? "正在处理"}</h3>
            <p>任务在本机后台运行。你可以留在此页等待，状态会自动刷新。</p>
          </div>
        </div>
      ) : result ? (
        <>
          <div className={`result-summary ${failed ? "warning" : ""}`}>
            <div>
              <span className="result-status">{result.status}</span>
              <h3>{result.executive_summary}</h3>
            </div>
            <div className="human-chip">需要人工确认</div>
          </div>

          {result.recommendations?.length > 0 && (
            <section className="result-section">
              <h3>建议动作</h3>
              <div className="recommendation-list">
                {result.recommendations.map((recommendation, index) => (
                  <article key={`${recommendation.action}-${index}`}>
                    <span>{recommendation.priority}</span>
                    <div>
                      <h4>{recommendation.action}</h4>
                      <p>{recommendation.reason}</p>
                      {recommendation.evidence?.length > 0 && (
                        <small>证据：{recommendation.evidence}</small>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            </section>
          )}

          {result.missing_inputs?.length > 0 && (
            <section className="result-section warning-list">
              <h3>还需要补充</h3>
              <ul>{result.missing_inputs.map((item) => <li key={item}>{item}</li>)}</ul>
            </section>
          )}

          {result.artifacts?.length > 0 && (
            <section className="result-section">
              <h3>结果文件</h3>
              <div className="artifact-list">
                {result.artifacts.map((path) => (
                  <a href={artifactHref(job.job_id, path)} key={path} target="_blank" rel="noreferrer">
                    <span>↓</span>
                    <div><strong>{path.split("/").pop()}</strong><small>点击查看或下载</small></div>
                  </a>
                ))}
              </div>
            </section>
          )}

          <section className="validator-box">
            <div>
              <span className={`validator-icon ${job.validation?.outcome === "PASS_CANDIDATE_ONLY" ? "pass" : ""}`}>
                {job.validation?.outcome === "PASS_CANDIDATE_ONLY" ? "✓" : "!"}
              </span>
              <div>
                <h3>Validator：{job.validation?.outcome ?? result.safety.validator_status}</h3>
                <p>{job.validation?.findings?.map((item) => item.message).join("；") || "未发现额外问题"}</p>
              </div>
            </div>
            <ul>
              <li>亚马逊执行：{result.safety.execution_allowed ? "允许" : "禁止"}</li>
              <li>自动应用：{result.safety.auto_apply ? "允许" : "禁止"}</li>
            </ul>
          </section>
        </>
      ) : (
        <div className="processing-card error-card">
          <span>!</span><div><h3>任务未完成</h3><p>{job.error || "没有生成可用结果，请查看任务日志。"}</p></div>
        </div>
      )}

      {FINAL_STATES.has(job.status) && (
        <div className="form-actions"><button className="primary-button" type="button" onClick={onNew}>新建同类任务</button></div>
      )}
    </div>
  );
}

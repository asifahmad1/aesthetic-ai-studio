/* ============================================================
   Aesthetic AI Studio — frontend SPA (vanilla JS, no frameworks)
   Sections:
     1. Utilities & state
     2. API layer
     3. Router / shell
     4. Dashboard view
     5. Outline view
     6. Editor view (toolbar, thumbnails, canvas, inspector)
     7. Settings view
     8. Shared components (export modal, dropdowns)
     9. Init
   ============================================================ */

/* ---------- 1. Utilities & state ---------- */

const $ = (sel, root) => (root || document).querySelector(sel);
const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

function esc(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function debounce(fn, ms) {
  let t = null;
  return function (...args) {
    clearTimeout(t);
    t = setTimeout(() => fn.apply(this, args), ms);
  };
}

function uid(prefix) {
  return (prefix || "id") + "_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

function fmtDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (isNaN(d)) return String(iso);
  return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

const state = {
  view: "dashboard",
  projects: [],
  themes: [],
  layouts: [],
  settings: null,
  project: null,          // current full project object
  slideIdx: 0,
  slideHtmlCache: {},     // slideId -> rendered html fragment
  outline: [],            // working outline in outline view
  currentInspectorTab: "content",
  saveTimer: null,
};

const SLIDE_W = 1000, SLIDE_H = 562.5;

const PURPOSES = [
  "Academic lecture", "Scientific presentation", "Research conference",
  "Business meeting", "Training workshop", "Thesis defense",
  "Food Science and Nutrition", "Marketing presentation",
  "Investor pitch deck", "Custom"
];
const AUDIENCES = [
  "General audience", "University students", "Researchers & academics",
  "Industry professionals", "Policymakers & regulators",
  "Investors & stakeholders", "Mixed audience"
];
const KNOWLEDGE_LEVELS = ["Beginner", "Intermediate", "Advanced", "Mixed"];
const SLIDE_COUNTS = [5, 10, 15, 20, 30, 40, 50];
const PROVIDER_KINDS = [
  { kind: "offline", label: "Offline composer (no key needed)" },
  { kind: "openai", label: "OpenAI-compatible" },
  { kind: "gemini", label: "Google Gemini" },
  { kind: "ollama", label: "Ollama" },
];

/* ---------- 2. API layer ---------- */

async function api(path, opts) {
  opts = opts || {};
  const init = { method: opts.method || "GET", headers: { "Content-Type": "application/json" } };
  if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
  let res;
  try {
    res = await fetch(path, init);
  } catch (e) {
    throw new Error("Could not reach the server (" + e.message + "). Is the app running?");
  }
  let data = {};
  try { data = await res.json(); } catch (e) { /* non-JSON body */ }
  if (!res.ok) {
    const msg = (data && (data.error || data.message)) || ("Request failed with status " + res.status);
    throw new Error(msg);
  }
  return data;
}

const apiGet = (p) => api(p);
const apiPost = (p, body) => api(p, { method: "POST", body: body || {} });
const apiPut = (p, body) => api(p, { method: "PUT", body: body || {} });
const apiDelete = (p) => api(p, { method: "DELETE" });

/* ---------- global UI helpers ---------- */

function showError(msg) {
  const banner = $("#error-banner");
  $("#error-text").textContent = msg;
  banner.classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}
function clearError() { $("#error-banner").classList.add("hidden"); }

function setLoading(on, text) {
  const el = $("#app-loading");
  if (text) $("#app-loading-text").textContent = text;
  el.classList.toggle("hidden", !on);
}

function withButtonSpinner(btn, fn) {
  return async function (...args) {
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner sm"></span> ' + esc(btn.dataset.busyLabel || "Working…");
    try {
      await fn.apply(this, args);
    } catch (e) {
      showError(e.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  };
}

/* ---------- 3. Router / shell ---------- */

const NAV_VIEWS = ["dashboard", "settings"];

function navigate(view, param) {
  state.view = view;
  clearError();
  $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.nav === view || (view === "outline" || view === "editor") && b.dataset.nav === "dashboard"));
  const renderers = {
    dashboard: renderDashboard,
    outline: () => renderOutline(param),
    editor: () => renderEditor(param),
    settings: renderSettings,
  };
  const fn = renderers[view];
  if (fn) fn();
  else renderDashboard();
}

function scrollTop() { window.scrollTo({ top: 0 }); }

async function openProject(id) {
  setLoading(true, "Opening project…");
  try {
    const project = await apiGet("/api/projects/" + encodeURIComponent(id));
    state.project = project;
    state.slideIdx = 0;
    state.slideHtmlCache = {};
    const st = project.status;
    if (st === "ready" || (project.slides && project.slides.length)) {
      navigate("editor", project.id);
    } else {
      navigate("outline", project.id);
    }
  } catch (e) {
    showError("Could not open project: " + e.message);
  } finally {
    setLoading(false);
  }
  scrollTop();
}

/* ---------- shared: render a slide fragment scaled ---------- */

function slideFrameHTML(html, targetWidth) {
  const scale = targetWidth / SLIDE_W;
  const h = Math.round(SLIDE_H * scale);
  return (
    '<div class="slide-frame" style="width:' + targetWidth + "px;height:" + h + 'px">' +
    '<div class="slide-inner" style="transform:scale(' + scale + ')">' + html + "</div>" +
    "</div>"
  );
}

async function getSlideHtml(projectId, slide) {
  if (state.slideHtmlCache[slide.id]) return state.slideHtmlCache[slide.id];
  const data = await apiGet("/api/projects/" + encodeURIComponent(projectId) + "/slides/" + encodeURIComponent(slide.id) + "/html");
  const html = (data && data.html) || "";
  state.slideHtmlCache[slide.id] = html;
  return html;
}

function invalidateSlideHtml(slideId) { delete state.slideHtmlCache[slideId]; }
function invalidateAllSlideHtml() { state.slideHtmlCache = {}; }

/* ============================================================
   4. Dashboard view
   ============================================================ */

async function renderDashboard() {
  const root = $("#view-root");
  root.innerHTML =
    '<div class="view">' +
      '<div class="hero">' +
        "<h1>Aesthetic AI Studio</h1>" +
        "<p>From Ideas to Extraordinary Presentations — describe your topic, pick a style, and let AI compose a polished slide deck for you.</p>" +
        '<div class="sample-row">' +
          '<button class="btn btn-lg" id="btn-sample">Generate sample deck (30 slides)</button>' +
        "</div>" +
      "</div>" +
      '<div class="dashboard-grid">' +
        '<div class="card" id="new-form-card">' +
          '<h2 class="section-title" style="font-size:19px">New presentation</h2>' +
          '<p class="section-sub">Fill in the brief, then generate an outline you can edit before building slides.</p>' +
          '<form id="new-project-form">' +
            '<div class="field"><label>Title</label>' +
              '<input type="text" id="np-title" placeholder="e.g. Food Safety in Hospital Canteens" required maxlength="160"></div>' +
            '<div class="field"><label>Instructions / topic brief</label>' +
              '<textarea id="np-instructions" placeholder="What should the presentation cover? Key points, tone, must-include facts…"></textarea></div>' +
            '<div class="form-grid">' +
              '<div class="field"><label>Purpose</label><select id="np-purpose">' +
                PURPOSES.map((p) => '<option value="' + esc(p) + '">' + esc(p) + "</option>").join("") +
              "</select></div>" +
              '<div class="field"><label>Audience</label><select id="np-audience">' +
                AUDIENCES.map((p) => '<option value="' + esc(p) + '">' + esc(p) + "</option>").join("") +
              "</select></div>" +
              '<div class="field"><label>Audience knowledge level</label><select id="np-knowledge">' +
                KNOWLEDGE_LEVELS.map((p) => '<option value="' + esc(p) + '">' + esc(p) + "</option>").join("") +
              "</select></div>" +
              '<div class="field"><label>Slide count</label>' +
                '<select id="np-count">' +
                  SLIDE_COUNTS.map((n) => '<option value="' + n + '"' + (n === 15 ? " selected" : "") + ">" + n + " slides</option>").join("") +
                  '<option value="custom">Custom…</option>' +
                "</select></div>" +
            "</div>" +
            '<div class="field hidden" id="np-custom-count-wrap"><label>Custom slide count</label>' +
              '<input type="number" id="np-custom-count" min="1" max="120" value="12"></div>' +
            '<div class="field"><label>Theme</label><div class="theme-picker" id="np-themes"></div>' +
              '<div class="hint">Pick a visual style for the deck.</div></div>' +
            '<div class="form-grid">' +
              '<div class="field"><label>AI provider</label><select id="np-provider">' +
                PROVIDER_KINDS.map((p) => '<option value="' + p.kind + '">' + esc(p.label) + "</option>").join("") +
              "</select></div>" +
              '<div class="field"><label>Model name</label>' +
                '<input type="text" id="np-model" placeholder="e.g. gpt-4o-mini, gemini-3.8-flash, llama3.1"><div class="hint">Optional — leave blank for the provider default.</div></div>' +
            "</div>" +
            '<button type="submit" class="btn btn-lg" id="np-submit" style="width:100%;justify-content:center">Create &amp; generate outline</button>' +
          "</form>" +
        "</div>" +
        '<div>' +
          '<h2 class="section-title" style="font-size:19px">Your presentations</h2>' +
          '<p class="section-sub" id="projects-sub"></p>' +
          '<div class="project-list" id="project-list"></div>' +
        "</div>" +
      "</div>" +
    "</div>";

  renderThemePicker();
  bindDashboard();
  await refreshProjectList();
}

function renderThemePicker() {
  const wrap = $("#np-themes");
  if (!state.themes.length) {
    wrap.innerHTML = '<div class="hint">Themes are still loading — you can pick one after creation in the editor.</div>';
    return;
  }
  wrap.innerHTML = state.themes
    .map((t, i) => {
      const sw = (t.swatches || []).slice(0, 3).map((c) => '<span style="background:' + esc(c) + '"></span>').join("");
      return (
        '<div class="theme-card' + (i === 0 ? " selected" : "") + '" data-theme="' + esc(t.id) + '" role="button" tabindex="0">' +
        '<div class="tname">' + esc(t.name) + "</div>" +
        '<div class="swatches">' + sw + "</div>" +
        "</div>"
      );
    })
    .join("");
  $$(".theme-card", wrap).forEach((el) => {
    const pick = () => {
      $$(".theme-card", wrap).forEach((x) => x.classList.remove("selected"));
      el.classList.add("selected");
    };
    el.addEventListener("click", pick);
    el.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
  });
}

function selectedThemeId() {
  const el = $(".theme-card.selected");
  return el ? el.dataset.theme : (state.themes[0] && state.themes[0].id) || "";
}

function bindDashboard() {
  $("#np-count").addEventListener("change", (e) => {
    $("#np-custom-count-wrap").classList.toggle("hidden", e.target.value !== "custom");
  });

  $("#new-project-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const countSel = $("#np-count").value;
    const slideCount = countSel === "custom"
      ? Math.max(1, Math.min(120, parseInt($("#np-custom-count").value, 10) || 12))
      : parseInt(countSel, 10);
    const btn = $("#np-submit");
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner sm"></span> Creating…';
    try {
      const project = await apiPost("/api/projects", {
        title: $("#np-title").value.trim(),
        instructions: $("#np-instructions").value.trim(),
        purpose: $("#np-purpose").value,
        audience: $("#np-audience").value,
        knowledge_level: $("#np-knowledge").value,
        slide_count: slideCount,
        theme: selectedThemeId(),
        provider: { kind: $("#np-provider").value, model: $("#np-model").value.trim() },
      });
      state.project = project;
      state.slideIdx = 0;
      state.slideHtmlCache = {};
      navigate("outline", project.id);
      scrollTop();
    } catch (err) {
      showError("Could not create project: " + err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  });

  const sampleBtn = $("#btn-sample");
  sampleBtn.dataset.busyLabel = "Building 30 slides…";
  sampleBtn.addEventListener("click", withButtonSpinner(sampleBtn, async () => {
    const data = await apiPost("/api/sample");
    if (!data || !data.id) throw new Error("Server did not return a project id.");
    await openProject(data.id);
  }));
}

async function refreshProjectList() {
  const list = $("#project-list");
  list.innerHTML = '<div class="empty-state"><div class="spinner" style="margin:0 auto 10px"></div>Loading projects…</div>';
  try {
    state.projects = await apiGet("/api/projects");
  } catch (e) {
    list.innerHTML = '<div class="empty-state">Could not load projects: ' + esc(e.message) + "</div>";
    return;
  }
  const sub = $("#projects-sub");
  if (sub) sub.textContent = state.projects.length ? state.projects.length + " project(s)" : "No projects yet — create your first one.";
  if (!state.projects.length) {
    list.innerHTML = '<div class="empty-state">Nothing here yet.<br>Create a presentation on the left, or generate the 30-slide sample deck above.</div>';
    return;
  }
  list.innerHTML = state.projects
    .map((p) => {
      const n = (p.slides && p.slides.length) || p.slide_count || 0;
      return (
        '<div class="project-card" data-id="' + esc(p.id) + '">' +
          '<div class="pinfo">' +
            '<p class="ptitle">' + esc(p.title || "Untitled") + "</p>" +
            '<div class="pmeta">' +
              '<span class="status-badge status-' + esc(p.status || "draft") + '">' + esc(p.status || "draft") + "</span>" +
              "<span>" + n + " slide" + (n === 1 ? "" : "s") + "</span>" +
              "<span>Updated " + esc(fmtDate(p.updated)) + "</span>" +
            "</div>" +
          "</div>" +
          '<div class="project-actions">' +
            '<button class="btn btn-sm" data-act="open">Open</button>' +
            '<div class="dropdown">' +
              '<button class="btn btn-sm btn-ghost" data-act="export-menu">Export ▾</button>' +
              '<div class="dropdown-menu hidden" data-menu>' +
                '<button data-export="pptx">Download PPTX</button>' +
                '<button data-export="pdf">Download PDF</button>' +
                '<button data-export="html">Download HTML</button>' +
              "</div>" +
            "</div>" +
            '<button class="btn btn-sm btn-danger" data-act="delete">Delete</button>' +
          "</div>" +
        "</div>"
      );
    })
    .join("");

  // close dropdowns on outside click (single global handler is bound in bindShell)

  $$(".project-card", list).forEach((card) => {
    const id = card.dataset.id;
    $("[data-act=open]", card).addEventListener("click", () => openProject(id));
    $("[data-act=export-menu]", card).addEventListener("click", (e) => {
      e.stopPropagation();
      const menu = $("[data-menu]", card);
      const wasHidden = menu.classList.contains("hidden");
      $$(".dropdown-menu").forEach((m) => m.classList.add("hidden"));
      if (wasHidden) menu.classList.remove("hidden");
    });
    $$("[data-export]", card).forEach((b) =>
      b.addEventListener("click", () => {
        $$(".dropdown-menu").forEach((m) => m.classList.add("hidden"));
        runExport(id, b.dataset.export);
      })
    );
    $("[data-act=delete]", card).addEventListener("click", async () => {
      const p = state.projects.find((x) => String(x.id) === String(id));
      if (!confirm('Delete "' + (p && p.title ? p.title : "this project") + '"? This cannot be undone.')) return;
      try {
        await apiDelete("/api/projects/" + encodeURIComponent(id));
        await refreshProjectList();
      } catch (e) {
        showError("Could not delete project: " + e.message);
      }
    });
  });
}

/* ============================================================
   5. Outline view
   ============================================================ */

async function renderOutline(projectId) {
  const root = $("#view-root");
  // ensure we have the project
  if (!state.project || String(state.project.id) !== String(projectId)) {
    try {
      state.project = await apiGet("/api/projects/" + encodeURIComponent(projectId));
    } catch (e) {
      root.innerHTML = '<div class="view"><div class="empty-state">Could not load project: ' + esc(e.message) + '</div></div>';
      return;
    }
  }
  const p = state.project;
  state.outline = Array.isArray(p.outline) ? JSON.parse(JSON.stringify(p.outline)) : [];

  root.innerHTML =
    '<div class="view">' +
      '<button class="back-link" id="outline-back">← Back to dashboard</button>' +
      '<div class="view-head">' +
        "<div><h2 class='section-title'>" + esc(p.title || "Untitled") + "</h2>" +
        '<p class="section-sub" style="margin:0">Step 1 of 2 — review and edit the outline. When it looks right, approve it to build slides.</p></div>' +
        '<div class="grow"></div>' +
        '<span class="status-badge status-' + esc(p.status || "draft") + '">' + esc(p.status || "draft") + "</span>" +
      "</div>" +
      (p.slides && p.slides.length
        ? '<div class="note-inline">This project already has ' + p.slides.length + " slide(s). Approving a new outline will replace them.</div>"
        : "") +
      '<div class="outline-toolbar">' +
        '<button class="btn btn-ghost" id="btn-gen-outline">⟳ Regenerate outline</button>' +
        '<button class="btn btn-ghost" id="btn-add-item">+ Add item</button>' +
        '<div class="grow" style="flex:1"></div>' +
        '<button class="btn btn-lg" id="btn-approve">Approve &amp; build slides →</button>' +
      "</div>" +
      '<div id="outline-list"></div>' +
    "</div>";

  $("#outline-back").addEventListener("click", () => navigate("dashboard"));
  $("#btn-gen-outline").addEventListener("click", withButtonSpinner($("#btn-gen-outline"), generateOutline));
  $("#btn-add-item").addEventListener("click", () => {
    state.outline.push({ title: "New section", bullets: [""], layout_hint: state.layouts[0] ? state.layouts[0].id : "", notes: "" });
    renderOutlineItems();
    persistOutlineDraft();
  });
  $("#btn-approve").addEventListener("click", withButtonSpinner($("#btn-approve"), approveOutline));

  renderOutlineItems();
  if (!state.outline.length) {
    // first visit: generate automatically so the user sees something useful
    generateOutline();
  }
}

function renderOutlineItems() {
  const wrap = $("#outline-list");
  if (!wrap) return;
  if (!state.outline.length) {
    wrap.innerHTML = '<div class="empty-state">No outline yet — click "Regenerate outline" to create one, or add items manually.</div>';
    return;
  }
  wrap.innerHTML = state.outline
    .map((item, i) => {
      const bulletsText = Array.isArray(item.bullets) ? item.bullets.join("\n") : String(item.bullets || "");
      const layoutOpts = state.layouts
        .map((l) => '<option value="' + esc(l.id) + '"' + (l.id === item.layout_hint ? " selected" : "") + ">" + esc(l.name) + "</option>")
        .join("");
      return (
        '<div class="outline-item" data-idx="' + i + '">' +
          '<div class="ohead">' +
            '<div class="onum">' + (i + 1) + "</div>" +
            '<input type="text" data-f="title" value="' + esc(item.title || "") + '" placeholder="Slide title" maxlength="160">' +
            '<div class="obtns">' +
              '<button class="icon-btn" data-op="up" title="Move up" ' + (i === 0 ? "disabled" : "") + ">↑</button>" +
              '<button class="icon-btn" data-op="down" title="Move down" ' + (i === state.outline.length - 1 ? "disabled" : "") + ">↓</button>" +
              '<button class="icon-btn danger" data-op="del" title="Delete item">✕</button>' +
            "</div>" +
          "</div>" +
          '<div class="outline-grid">' +
            '<div class="field" style="margin-bottom:10px"><label>Bullet points (one per line)</label>' +
              '<textarea data-f="bullets" rows="4">' + esc(bulletsText) + "</textarea></div>" +
            '<div>' +
              '<div class="field" style="margin-bottom:10px"><label>Suggested layout</label>' +
                '<select data-f="layout_hint">' + layoutOpts + "</select></div>" +
              '<div class="field" style="margin-bottom:0"><label>Speaker notes</label>' +
                '<input type="text" data-f="notes" value="' + esc(item.notes || "") + '" placeholder="Optional notes for this slide"></div>' +
            "</div>" +
          "</div>" +
        "</div>"
      );
    })
    .join("");

  $$(".outline-item", wrap).forEach((el) => {
    const idx = parseInt(el.dataset.idx, 10);
    $("[data-f=title]", el).addEventListener("input", (e) => { state.outline[idx].title = e.target.value; persistOutlineDraft(); });
    $("[data-f=bullets]", el).addEventListener("input", (e) => { state.outline[idx].bullets = e.target.value.split("\n"); persistOutlineDraft(); });
    $("[data-f=layout_hint]", el).addEventListener("change", (e) => { state.outline[idx].layout_hint = e.target.value; persistOutlineDraft(); });
    $("[data-f=notes]", el).addEventListener("input", (e) => { state.outline[idx].notes = e.target.value; persistOutlineDraft(); });
    $$("[data-op]", el).forEach((b) =>
      b.addEventListener("click", () => {
        const op = b.dataset.op;
        if (op === "del") {
          if (!confirm("Delete outline item " + (idx + 1) + "?")) return;
          state.outline.splice(idx, 1);
        } else if (op === "up" && idx > 0) {
          const t = state.outline[idx - 1]; state.outline[idx - 1] = state.outline[idx]; state.outline[idx] = t;
        } else if (op === "down" && idx < state.outline.length - 1) {
          const t = state.outline[idx + 1]; state.outline[idx + 1] = state.outline[idx]; state.outline[idx] = t;
        }
        renderOutlineItems();
        persistOutlineDraft();
      })
    );
  });
}

const persistOutlineDraft = debounce(async () => {
  if (!state.project) return;
  try {
    await apiPut("/api/projects/" + encodeURIComponent(state.project.id), { outline: state.outline });
  } catch (e) {
    showError("Could not save outline draft: " + e.message);
  }
}, 900);

async function generateOutline() {
  if (!state.project) return;
  setLoading(true, "Generating outline…");
  try {
    const data = await apiPost("/api/projects/" + encodeURIComponent(state.project.id) + "/outline");
    state.outline = Array.isArray(data.outline) ? data.outline : [];
    await apiPut("/api/projects/" + encodeURIComponent(state.project.id), { outline: state.outline });
    state.project = await apiGet("/api/projects/" + encodeURIComponent(state.project.id));
    navigate("outline", state.project.id);
  } catch (e) {
    // 502 from AI provider or any other failure: show the REAL error
    showError("Outline generation failed: " + e.message);
  } finally {
    setLoading(false);
  }
}

async function approveOutline() {
  if (!state.project) return;
  if (!state.outline.length) {
    showError("The outline is empty — add at least one item before building slides.");
    return;
  }
  setLoading(true, "Building slides… this can take a while");
  try {
    const project = await apiPost("/api/projects/" + encodeURIComponent(state.project.id) + "/generate", { outline: state.outline });
    state.project = project;
    state.slideIdx = 0;
    state.slideHtmlCache = {};
    navigate("editor", project.id);
    scrollTop();
  } catch (e) {
    showError("Slide generation failed: " + e.message);
  } finally {
    setLoading(false);
  }
}

/* ============================================================
   6. Editor view — three-panel slide editor
   ============================================================ */

function currentSlide() {
  const s = state.project && state.project.slides;
  if (!s || !s.length) return null;
  return s[Math.min(state.slideIdx, s.length - 1)];
}

function setSaveStatus(mode, msg) {
  const el = $("#save-status");
  if (!el) return;
  el.classList.remove("saving", "saved", "failed");
  const dot = '<span class="dot"></span>';
  if (mode === "saving") { el.classList.add("saving"); el.innerHTML = dot + "<span>Saving…</span>"; }
  else if (mode === "saved") { el.classList.add("saved"); el.innerHTML = dot + "<span>All changes saved</span>"; }
  else if (mode === "failed") { el.classList.add("failed"); el.innerHTML = dot + "<span>Save failed" + (msg ? ": " + esc(msg) : "") + "</span>"; }
  else { el.innerHTML = dot + "<span>Saved</span>"; }
}

function scheduleSave(after) {
  setSaveStatus("saving");
  clearTimeout(state.saveTimer);
  state.saveTimer = setTimeout(async () => {
    try {
      const updated = await apiPut("/api/projects/" + encodeURIComponent(state.project.id), {
        title: state.project.title,
        theme: state.project.theme,
        slides: state.project.slides,
      });
      // Keep the local slides/title/theme objects authoritative so keystrokes
      // typed while the request was in flight are not lost; take everything
      // else (status, updated timestamp, server normalizations) from the response.
      const keep = {
        title: state.project.title,
        theme: state.project.theme,
        slides: state.project.slides,
      };
      state.project = Object.assign({}, updated, keep);
      setSaveStatus("saved");
      if (after) await after();
    } catch (e) {
      setSaveStatus("failed", e.message);
      showError("Autosave failed: " + e.message);
    }
  }, 800);
}

async function renderEditor(projectId) {
  const root = $("#view-root");
  if (!state.project || String(state.project.id) !== String(projectId)) {
    try {
      state.project = await apiGet("/api/projects/" + encodeURIComponent(projectId));
    } catch (e) {
      root.innerHTML = '<div class="view"><div class="empty-state">Could not load project: ' + esc(e.message) + "</div></div>";
      return;
    }
  }
  const p = state.project;
  if (!p.slides || !p.slides.length) {
    root.innerHTML = '<div class="view"><div class="empty-state">This project has no slides yet. <button class="btn btn-sm" id="go-outline">Go to outline</button></div></div>';
    $("#go-outline").addEventListener("click", () => navigate("outline", p.id));
    return;
  }
  state.slideIdx = Math.min(state.slideIdx, p.slides.length - 1);
  state.currentInspectorTab = "content";

  const layoutOpts = state.layouts
    .map((l) => '<option value="' + esc(l.id) + '">' + esc(l.name) + "</option>")
    .join("");

  root.innerHTML =
    '<div class="view" style="max-width:1500px">' +
      '<button class="back-link" id="ed-back">← Back to dashboard</button>' +
      '<div class="editor-toolbar">' +
        '<input type="text" class="ptitle-input" id="ed-title" value="' + esc(p.title || "Untitled") + '" maxlength="160" title="Project title (click to edit)">' +
        '<div class="toolbar-sep"></div>' +
        '<span class="slide-counter" id="slide-counter"></span>' +
        '<div class="toolbar-sep"></div>' +
        '<select id="add-layout-select" class="btn-ghost" style="width:auto" title="Layout for the new slide">' + layoutOpts + "</select>" +
        '<button class="btn btn-sm btn-ghost" id="btn-add-slide">+ Add slide</button>' +
        '<button class="btn btn-sm btn-ghost" id="btn-dup-slide" title="Duplicate current slide">Duplicate</button>' +
        '<button class="btn btn-sm btn-ghost" id="btn-del-slide" title="Delete current slide">Delete</button>' +
        '<button class="btn btn-sm btn-ghost" id="btn-move-left" title="Move slide left">←</button>' +
        '<button class="btn btn-sm btn-ghost" id="btn-move-right" title="Move slide right">→</button>' +
        '<div class="dropdown">' +
          '<button class="btn btn-sm" id="btn-export-menu">Export ▾</button>' +
          '<div class="dropdown-menu hidden" id="export-menu">' +
            '<button data-export="pptx">Download PPTX</button>' +
            '<button data-export="pdf">Download PDF</button>' +
            '<button data-export="html">Download HTML</button>' +
          "</div>" +
        "</div>" +
        '<span class="save-status" id="save-status"><span class="dot"></span><span>Saved</span></span>' +
      "</div>" +
      '<div class="editor-grid">' +
        '<div class="thumb-rail" id="thumb-rail"></div>' +
        '<div class="stage-wrap" id="stage-wrap"><div id="stage"><div class="spinner"></div></div></div>' +
        '<div class="inspector">' +
          '<div class="tabs">' +
            '<button class="tab active" data-tab="content">Content</button>' +
            '<button class="tab" data-tab="design">Design</button>' +
            '<button class="tab" data-tab="assist">AI Assist</button>' +
          "</div>" +
          '<div class="tab-body" id="tab-body"></div>' +
        "</div>" +
      "</div>" +
    "</div>";

  bindEditorToolbar();
  bindInspectorTabs();
  await renderThumbnails();
  await selectSlide(state.slideIdx);
  updateSlideCounter();

  let rsz;
  window.addEventListener("resize", () => { clearTimeout(rsz); rsz = setTimeout(() => renderStage(), 200); });
}

function bindEditorToolbar() {
  const p = () => state.project;
  $("#ed-back").addEventListener("click", () => navigate("dashboard"));

  $("#ed-title").addEventListener("input", (e) => {
    state.project.title = e.target.value;
    scheduleSave();
  });

  $("#btn-add-slide").addEventListener("click", async () => {
    const layout = $("#add-layout-select").value || (state.layouts[0] && state.layouts[0].id) || "title";
    const slide = { id: uid("slide"), layout: layout, elements: [], notes: "" };
    state.project.slides.splice(state.slideIdx + 1, 0, slide);
    state.slideIdx = state.slideIdx + 1;
    setSaveStatus("saving");
    try {
      state.project = await apiPut("/api/projects/" + encodeURIComponent(p().id), { slides: state.project.slides });
      setSaveStatus("saved");
      await renderThumbnails();
      await selectSlide(state.slideIdx);
      updateSlideCounter();
    } catch (e) {
      setSaveStatus("failed", e.message);
      showError("Could not add slide: " + e.message);
    }
  });

  $("#btn-dup-slide").addEventListener("click", async () => {
    const s = currentSlide();
    if (!s) return;
    const copy = JSON.parse(JSON.stringify(s));
    copy.id = uid("slide");
    (copy.elements || []).forEach((el) => { el.id = uid("el"); });
    state.project.slides.splice(state.slideIdx + 1, 0, copy);
    state.slideIdx = state.slideIdx + 1;
    setSaveStatus("saving");
    try {
      state.project = await apiPut("/api/projects/" + encodeURIComponent(p().id), { slides: state.project.slides });
      setSaveStatus("saved");
      await renderThumbnails();
      await selectSlide(state.slideIdx);
      updateSlideCounter();
    } catch (e) {
      setSaveStatus("failed", e.message);
      showError("Could not duplicate slide: " + e.message);
    }
  });

  $("#btn-del-slide").addEventListener("click", async () => {
    const s = currentSlide();
    if (!s) return;
    if (!confirm("Delete slide " + (state.slideIdx + 1) + "?")) return;
    invalidateSlideHtml(s.id);
    state.project.slides.splice(state.slideIdx, 1);
    if (!state.project.slides.length) {
      showError("A deck needs at least one slide — the last slide was kept.");
      state.project.slides.push(s);
      return;
    }
    state.slideIdx = Math.min(state.slideIdx, state.project.slides.length - 1);
    setSaveStatus("saving");
    try {
      state.project = await apiPut("/api/projects/" + encodeURIComponent(p().id), { slides: state.project.slides });
      setSaveStatus("saved");
      await renderThumbnails();
      await selectSlide(state.slideIdx);
      updateSlideCounter();
    } catch (e) {
      setSaveStatus("failed", e.message);
      showError("Could not delete slide: " + e.message);
    }
  });

  const move = async (dir) => {
    const i = state.slideIdx, n = state.project.slides.length;
    const j = i + dir;
    if (j < 0 || j >= n) return;
    const arr = state.project.slides;
    const t = arr[i]; arr[i] = arr[j]; arr[j] = t;
    state.slideIdx = j;
    setSaveStatus("saving");
    try {
      state.project = await apiPut("/api/projects/" + encodeURIComponent(p().id), { slides: state.project.slides });
      setSaveStatus("saved");
      await renderThumbnails();
      await selectSlide(state.slideIdx);
    } catch (e) {
      setSaveStatus("failed", e.message);
      showError("Could not move slide: " + e.message);
    }
  };
  $("#btn-move-left").addEventListener("click", () => move(-1));
  $("#btn-move-right").addEventListener("click", () => move(1));

  // export dropdown
  $("#btn-export-menu").addEventListener("click", (e) => {
    e.stopPropagation();
    $("#export-menu").classList.toggle("hidden");
  });
  $$("#export-menu [data-export]").forEach((b) =>
    b.addEventListener("click", () => {
      $("#export-menu").classList.add("hidden");
      runExport(state.project.id, b.dataset.export);
    })
  );
}

function updateSlideCounter() {
  const el = $("#slide-counter");
  if (el && state.project) el.textContent = "Slide " + (state.slideIdx + 1) + " / " + state.project.slides.length;
}

/* ---------- thumbnails ---------- */

async function renderThumbnails() {
  const rail = $("#thumb-rail");
  if (!rail || !state.project) return;
  const slides = state.project.slides;
  rail.innerHTML = slides
    .map((s, i) =>
      '<div class="thumb" data-idx="' + i + '" data-sid="' + esc(s.id) + '">' +
        '<div class="tnum">' + (i + 1) + "</div>" +
        '<div class="tloading"><div class="spinner sm"></div></div>' +
      "</div>"
    )
    .join("");
  $$(".thumb", rail).forEach((t) =>
    t.addEventListener("click", () => selectSlide(parseInt(t.dataset.idx, 10)))
  );
  markActiveThumb();
  // fetch html for each slide (tolerate individual failures)
  const results = await Promise.allSettled(slides.map((s) => getSlideHtml(state.project.id, s)));
  results.forEach((r, i) => {
    const t = $('.thumb[data-idx="' + i + '"]', rail);
    if (!t) return;
    if (r.status === "fulfilled") {
      t.innerHTML = '<div class="tnum">' + (i + 1) + "</div>" + slideFrameHTML(r.value, 164);
    } else {
      t.innerHTML = '<div class="tnum">' + (i + 1) + "</div>" + '<div class="tloading" style="height:92px;font-size:12px">Preview unavailable</div>';
    }
  });
}

function markActiveThumb() {
  $$(".thumb").forEach((t) => t.classList.toggle("active", parseInt(t.dataset.idx, 10) === state.slideIdx));
}

async function refreshThumb(idx) {
  const rail = $("#thumb-rail");
  if (!rail) return;
  const s = state.project.slides[idx];
  const t = $('.thumb[data-idx="' + idx + '"]', rail);
  if (!s || !t) return;
  try {
    const html = await getSlideHtml(state.project.id, s);
    t.innerHTML = '<div class="tnum">' + (idx + 1) + "</div>" + slideFrameHTML(html, 164);
  } catch (e) {
    t.innerHTML = '<div class="tnum">' + (idx + 1) + "</div>" + '<div class="tloading" style="height:92px;font-size:12px">Preview unavailable</div>';
  }
}

/* ---------- stage ---------- */

async function selectSlide(idx) {
  state.slideIdx = Math.max(0, Math.min(idx, state.project.slides.length - 1));
  markActiveThumb();
  updateSlideCounter();
  await renderStage();
  renderInspectorBody();
}

async function renderStage() {
  const wrap = $("#stage-wrap");
  const stage = $("#stage");
  if (!wrap || !stage) return;
  const s = currentSlide();
  if (!s) { stage.innerHTML = '<div class="empty-state">No slides</div>'; return; }
  const targetW = Math.max(320, Math.min(1000, wrap.clientWidth - 56));
  stage.innerHTML = '<div style="color:#8fa39a;font-weight:600"><div class="spinner" style="margin:0 auto 10px"></div>Rendering…</div>';
  try {
    const html = await getSlideHtml(state.project.id, s);
    stage.innerHTML = slideFrameHTML(html, targetW);
  } catch (e) {
    stage.innerHTML = '<div style="color:#e8b4ae;font-weight:600">Could not render slide: ' + esc(e.message) + "</div>";
  }
}

/* ---------- inspector ---------- */

function bindInspectorTabs() {
  $$(".tab").forEach((t) =>
    t.addEventListener("click", () => {
      $$(".tab").forEach((x) => x.classList.remove("active"));
      t.classList.add("active");
      state.currentInspectorTab = t.dataset.tab;
      renderInspectorBody();
    })
  );
}

function renderInspectorBody() {
  const body = $("#tab-body");
  if (!body) return;
  const tab = state.currentInspectorTab;
  if (tab === "content") renderContentTab(body);
  else if (tab === "design") renderDesignTab(body);
  else renderAssistTab(body);
}

function renderContentTab(body) {
  const s = currentSlide();
  if (!s) { body.innerHTML = '<div class="hint">No slide selected.</div>'; return; }
  const textEls = (s.elements || []).filter((el) => el.type === "text");
  let html = "";
  if (!textEls.length) {
    html += '<div class="note-inline" style="margin-bottom:14px">This slide has no editable text elements.</div>';
  }
  html += textEls
    .map((el) =>
      '<div class="el-block" data-el="' + esc(el.id) + '">' +
        "<label>" + esc(el.role || el.type || "text") + "</label>" +
        '<textarea data-eltext>' + esc(el.text || "") + "</textarea>" +
      "</div>"
    )
    .join("");
  html +=
    '<div class="el-block"><label>Speaker notes</label>' +
    '<textarea id="insp-notes" rows="4" placeholder="Notes for the presenter…">' + esc(s.notes || "") + "</textarea></div>";
  body.innerHTML = html;

  $$("[data-el]", body).forEach((blk) => {
    const elId = blk.dataset.el;
    const el = (s.elements || []).find((x) => String(x.id) === String(elId));
    if (!el) return;
    $("[data-eltext]", blk).addEventListener("input", (e) => {
      el.text = e.target.value;
      scheduleSave(async () => {
        invalidateSlideHtml(s.id);
        await renderStage();
        await refreshThumb(state.slideIdx);
      });
    });
  });
  $("#insp-notes").addEventListener("input", (e) => {
    s.notes = e.target.value;
    scheduleSave();
  });
}

function renderDesignTab(body) {
  const s = currentSlide();
  if (!s) { body.innerHTML = '<div class="hint">No slide selected.</div>'; return; }
  const layoutOpts = state.layouts
    .map((l) => '<option value="' + esc(l.id) + '"' + (l.id === s.layout ? " selected" : "") + ">" + esc(l.name) + "</option>")
    .join("");
  const themeOpts = state.themes
    .map((t) => '<option value="' + esc(t.id) + '"' + (t.id === state.project.theme ? " selected" : "") + ">" + esc(t.name) + "</option>")
    .join("");
  body.innerHTML =
    '<div class="el-block"><label>Slide layout</label>' +
      '<select id="insp-layout">' + layoutOpts + "</select>" +
      '<div class="hint">Changing the layout re-renders this slide.</div></div>' +
    '<div class="el-block"><label>Deck theme</label>' +
      '<select id="insp-theme">' + themeOpts + "</select>" +
      '<div class="hint">Applies to every slide in the deck.</div></div>';
  $("#insp-layout").addEventListener("change", (e) => {
    s.layout = e.target.value;
    scheduleSave(async () => {
      invalidateSlideHtml(s.id);
      await renderStage();
      await refreshThumb(state.slideIdx);
    });
  });
  $("#insp-theme").addEventListener("change", (e) => {
    state.project.theme = e.target.value;
    scheduleSave(async () => {
      invalidateAllSlideHtml();
      await renderThumbnails();
      await selectSlide(state.slideIdx);
    });
  });
}

function renderAssistTab(body) {
  const s = currentSlide();
  body.innerHTML =
    '<div class="el-block"><label>Instruction for the AI</label>' +
    '<textarea id="assist-instruction" rows="4" placeholder="e.g. Make the bullets punchier for a student audience…"></textarea></div>' +
    '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
      '<button class="btn btn-sm" id="assist-improve">Improve text</button>' +
      '<button class="btn btn-sm btn-ghost" id="assist-relayout">Suggest new layout</button>' +
    "</div>" +
    '<div id="assist-result"></div>' +
    '<div class="hint" style="margin-top:12px">AI Assist needs a configured provider (OpenAI, Gemini or Ollama). It does not work with the offline composer.</div>';
  if (!s) return;
  const run = async (task, btn) => {
    const instruction = $("#assist-instruction").value.trim();
    const resBox = $("#assist-result");
    resBox.innerHTML = "";
    const orig = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner sm"></span> Thinking…';
    try {
      const updated = await apiPost("/api/assist", {
        project_id: state.project.id,
        slide_id: s.id,
        task: task,
        instruction: instruction,
      });
      state.project = updated;
      state.slideIdx = Math.min(state.slideIdx, state.project.slides.length - 1);
      invalidateAllSlideHtml();
      await renderThumbnails();
      await selectSlide(state.slideIdx);
      updateSlideCounter();
      setSaveStatus("saved");
      resBox.innerHTML = '<div class="assist-result ok">Done — the AI changes have been applied to this slide.</div>';
    } catch (e) {
      // honest error, e.g. 400 when provider is offline — never fake a result
      resBox.innerHTML = '<div class="assist-result err"><strong>AI Assist could not run.</strong><br>' + esc(e.message) + "</div>";
    } finally {
      btn.disabled = false;
      btn.innerHTML = orig;
    }
  };
  $("#assist-improve").addEventListener("click", (e) => run("improve", e.currentTarget));
  $("#assist-relayout").addEventListener("click", (e) => run("relayout", e.currentTarget));
}

/* ============================================================
   7. Settings view
   ============================================================ */

const PROVIDER_META = {
  openai: {
    title: "OpenAI-compatible",
    fields: [
      { key: "base_url", label: "Base URL", type: "text", def: "https://api.openai.com/v1", ph: "https://api.openai.com/v1" },
      { key: "model", label: "Model", type: "text", def: "", ph: "e.g. gpt-4o-mini" },
      { key: "api_key", label: "API key", type: "password", def: "", ph: "sk-…" },
    ],
  },
  gemini: {
    title: "Google Gemini",
    fields: [
      { key: "model", label: "Model", type: "text", def: "gemini-3.8-flash", ph: "gemini-3.8-flash" },
      { key: "api_key", label: "API key", type: "password", def: "", ph: "AIza…" },
    ],
  },
  ollama: {
    title: "Ollama (local)",
    fields: [
      { key: "base_url", label: "Base URL", type: "text", def: "http://localhost:11434", ph: "http://localhost:11434" },
      { key: "model", label: "Model", type: "text", def: "", ph: "e.g. llama3.1" },
    ],
  },
};

async function renderSettings() {
  const root = $("#view-root");
  root.innerHTML =
    '<div class="view">' +
      '<button class="back-link" id="set-back">← Back to dashboard</button>' +
      '<h2 class="section-title">AI provider settings</h2>' +
      '<p class="section-sub">Configure the providers used for outline generation, slide building and AI Assist. The offline composer always works without a key.</p>' +
      '<div class="provider-grid" id="provider-grid"><div class="card"><div class="spinner"></div> Loading…</div></div>' +
      '<div class="keys-note"><strong>Note:</strong> API keys are stored server-side only and are never shown back in the browser. Leaving the key field blank when saving keeps the existing key unchanged.</div>' +
    "</div>";
  $("#set-back").addEventListener("click", () => navigate("dashboard"));

  try {
    state.settings = await apiGet("/api/settings");
  } catch (e) {
    $("#provider-grid").innerHTML = '<div class="card">Could not load settings: ' + esc(e.message) + "</div>";
    return;
  }
  const provs = (state.settings && state.settings.providers) || {};
  const grid = $("#provider-grid");
  grid.innerHTML = Object.keys(PROVIDER_META)
    .map((key) => {
      const meta = PROVIDER_META[key];
      const cur = provs[key] || {};
      const configured = !!cur.configured;
      const fields = meta.fields
        .map((f) => {
          const val = f.key === "api_key" ? "" : (cur[f.key] || f.def || "");
          return (
            '<div class="field"><label>' + esc(f.label) + "</label>" +
            '<input type="' + f.type + '" data-pk="' + key + '" data-fk="' + f.key + '" value="' + esc(val) + '" placeholder="' + esc(f.ph || "") + '" autocomplete="off">' +
            (f.key === "api_key" && configured ? '<div class="hint">A key is already saved — leave blank to keep it.</div>' : "") +
            "</div>"
          );
        })
        .join("");
      return (
        '<div class="card provider-card">' +
          '<div class="phead"><h3>' + esc(meta.title) + "</h3>" +
          '<span class="configured-pill' + (configured ? "" : " no") + '">' + (configured ? "Configured" : "Not configured") + "</span></div>" +
          fields +
          '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
            '<button class="btn btn-sm" data-save="' + key + '">Save</button>' +
            '<button class="btn btn-sm btn-ghost" data-test="' + key + '">Test connection</button>' +
          "</div>" +
          '<div class="test-result hidden" data-result="' + key + '"></div>' +
        "</div>"
      );
    })
    .join("");

  const showResult = (key, ok, msg) => {
    const box = $('[data-result="' + key + '"]', grid);
    box.classList.remove("hidden", "ok", "err");
    box.classList.add(ok ? "ok" : "err");
    box.textContent = (ok ? "✓ Connection works. " : "✕ ") + (msg || "");
  };

  $$("[data-save]", grid).forEach((btn) =>
    btn.addEventListener("click", withButtonSpinner(btn, async () => {
      const key = btn.dataset.save;
      const meta = PROVIDER_META[key];
      const config = {};
      meta.fields.forEach((f) => {
        const inp = $('input[data-pk="' + key + '"][data-fk="' + f.key + '"]', grid);
        const v = inp.value.trim();
        if (f.key === "api_key") { if (v) config.api_key = v; }
        else if (v) config[f.key] = v;
        else if (f.def) config[f.key] = f.def;
      });
      await apiPost("/api/settings", { provider: key, config: config });
      state.settings = await apiGet("/api/settings");
      renderSettings();
      // show confirmation after re-render (re-render rebuilds the result boxes)
      const box = $('[data-result="' + key + '"]');
      if (box) {
        box.classList.remove("hidden");
        box.classList.add("ok");
        box.textContent = "✓ Settings saved.";
      }
    }))
  );

  $$("[data-test]", grid).forEach((btn) =>
    btn.addEventListener("click", withButtonSpinner(btn, async () => {
      const key = btn.dataset.test;
      try {
        const r = await apiPost("/api/settings/test", { provider: key });
        if (r && r.ok) showResult(key, true, r.message || "Connection OK.");
        else showResult(key, false, (r && r.error) || "Test failed.");
      } catch (e) {
        showResult(key, false, e.message);
      }
    }))
  );
}

/* ============================================================
   8. Shared: export (validation panel + download)
   ============================================================ */

function normalizeValidation(v) {
  if (!v) return [];
  let arr = null;
  if (Array.isArray(v)) arr = v;
  else if (Array.isArray(v.checks)) arr = v.checks;
  else if (Array.isArray(v.results)) arr = v.results;
  if (arr) {
    return arr.map((c) => ({
      name: c.name || c.check || c.title || "Check",
      passed: c.passed === true || c.ok === true || c.status === "pass" || c.status === "passed",
      detail: c.detail || c.message || c.info || "",
    }));
  }
  if (typeof v === "object") {
    return Object.keys(v).map((k) => ({ name: k, passed: !!v[k], detail: "" }));
  }
  return [];
}

async function runExport(projectId, format) {
  setLoading(true, "Exporting " + format.toUpperCase() + "…");
  try {
    const data = await apiPost("/api/projects/" + encodeURIComponent(projectId) + "/export", { format: format });
    if (!data || !data.ok) throw new Error((data && data.error) || "Export failed.");
    openExportModal(data.filename || ("export." + format), data.validation, data.download_url);
  } catch (e) {
    showError("Export failed: " + e.message);
  } finally {
    setLoading(false);
  }
}

function openExportModal(filename, validation, downloadUrl) {
  const checks = normalizeValidation(validation);
  const rows = checks.length
    ? checks.map((c) =>
        '<div class="check-row ' + (c.passed ? "pass" : "fail") + '">' +
          '<span class="cicon">' + (c.passed ? "✓" : "✕") + "</span>" +
          "<div><div><strong>" + esc(c.name) + "</strong> — " + (c.passed ? "passed" : "failed") + "</div>" +
          (c.detail ? '<div class="cdetail">' + esc(c.detail) + "</div>" : "") + "</div>" +
        "</div>"
      ).join("")
    : '<div class="hint">The server did not return validation details.</div>';
  const failed = checks.filter((c) => !c.passed).length;

  $("#modal-root").innerHTML =
    '<div class="modal-overlay" id="export-overlay">' +
      '<div class="modal">' +
        "<h3>Export complete</h3>" +
        '<p class="section-sub" style="margin-bottom:6px"><strong>' + esc(filename) + "</strong></p>" +
        (failed
          ? '<div class="assist-result err" style="margin-bottom:6px"><strong>' + failed + " check(s) failed.</strong> The file was still produced — review the details below.</div>"
          : '<div class="assist-result ok" style="margin-bottom:6px">All validation checks passed.</div>') +
        '<div class="validation-list">' + rows + "</div>" +
        '<div class="modal-actions">' +
          (downloadUrl
            ? '<a class="btn" href="' + esc(downloadUrl) + '" download="' + esc(filename) + '">Download file</a>'
            : '<span class="hint">No download URL was returned by the server.</span>') +
          '<button class="btn btn-ghost" id="export-close">Close</button>' +
        "</div>" +
      "</div>" +
    "</div>";

  const close = () => { $("#modal-root").innerHTML = ""; };
  $("#export-close").addEventListener("click", close);
  $("#export-overlay").addEventListener("click", (e) => { if (e.target.id === "export-overlay") close(); });
  document.addEventListener("keydown", function escClose(e) {
    if (e.key === "Escape") { close(); document.removeEventListener("keydown", escClose); }
  });
}

/* ============================================================
   9. Init
   ============================================================ */

async function loadReferenceData() {
  const results = await Promise.allSettled([
    apiGet("/api/themes"),
    apiGet("/api/layouts"),
  ]);
  if (results[0].status === "fulfilled" && Array.isArray(results[0].value)) {
    state.themes = results[0].value;
  } else if (results[0].status === "rejected") {
    showError("Could not load themes: " + results[0].reason.message);
  }
  if (results[1].status === "fulfilled" && Array.isArray(results[1].value)) {
    state.layouts = results[1].value;
  } else if (results[1].status === "rejected") {
    showError("Could not load layouts: " + results[1].reason.message);
  }
}

function bindShell() {
  $("#error-close").addEventListener("click", clearError);
  $$(".nav-btn").forEach((b) => b.addEventListener("click", () => navigate(b.dataset.nav)));
  const brand = $("#brand-home");
  if (brand) brand.addEventListener("click", () => navigate("dashboard"));
  // single global handler: close any open dropdown menu on outside click
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".dropdown")) $$(".dropdown-menu").forEach((m) => m.classList.add("hidden"));
  });
}

async function init() {
  bindShell();
  setLoading(true, "Loading Aesthetic AI Studio…");
  try {
    await loadReferenceData();
  } finally {
    setLoading(false);
  }
  navigate("dashboard");
}

document.addEventListener("DOMContentLoaded", init);

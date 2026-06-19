// Reader frontend. Wires live controls (book picker, chapter nav, density swap,
// dialogue-forward) to the FastAPI backend. Density switching uses pre-baked tiers
// from the cache - never re-bills the LLM (CLAUDE.md cost UX).

const state = {
  books: [],
  bookId: null,
  index: 0,
  chaptersCount: 0,
  chapter: null,
  density: 60,
  densityTiers: [100, 60, 40],
};

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail;
    try { detail = (await res.json()).detail; }
    catch { detail = await res.text(); }
    throw new Error(`${res.status} ${detail || res.statusText}`);
  }
  return res.json();
}

async function init() {
  try {
    const cfg = await api("/api/bindings");
    state.densityTiers = cfg.density_tiers;
    syncDensityOptions();
  } catch (e) {
    showStatus(`Backend unreachable: ${e.message}`, true);
    return;
  }

  await refreshBooks();

  document.getElementById("density").addEventListener("change", (e) => {
    state.density = parseInt(e.target.value, 10);
    renderChapter();
  });

  document.getElementById("dialogue-mode").addEventListener("change", (e) => {
    document.body.classList.toggle("dialogue-forward", e.target.checked);
  });
}

function syncDensityOptions() {
  const sel = document.getElementById("density");
  sel.innerHTML = state.densityTiers
    .map((d) => `<option value="${d}" ${d === state.density ? "selected" : ""}>${d}%</option>`)
    .join("");
}

async function refreshBooks() {
  state.books = await api("/api/books");
  renderBookPicker();
}

function renderBookPicker() {
  const el = document.getElementById("book-picker");
  if (state.books.length === 0) {
    el.innerHTML = '<span class="muted">no books</span>';
    return;
  }
  const opts = ['<option value="">Pick a book...</option>'].concat(
    state.books.map(
      (b) =>
        `<option value="${b.id}">${escapeHTML(b.title)}${b.processed ? "" : " (unprocessed)"}</option>`,
    ),
  );
  el.innerHTML = `<select id="book-select">${opts.join("")}</select>`;
  document.getElementById("book-select").addEventListener("change", (e) => {
    if (e.target.value) loadBook(e.target.value);
  });
}

async function loadBook(bookId) {
  const book = state.books.find((b) => b.id === bookId);
  state.bookId = bookId;

  if (!book.processed) {
    if (!confirm(
      `"${book.title}" hasn't been processed yet. Running the pipeline will call your LLM provider and charge your API account. Continue?`,
    )) {
      return;
    }
    showStatus(`Processing "${book.title}". This can take several minutes - watch the terminal for chapter-by-chapter progress.`);
    try {
      await api(`/api/books/${encodeURIComponent(bookId)}/process`, { method: "POST" });
    } catch (e) {
      showStatus(`Processing failed: ${e.message}`, true);
      return;
    }
    await refreshBooks();
    hideStatus();
  }

  await loadChapter(0);
  await refreshCost();
}

async function loadChapter(index) {
  state.index = index;
  try {
    state.chapter = await api(
      `/api/books/${encodeURIComponent(state.bookId)}/chapters/${index}`,
    );
    state.chaptersCount = state.chapter.chapters_count;
  } catch (e) {
    showStatus(`Couldn't load chapter ${index + 1}: ${e.message}`, true);
    return;
  }
  hideStatus();
  renderChapter();
  renderNav();
}

function renderChapter() {
  const reader = document.getElementById("reader");
  const ch = state.chapter;
  if (!ch) {
    reader.innerHTML = '<p class="placeholder">Select a book to begin.</p>';
    return;
  }

  const rewrite = ch.rewrites[String(state.density)];
  if (!rewrite || !rewrite.spans) {
    reader.innerHTML = `<p class="placeholder">No ${state.density}% tier cached for this chapter.</p>`;
    return;
  }

  const frag = document.createDocumentFragment();

  const titleEl = document.createElement("h2");
  titleEl.className = "chapter-title";
  titleEl.textContent = ch.title;
  frag.appendChild(titleEl);

  for (const span of rewrite.spans) {
    const p = document.createElement("p");
    const kind = ["dialogue", "narration", "beat"].includes(span.kind) ? span.kind : "narration";
    p.className = `line-${kind}`;
    p.textContent = span.text;
    // Store the source span so a future "show original" toggle has the data.
    if (span.source) {
      p.dataset.sourceStart = span.source.char_start;
      p.dataset.sourceEnd = span.source.char_end;
    }
    frag.appendChild(p);
  }

  reader.innerHTML = "";
  reader.appendChild(frag);
  reader.scrollTo({ top: 0, behavior: "instant" });
}

function renderNav() {
  const nav = document.getElementById("chapter-nav");
  if (!state.bookId || state.chaptersCount === 0) {
    nav.innerHTML = "";
    return;
  }
  nav.innerHTML = `
    <button id="prev-btn" ${state.index === 0 ? "disabled" : ""}>&laquo; Prev</button>
    <span class="ch-counter">Ch. ${state.index + 1} / ${state.chaptersCount}</span>
    <button id="next-btn" ${state.index >= state.chaptersCount - 1 ? "disabled" : ""}>Next &raquo;</button>
  `;
  document.getElementById("prev-btn").onclick = () => loadChapter(state.index - 1);
  document.getElementById("next-btn").onclick = () => loadChapter(state.index + 1);
}

async function refreshCost() {
  if (!state.bookId) return;
  try {
    const c = await api(`/api/books/${encodeURIComponent(state.bookId)}/cost`);
    const el = document.getElementById("cost-meter");
    el.textContent = `$${(c.usd || 0).toFixed(4)}`;
    el.title = `in=${c.input_tokens} out=${c.output_tokens} cached=${c.cached_input_tokens}`;
  } catch {
    // Silent - cost is informational
  }
}

function showStatus(text, isError = false) {
  const el = document.getElementById("status");
  el.textContent = text;
  el.classList.toggle("error", isError);
  el.hidden = false;
}

function hideStatus() {
  document.getElementById("status").hidden = true;
}

function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

init();

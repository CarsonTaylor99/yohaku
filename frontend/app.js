// Reader frontend — scaffolding. Wires the live controls to the (stubbed) backend.

const densityEl = document.getElementById("density");
const dialogueEl = document.getElementById("dialogue-mode");

// Density selector switches between PRE-BAKED tiers instantly — never re-bills the LLM.
densityEl?.addEventListener("change", () => {
  // TODO: swap the rendered chapter to the selected baked tier.
  console.log("density ->", densityEl.value);
});

// Dialogue-forward mode is separate from the density slider (CLAUDE.md).
dialogueEl?.addEventListener("change", () => {
  document.body.classList.toggle("dialogue-forward", dialogueEl.checked);
});

async function loadBindings() {
  // TODO: render per-task provider/model toggles from this.
  try {
    const res = await fetch("/api/bindings");
    console.log("bindings", await res.json());
  } catch (e) {
    console.warn("backend not running yet", e);
  }
}

loadBindings();

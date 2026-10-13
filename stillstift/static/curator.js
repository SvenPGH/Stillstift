import { ApiError, api, button, byId, el, json } from "./dom.js";
import { stepIndex, tiles } from "./grid.js";
import {
  FLAWS,
  PARTS,
  TRI_ROWS,
  blankDraft,
  deletePrompt,
  draftOf,
  entryAfterDelete,
  entryStatus,
  favoriteButton,
  isRated,
  nextEntry,
  nextUnrated,
  othersLines,
  payload,
  submitButton,
  toggled,
  withFlaw,
  withTri,
} from "./rating.js";
import { isLab, labBadge } from "./kinds.js";
import {
  flawChips,
  ratedText,
  renderStepRow,
  renderSubmit,
  segmentSlots,
  starRow,
  triRows,
} from "./rate-ui.js";
import { watchChanges } from "./live.js";
import { mountShell } from "./shell.js";
import {
  draftKey,
  keptDrafts,
  neighbour,
  openingDraft,
  stepList,
} from "./steps.js";
import { wireSwipe } from "./swipe.js";

/** @typedef {import("./rating.js").CellView} CellView */
/** @typedef {import("./rating.js").Draft} Draft */
/** @typedef {import("./rating.js").EntrySummary} EntrySummary */
/** @typedef {import("./rating.js").Rating} Rating */
/** @typedef {import("./rating.js").SaveStatus} SaveStatus */
/** @typedef {import("./rating.js").Button} Button */
/** @typedef {"loading" | "rate" | "grid" | "empty"} View */
/** @typedef {"all" | "P" | "X" | "T"} PickerKind */

/** @type {readonly PickerKind[]} */
const PICKER_KINDS = ["all", "P", "X", "T"];

const SAVED_PAUSE_MS = 650;
/** Where the rating view shows the phone-sized preview instead of the full render. */
const PHONE = window.matchMedia("(max-width: 700px)");

const ui = {
  picker: byId("picker", HTMLButtonElement),
  pickerId: byId("picker-id", HTMLElement),
  pickerSub: byId("picker-sub", HTMLElement),
  pickerList: byId("picker-list", HTMLElement),
  progress: byId("progress", HTMLElement),
  nav: byId("nav", HTMLElement),
  actions: byId("actions", HTMLElement),
  segments: byId("segments", HTMLElement),
  prompt: byId("prompt", HTMLElement),
  promptClose: byId("prompt-close", HTMLButtonElement),
  promptText: byId("prompt-text", HTMLElement),
  negativeText: byId("negative-text", HTMLElement),
  settings: byId("settings", HTMLElement),
  rate: byId("rate", HTMLElement),
  frame: byId("frame", HTMLElement),
  image: byId("image", HTMLImageElement),
  zoom: byId("zoom", HTMLButtonElement),
  imgCode: byId("img-code", HTMLElement),
  imgSize: byId("img-size", HTMLElement),
  lightbox: byId("lightbox", HTMLElement),
  lbTitle: byId("lb-title", HTMLElement),
  lbRate: byId("lb-rate", HTMLButtonElement),
  lbClose: byId("lb-close", HTMLButtonElement),
  lbStage: byId("lb-stage", HTMLElement),
  lbPrev: byId("lb-prev", HTMLButtonElement),
  lbNext: byId("lb-next", HTMLButtonElement),
  stepPrev: byId("step-prev", HTMLButtonElement),
  stepNext: byId("step-next", HTMLButtonElement),
  stepPos: byId("step-pos", HTMLElement),
  stepDrafts: byId("step-drafts", HTMLElement),
  stepScope: byId("step-scope", HTMLElement),
  cellCode: byId("cell-code", HTMLElement),
  labBadge: byId("lab-badge", HTMLElement),
  intent: byId("intent", HTMLElement),
  stars: byId("stars", HTMLElement),
  others: byId("others", HTMLElement),
  flaws: byId("flaws", HTMLElement),
  tri: byId("tri", HTMLElement),
  why: byId("why", HTMLTextAreaElement),
  empty: byId("empty", HTMLElement),
  emptyText: byId("empty-text", HTMLElement),
  emptyGo: byId("empty-go", HTMLButtonElement),
  back: byId("back", HTMLButtonElement),
  grid: byId("grid", HTMLElement),
  gridTitle: byId("grid-title", HTMLElement),
  favText: byId("fav-text", HTMLElement),
  tiles: byId("tiles", HTMLElement),
  note: byId("note", HTMLElement),
  dock: byId("dock", HTMLElement),
  dockPrev: byId("dock-prev", HTMLButtonElement),
  dockNext: byId("dock-next", HTMLButtonElement),
  submit: byId("submit", HTMLButtonElement),
};

const state = {
  /** @type {EntrySummary[]} */
  entries: [],
  entry: "",
  /** @type {CellView[]} */
  cells: [],
  /** @type {View} */
  view: "loading",
  cur: 0,
  draft: blankDraft(),
  /** @type {SaveStatus} */
  status: "idle",
  returnToGrid: false,
  /** @type {string | null} */
  favorite: null,
  /** @type {SaveStatus} */
  gridStatus: "idle",
  /** @type {{ entry: string, cell: string }[]} */
  history: [],
  pickerOpen: false,
  promptOpen: false,
  deleteFailed: false,
  /** @type {number | null} the index of the cell the lightbox shows */
  lightbox: null,
  /** @type {import("./steps.js").Drafts} */
  drafts: {},
  /** @type {import("./steps.js").Scope} */
  scope: "torate",
  /** @type {PickerKind} */
  pickerKind: "all",
};

/**
 * @param {string} entry
 * @param {string} cellId
 */
function ratingUrl(entry, cellId) {
  return `${entryUrl(entry)}/cells/${encodeURIComponent(cellId)}/rating`;
}

/** @param {string} entry */
function entryUrl(entry) {
  return `/api/entries/${encodeURIComponent(entry)}`;
}

/** The picked rater, kept per browser; null until one is picked in the header menu. */
function rater() {
  return shell.currentRater();
}

/** @param {string} url */
function withRater(url) {
  const picked = rater();
  if (picked === null) return url;
  const join = url.includes("?") ? "&" : "?";
  return `${url}${join}rater=${encodeURIComponent(picked)}`;
}

function summary() {
  return state.entries.find((e) => e.entry === state.entry) ?? null;
}

function currentCell() {
  return state.view === "rate" ? (state.cells[state.cur] ?? null) : null;
}

/** @param {EventTarget | null} target */
function typing(target) {
  return (
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLInputElement ||
    target instanceof HTMLSelectElement
  );
}

function toTop() {
  window.scrollTo(0, 0);
}

function grow() {
  ui.why.style.height = "auto";
  ui.why.style.height = `${String(ui.why.scrollHeight + 2)}px`;
}

/** @param {(draft: Draft) => Draft} change */
function edit(change) {
  state.draft = change(state.draft);
  if (state.status === "failed") state.status = "idle";
  render();
}

async function loadEntries() {
  state.entries = /** @type {EntrySummary[]} */ (
    await api(withRater("/api/entries"))
  );
}

/** Leaving the open cell: keep its draft if it differs from its rating, else drop it. */
function stash() {
  const cell = currentCell();
  if (cell === null || state.status === "saved") return;
  const key = draftKey(state.entry, cell.cell_id);
  state.drafts = keptDrafts(state.drafts, key, state.draft, cell);
}

/** @param {-1 | 1} delta */
function stepCell(delta) {
  const list = stepList(state.cells, state.cur, state.scope);
  const next = neighbour(list, state.cur, delta);
  if (next >= 0) openCell(next, state.returnToGrid);
}

/** @param {string} entry */
async function loadCells(entry) {
  const url = withRater(`${entryUrl(entry)}/cells`);
  state.cells = /** @type {CellView[]} */ (await api(url));
}

/**
 * @param {number} index
 * @param {boolean} [fromGrid]
 */
function openCell(index, fromGrid = false) {
  const cell = state.cells[index];
  if (cell === undefined) return;
  stash();
  state.view = "rate";
  state.cur = index;
  state.returnToGrid = fromGrid;
  state.draft = openingDraft(
    state.drafts,
    draftKey(state.entry, cell.cell_id),
    cell,
  );
  state.status = "idle";
  state.promptOpen = false;
  ui.why.value = state.draft.reason;
  render();
  grow();
  toTop();
}

function openGrid() {
  stash();
  state.view = "grid";
  state.returnToGrid = false;
  state.promptOpen = false;
  state.favorite = state.cells.find((c) => c.favorite)?.cell_id ?? null;
  state.gridStatus = "idle";
  render();
  toTop();
}

/** @param {string} entry */
async function openEntry(entry) {
  stash();
  state.view = "loading";
  state.entry = entry;
  state.deleteFailed = false;
  state.lightbox = null;
  state.pickerOpen = false;
  state.promptOpen = false;
  history.replaceState(null, "", `#${entry}`);
  await loadCells(entry);
  if (state.cells.length === 0) {
    state.view = "empty";
    render();
    toTop();
    return;
  }
  const first = nextUnrated(state.cells, 0);
  if (first < 0) openGrid();
  else openCell(first);
}

/**
 * Take in what changed elsewhere: the sets, and the open set's cells, keeping the open
 * cell, its draft and the view. A set that was empty opens once its first cell arrives.
 */
async function refresh() {
  if (state.status === "saving" || state.view === "loading")
    throw new Error("busy: the next check tries again");
  await loadEntries();
  if (state.entry === "") {
    const first = state.entries.find((e) => e.unrated > 0) ?? state.entries[0];
    if (first !== undefined) await openEntry(first.entry);
    else render();
    return;
  }
  const open = currentCell()?.cell_id ?? null;
  await loadCells(state.entry);
  if (state.view === "empty" && state.cells.length > 0) {
    const first = nextUnrated(state.cells, 0);
    if (first < 0) openGrid();
    else openCell(first);
    return;
  }
  const at = state.cells.findIndex((c) => c.cell_id === open);
  if (at >= 0) state.cur = at;
  render();
}

async function submit() {
  const cell = currentCell();
  const body = payload(state.draft);
  if (cell === null || body === null || rater() === null) return;
  if (state.status === "saving" || state.status === "saved") return;
  state.status = "saving";
  render();
  try {
    await api(withRater(ratingUrl(state.entry, cell.cell_id)), {
      method: "POST",
      ...json(body),
    });
  } catch {
    state.status = "failed";
    render();
    return;
  }
  cell.rating = body;
  cell.verdict = null;
  const entry = state.entry;
  state.drafts = keptDrafts(
    state.drafts,
    draftKey(entry, cell.cell_id),
    draftOf(body),
    cell,
  );
  state.history = [
    ...state.history.filter(
      (h) => h.entry !== entry || h.cell !== cell.cell_id,
    ),
    { entry, cell: cell.cell_id },
  ];
  state.status = "saved";
  render();
  await loadEntries();
  window.setTimeout(advance, SAVED_PAUSE_MS);
}

function advance() {
  const next = nextUnrated(state.cells, state.cur + 1);
  if (state.returnToGrid || next < 0) openGrid();
  else openCell(next);
}

async function saveFavorite() {
  const favorite = state.favorite;
  if (favorite === null || state.gridStatus === "saving" || rater() === null)
    return;
  state.gridStatus = "saving";
  render();
  try {
    await api(withRater(`${entryUrl(state.entry)}/favorite`), {
      method: "PUT",
      ...json({ cell: favorite }),
    });
  } catch {
    state.gridStatus = "failed";
    render();
    return;
  }
  for (const cell of state.cells) cell.favorite = cell.cell_id === favorite;
  state.gridStatus = "saved";
  render();
}

function onGridButton() {
  const next = nextEntry(state.entries, state.entry);
  if (state.gridStatus === "saved") {
    if (next !== null) void openEntry(next);
    return;
  }
  void saveFavorite();
}

async function undo() {
  const last = state.history.at(-1);
  if (last === undefined || rater() === null) return;
  /** @type {Rating} */
  let removed;
  try {
    removed = /** @type {Rating} */ (
      await api(withRater(ratingUrl(last.entry, last.cell)), {
        method: "DELETE",
      })
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      state.history.pop();
      render();
    }
    return;
  }
  state.history.pop();
  stash();
  state.view = "loading";
  state.entry = last.entry;
  history.replaceState(null, "", `#${last.entry}`);
  await Promise.all([loadEntries(), loadCells(last.entry)]);
  const index = state.cells.findIndex((c) => c.cell_id === last.cell);
  openCell(index);
  state.draft = draftOf(removed);
  ui.why.value = state.draft.reason;
  render();
  grow();
}

async function deleteSet() {
  const entry = state.entry;
  if (!window.confirm(deletePrompt(entry, state.cells))) return;
  try {
    await api(entryUrl(entry), { method: "DELETE" });
  } catch {
    state.deleteFailed = true;
    render();
    return;
  }
  state.history = state.history.filter((h) => h.entry !== entry);
  await loadEntries();
  const next = entryAfterDelete(state.entries);
  if (next !== null) {
    await openEntry(next);
    return;
  }
  state.entry = "";
  state.cells = [];
  state.view = "loading";
  history.replaceState(null, "", location.pathname);
  render();
}

function renderStars() {
  const d = state.draft;
  const parts = isLab(state.entry) ? [] : PARTS;
  ui.stars.replaceChildren(
    ...parts.map(([part, label]) =>
      starRow(label, d.rows[part] ?? null, false, (stars) => {
        edit((x) => ({ ...x, rows: { ...x.rows, [part]: stars } }));
      }),
    ),
    starRow("Render", d.render, true, (stars) => {
      edit((x) => ({ ...x, render: stars }));
    }),
    starRow("Liked", d.taste, true, (stars) => {
      edit((x) => ({ ...x, taste: stars }));
    }),
  );
}

function renderFlaws() {
  ui.flaws.replaceChildren(
    ...flawChips(FLAWS, state.draft.flaws, (flaw) => {
      edit((x) => withFlaw(x, flaw));
    }),
  );
}

function renderTri() {
  ui.tri.replaceChildren(
    ...triRows(TRI_ROWS, state.draft, (key, option) => {
      edit((x) => withTri(x, key, option));
    }),
  );
}

/**
 * The rating view's image: the preview on a phone, to spare mobile data; the full render opens
 * from it, in the lightbox.
 * @param {CellView} cell
 */
function viewImage(cell) {
  return PHONE.matches ? cell.preview : cell.image;
}

/** Fetch the next cell's image ahead, so stepping on shows it at once. */
function preloadNext() {
  const list = stepList(state.cells, state.cur, state.scope);
  const next = state.cells[neighbour(list, state.cur, 1)];
  if (next !== undefined) new Image().src = viewImage(next);
}

/** @param {CellView} cell */
function renderImage(cell) {
  const src = viewImage(cell);
  if (ui.image.getAttribute("src") !== src) {
    ui.image.src = src;
    preloadNext();
  }
  ui.image.alt = `Image ${state.entry} ${cell.cell_id}`;
  ui.imgCode.textContent = `${state.entry} · ${cell.cell_id}`;
  const size = cell.settings.find(([key]) => key === "size");
  ui.imgSize.textContent = size === undefined ? "" : `image · ${size[1]}`;
}

/** @param {CellView} cell */
function renderOthers(cell) {
  const lines = othersLines(cell.others);
  ui.others.replaceChildren(...lines.map((line) => el("div", "", line)));
  ui.others.hidden = lines.length === 0;
}

/** @param {CellView} cell */
function renderRate(cell) {
  renderImage(cell);
  renderStep();
  ui.back.hidden = !state.returnToGrid;
  ui.cellCode.textContent = `${state.entry} · ${cell.cell_id}`;
  const badge = labBadge(state.entry);
  ui.labBadge.hidden = badge === "";
  ui.labBadge.textContent = badge;
  ui.intent.textContent = cell.intent;
  renderStars();
  renderOthers(cell);
  ui.flaws.hidden = badge !== "";
  ui.tri.hidden = badge !== "";
  if (badge === "") {
    renderFlaws();
    renderTri();
  }
}

/**
 * @param {import("./grid.js").Tile} tile
 * @param {number} index the cell's place in the set
 */
function renderTile(tile, index) {
  const open = button("tile-open", "", () => {
    openLightbox(index);
  });
  open.ariaLabel = `View ${tile.cellId}`;
  const image = el("img", "");
  image.src = tile.thumb;
  image.alt = "";
  image.loading = "lazy";
  open.append(image);
  const isFavorite = state.favorite === tile.cellId;
  const lab = isLab(state.entry);
  const star = button("corner fav", isFavorite ? "★" : "☆", () => {
    state.favorite = toggled(state.favorite, tile.cellId);
    state.gridStatus = "idle";
    render();
  });
  star.ariaPressed = String(isFavorite);
  star.ariaLabel = `${isFavorite ? "Unmark" : "Mark"} ${tile.cellId} as favorite`;
  const download = el("a", "corner dl", "↓");
  download.href = tile.image;
  download.download = tile.download;
  download.ariaLabel = `Download ${tile.cellId}`;
  const frame = el("div", "tile-frame");
  frame.append(open, ...(lab ? [] : [star]), download);
  const stars = el("span", "tile-stars");
  stars.append(
    el("span", "on", "★".repeat(tile.stars)),
    "☆".repeat(5 - tile.stars),
  );
  const meta = el("div", "tile-meta");
  meta.append(el("span", "tile-id mono", tile.cellId), stars);
  const card = el("div", "tile");
  card.append(frame, meta);
  if (tile.flaws.length > 0) {
    const badges = el("div", "badges");
    badges.append(...tile.flaws.map((f) => el("span", "badge", f)));
    card.append(badges);
  }
  return card;
}

function renderGrid() {
  const lab = isLab(state.entry);
  ui.gridTitle.textContent = lab ? state.entry : `${state.entry} · favorite`;
  ui.favText.hidden = lab;
  ui.favText.textContent = `★ ${state.favorite ?? "none"}`;
  const grid = el("div", "tiles");
  grid.append(...tiles(state.cells).map(renderTile));
  ui.tiles.replaceChildren(grid);
}

/** @param {number} index */
function openLightbox(index) {
  state.lightbox = index;
  render();
}

/** The cell the lightbox shows; null when it is closed. */
function shownCell() {
  return state.lightbox === null ? null : (state.cells[state.lightbox] ?? null);
}

function closeLightbox() {
  state.lightbox = null;
  render();
}

/** @param {number} delta */
function stepLightbox(delta) {
  if (state.lightbox === null) return;
  state.lightbox = stepIndex(state.lightbox, delta, state.cells.length);
  render();
}

function renderLightbox() {
  const cell = shownCell();
  ui.lightbox.hidden = cell === null;
  if (cell === null || state.lightbox === null) return;
  ui.lbTitle.textContent = `${state.entry} · ${cell.cell_id}`;
  ui.lbPrev.disabled = state.lightbox === 0;
  ui.lbNext.disabled = state.lightbox === state.cells.length - 1;
  const single = el("div", "lb-single");
  const image = el("img", "");
  image.src = cell.image;
  image.alt = `Image ${state.entry} ${cell.cell_id}`;
  image.draggable = false;
  single.append(image);
  ui.lbStage.replaceChildren(single);
}

function rateShown() {
  const index = state.lightbox;
  if (index === null) return;
  state.lightbox = null;
  if (state.view === "rate" && index === state.cur) render();
  else openCell(index, state.view === "grid" || state.returnToGrid);
}

function renderPicker() {
  const entry = summary();
  ui.pickerId.textContent = state.entry;
  ui.pickerSub.textContent = entry === null ? "" : `· ${entryStatus(entry)}`;
  ui.picker.ariaExpanded = String(state.pickerOpen);
  ui.pickerList.hidden = !state.pickerOpen;
  if (!state.pickerOpen) return;
  const kinds = el("div", "seg picker-kinds");
  kinds.role = "radiogroup";
  kinds.ariaLabel = "Kind";
  kinds.append(
    ...PICKER_KINDS.map((kind) => {
      const choice = button(
        "seg-btn mono",
        kind === "all" ? "All" : kind,
        () => {
          state.pickerKind = kind;
          render();
        },
      );
      choice.role = "radio";
      choice.ariaChecked = String(state.pickerKind === kind);
      return choice;
    }),
  );
  const shown = state.entries.filter(
    (e) => state.pickerKind === "all" || e.kind === state.pickerKind,
  );
  ui.pickerList.replaceChildren(
    kinds,
    ...shown.map((e) => {
      const item = button("picker-item", "", () => void openEntry(e.entry));
      item.role = "option";
      item.ariaSelected = String(e.entry === state.entry);
      item.append(
        el("span", "mono", e.entry),
        el("span", "picker-sub", entryStatus(e)),
      );
      return item;
    }),
  );
}

function renderProgress() {
  const queued = summary()?.cells ?? 0;
  ui.progress.textContent =
    state.cells.length > 0
      ? ratedText(state.cells)
      : `0 / ${String(queued)} rendered`;
  if (state.cells.length === 0) {
    ui.segments.replaceChildren(
      ...Array.from({ length: queued }, () => {
        const slot = el("div", "segment-slot");
        slot.append(el("div", "segment"));
        return slot;
      }),
    );
    return;
  }
  const fromGrid = state.view === "grid" || state.returnToGrid;
  ui.segments.replaceChildren(
    ...segmentSlots(stepping(state.view === "rate" ? state.cur : -1), (at) => {
      openCell(at, fromGrid);
    }),
  );
}

/** @param {number} cur */
function stepping(cur) {
  return {
    entry: state.entry,
    cells: state.cells,
    cur,
    scope: state.scope,
    drafts: state.drafts,
  };
}

function renderStep() {
  renderStepRow(
    {
      prev: ui.stepPrev,
      next: ui.stepNext,
      pos: ui.stepPos,
      drafts: ui.stepDrafts,
      scope: ui.stepScope,
    },
    stepping(state.cur),
    (scope) => {
      state.scope = scope;
      render();
    },
  );
}

/** @returns {import("./shell.js").ActionsModel} */
function actionsModel() {
  const last = state.history.at(-1);
  /** @type {import("./shell.js").ActionLine[]} */
  const items = [
    {
      label: last === undefined ? "Undo" : `Undo ${last.cell}`,
      hint: "↶",
      disabled: last === undefined,
      onClick: () => void undo(),
    },
  ];
  if (currentCell() !== null)
    items.push({
      label: state.promptOpen ? "Hide prompt" : "Show prompt",
      onClick: () => {
        state.promptOpen = !state.promptOpen;
        render();
      },
    });
  if (state.view !== "loading")
    items.push("divider", {
      label: state.deleteFailed
        ? `Retry delete ${state.entry}`
        : `Delete ${state.entry}…`,
      danger: true,
      onClick: () => void deleteSet(),
    });
  return { general: [], items };
}

const shell = mountShell({
  nav: ui.nav,
  actions: ui.actions,
  page: "Curate",
  model: actionsModel,
  onRaterChange: () => void onRaterChanged(),
  onRatersLoaded: () => {
    render();
  },
});

/**
 * Reload with the new rater's own ratings; a cross-rater undo or unsaved draft would only
 * confuse, so both are dropped.
 */
async function onRaterChanged() {
  state.history = [];
  state.drafts = {};
  const entry = state.entry;
  if (entry === "") {
    await refresh();
    return;
  }
  await openEntry(entry);
  state.drafts = {};
  render();
}

function renderHeader() {
  renderPicker();
  renderProgress();
  shell.render();
  const cell = currentCell();
  ui.prompt.hidden = cell === null || !state.promptOpen;
  if (cell === null) return;
  ui.promptText.textContent = cell.prompt;
  ui.negativeText.textContent = cell.negative;
  ui.settings.replaceChildren(
    ...cell.settings.map(([key, value]) => {
      const row = document.createElement("div");
      row.append(el("dt", "", key), el("dd", "", value));
      return row;
    }),
  );
}

function renderEmpty() {
  const queued = summary()?.cells ?? 0;
  ui.emptyText.textContent = `${String(queued)} cells queued.`;
  const next = state.entries.find(
    (e) => e.entry !== state.entry && e.unrated > 0,
  );
  ui.emptyGo.hidden = next === undefined;
  ui.emptyGo.textContent = next === undefined ? "" : `Go to ${next.entry}`;
  ui.emptyGo.onclick =
    next === undefined ? null : () => void openEntry(next.entry);
}

function render() {
  renderHeader();
  const cell = currentCell();
  ui.rate.hidden = cell === null;
  ui.grid.hidden = state.view !== "grid";
  ui.empty.hidden = state.view !== "empty";
  if (cell !== null) renderRate(cell);
  if (state.view === "grid") renderGrid();
  if (state.view === "empty") renderEmpty();
  renderLightbox();
  renderSubmit(ui, floatingButton(cell));
  ui.dock.hidden = ui.submit.hidden;
  ui.dockPrev.hidden = cell === null;
  ui.dockNext.hidden = cell === null;
  ui.dockPrev.disabled = ui.stepPrev.disabled;
  ui.dockNext.disabled = ui.stepNext.disabled;
}

/**
 * @param {CellView | null} cell
 * @returns {Button | null}
 */
function floatingButton(cell) {
  if (cell !== null)
    return submitButton({
      cellId: cell.cell_id,
      rerate: isRated(cell),
      status: state.status,
      liked: state.draft.taste !== null,
      rater: rater(),
    });
  if (state.view !== "grid" || isLab(state.entry)) return null;
  return favoriteButton({
    status: state.gridStatus,
    favorite: state.favorite !== null,
    next: nextEntry(state.entries, state.entry) !== null,
    rater: rater(),
  });
}

function wire() {
  ui.picker.addEventListener("click", (event) => {
    event.stopPropagation();
    state.pickerOpen = !state.pickerOpen;
    render();
  });
  document.addEventListener("click", (event) => {
    if (
      !state.pickerOpen ||
      ui.pickerList.contains(/** @type {Node} */ (event.target))
    )
      return;
    state.pickerOpen = false;
    render();
  });
  ui.promptClose.addEventListener("click", () => {
    state.promptOpen = false;
    render();
  });
  ui.why.addEventListener("input", () => {
    state.draft = { ...state.draft, reason: ui.why.value };
    grow();
  });
  ui.back.addEventListener("click", openGrid);
  ui.lbClose.addEventListener("click", closeLightbox);
  ui.lbPrev.addEventListener("click", () => {
    stepLightbox(-1);
  });
  ui.lbNext.addEventListener("click", () => {
    stepLightbox(1);
  });
  ui.lbRate.addEventListener("click", rateShown);
  ui.stepPrev.addEventListener("click", () => {
    stepCell(-1);
  });
  ui.stepNext.addEventListener("click", () => {
    stepCell(1);
  });
  ui.dockPrev.addEventListener("click", () => {
    stepCell(-1);
  });
  ui.dockNext.addEventListener("click", () => {
    stepCell(1);
  });
  ui.zoom.addEventListener("click", () => {
    openLightbox(state.cur);
  });
  wireSwipe(ui.frame, stepCell);
  PHONE.addEventListener("change", render);
  document.addEventListener("keydown", (event) => {
    if (state.lightbox === null) {
      if (state.view !== "rate" || typing(event.target)) return;
      if (event.key === "ArrowLeft") stepCell(-1);
      else if (event.key === "ArrowRight") stepCell(1);
      return;
    }
    if (event.key === "Escape") closeLightbox();
    else if (event.key === "ArrowLeft") stepLightbox(-1);
    else if (event.key === "ArrowRight") stepLightbox(1);
  });
  wireSwipe(ui.lbStage, stepLightbox);
  ui.submit.addEventListener("click", () => {
    if (state.view === "grid") onGridButton();
    else void submit();
  });
}

async function start() {
  wire();
  await loadEntries();
  const asked = decodeURIComponent(location.hash.slice(1));
  const first =
    state.entries.find((e) => e.entry === asked) ??
    state.entries.find((e) => e.unrated > 0) ??
    state.entries[0];
  watchChanges(refresh);
  if (first === undefined) {
    render();
    return;
  }
  await openEntry(first.entry);
}

void start();

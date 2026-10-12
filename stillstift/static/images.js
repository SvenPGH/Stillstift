import { api, button, byId, el, fillSelect, pills } from "./dom.js";
import {
  DEFAULTS,
  filtersFor,
  groupsOf,
  isFiltered,
  setChoices,
  shownCells,
  totalText,
  verdictLabel,
  viewerRows,
} from "./images-view.js";
import { stepIndex } from "./grid.js";
import { watchChanges } from "./live.js";
import { FLAWS } from "./rating.js";
import { overviewSection, tileStars } from "./overview.js";
import { mountShell } from "./shell.js";
import { renderViewer, viewerUi, wireViewer } from "./viewer.js";

/** @typedef {import("./images-view.js").CellRow} CellRow */
/** @typedef {import("./images-view.js").Filters} Filters */
/** @typedef {import("./rating.js").EntrySummary} EntrySummary */

/** @type {readonly (readonly [Filters["kind"], string])[]} */
const KINDS = [
  ["P", "Page sets"],
  ["X", "Experiments"],
  ["T", "Tests"],
  ["all", "All"],
];
/** @type {readonly (readonly [Filters["book"], string])[]} */
const BOOKS = [
  ["all", "Any book"],
  ["yes", "Book: yes"],
  ["candidate", "Book: candidate"],
];
/** @type {readonly (readonly [Filters["verdict"], string])[]} */
const VERDICTS = [
  ["all", "All"],
  ["fav", "fav"],
  ["keep", "keep"],
  ["issue", "issue"],
  ["kill", "kill"],
  ["unrated", "unrated"],
];
/** @type {readonly (readonly [Filters["sort"], string])[]} */
const SORTS = [
  ["newest", "Newest set first"],
  ["liked_desc", "Liked, high to low"],
  ["liked_asc", "Liked, low to high"],
  ["render_desc", "Render, high to low"],
];
/** @type {readonly (readonly [boolean, string])[]} */
const LAYOUTS = [
  [true, "By set"],
  [false, "Flat"],
];

const ui = {
  nav: byId("nav", HTMLElement),
  actions: byId("actions", HTMLElement),
  total: byId("total", HTMLElement),
  kind: byId("kind", HTMLElement),
  set: byId("set", HTMLSelectElement),
  book: byId("book", HTMLSelectElement),
  verdict: byId("verdict", HTMLElement),
  flaw: byId("flaw", HTMLSelectElement),
  sort: byId("sort", HTMLSelectElement),
  layout: byId("layout", HTMLElement),
  shown: byId("shown", HTMLElement),
  clear: byId("clear", HTMLButtonElement),
  groups: byId("groups", HTMLElement),
  noResults: byId("no-results", HTMLElement),
  rate: byId("viewer-rate", HTMLAnchorElement),
  prev: byId("viewer-prev", HTMLButtonElement),
  next: byId("viewer-next", HTMLButtonElement),
  sub: byId("viewer-sub", HTMLElement),
  pos: byId("viewer-pos", HTMLElement),
};
const viewer = viewerUi();

const state = {
  /** @type {EntrySummary[]} */
  entries: [],
  /** @type {CellRow[]} */
  cells: [],
  filters: DEFAULTS,
  /** @type {CellRow | null} */
  viewing: null,
};

/** @param {CellRow} cell */
function keyOf(cell) {
  return `${cell.entry}:${cell.cell_id}`;
}

/** @param {Partial<Filters>} change */
function filter(change) {
  state.filters = { ...state.filters, ...change };
  render();
}

function renderFilters() {
  const f = state.filters;
  pills(ui.kind, KINDS, f.kind, (kind) => {
    filter({ kind, set: "all" });
  });
  fillSelect(ui.set, setChoices(state.entries, f.kind), f.set);
  fillSelect(ui.book, BOOKS, f.book);
  pills(ui.verdict, VERDICTS, f.verdict, (verdict) => {
    filter({ verdict });
  });
  const flaws = FLAWS.map((name) => /** @type {const} */ ([name, name]));
  fillSelect(
    ui.flaw,
    [["any", "Any flaws"], ["none", "No flaws"], ...flaws],
    f.flaw,
  );
  fillSelect(ui.sort, SORTS, f.sort);
  pills(ui.layout, LAYOUTS, f.grouped, (grouped) => {
    filter({ grouped });
  });
  ui.clear.hidden = !isFiltered(f);
}

/**
 * @param {CellRow} cell
 * @param {boolean} grouped whether the tile sits under its set's heading
 */
function tile(cell, grouped) {
  const open = button("tile-open", "", () => {
    state.viewing = cell;
    render();
  });
  open.ariaLabel = `View ${cell.entry} ${cell.cell_id}`;
  const image = el("img", "");
  image.src = cell.thumb;
  image.alt = "";
  image.loading = "lazy";
  open.append(image);
  const download = el("a", "corner dl", "↓");
  download.href = cell.image;
  download.download = cell.download;
  download.ariaLabel = `Download ${cell.entry}-${cell.cell_id}`;
  const frame = el("div", "tile-frame");
  frame.append(open, download);
  if (cell.favorite) frame.append(el("span", "corner fav shown", "★"));
  const { text, tone } = verdictLabel(cell);
  const meta = el("div", "tile-meta");
  meta.append(
    el(
      "span",
      "tile-id mono",
      grouped ? cell.cell_id : `${cell.entry} · ${cell.cell_id}`,
    ),
    tileStars(cell.rating?.taste ?? null),
    el("span", `tile-verdict mono ${tone}`, text),
  );
  const card = el("div", "tile");
  card.append(frame, meta);
  const flaws = cell.rating?.flaws ?? [];
  if (flaws.length > 0) {
    const badges = el("div", "badges");
    badges.append(...flaws.map((f) => el("span", "badge", f)));
    card.append(badges);
  }
  return card;
}

/** @param {CellRow[]} shown */
function renderGroups(shown) {
  const groups = groupsOf(shown, state.cells, state.entries, state.filters);
  ui.noResults.hidden = groups.length > 0;
  ui.groups.replaceChildren(
    ...groups.map((group) =>
      overviewSection(
        group,
        group.cells.map((c) => tile(c, group.entry !== "")),
      ),
    ),
  );
}

/** @param {CellRow[]} shown */
function renderOpen(shown) {
  const cell = state.viewing;
  renderViewer(
    viewer,
    cell === null
      ? null
      : {
          ref: `${cell.entry} · ${cell.cell_id}`,
          image: cell.image,
          taste: cell.rating?.taste ?? null,
          favorite: cell.favorite,
          rows: viewerRows(cell),
          flaws: cell.rating?.flaws ?? [],
          reason: cell.rating?.reason ?? "",
        },
  );
  if (cell === null) return;
  const at = shown.indexOf(cell);
  const name = state.entries.find((e) => e.entry === cell.entry)?.name ?? "";
  ui.sub.textContent = name;
  ui.rate.href = `/#${encodeURIComponent(cell.entry)}`;
  ui.prev.disabled = at <= 0;
  ui.next.disabled = at < 0 || at >= shown.length - 1;
  ui.pos.textContent =
    at < 0 ? "" : `${String(at + 1)} of ${String(shown.length)} · ← → to step`;
}

/** @param {-1 | 1} delta */
function stepViewer(delta) {
  const shown = shownCells(state.cells, state.filters);
  const at = state.viewing === null ? -1 : shown.indexOf(state.viewing);
  if (at < 0) return;
  state.viewing = shown[stepIndex(at, delta, shown.length)] ?? state.viewing;
  render();
}

const shell = mountShell({
  nav: ui.nav,
  actions: ui.actions,
  page: "Images",
  model: () => ({
    general: [],
    items: [
      {
        label: "Clear filters",
        disabled: !isFiltered(state.filters),
        onClick: () => {
          filter({ ...DEFAULTS, grouped: state.filters.grouped });
        },
      },
    ],
  }),
});

function render() {
  const shown = shownCells(state.cells, state.filters);
  ui.total.textContent = totalText(state.cells);
  ui.shown.textContent = `${String(shown.length)} of ${String(state.cells.length)}`;
  renderFilters();
  renderGroups(shown);
  shell.render();
  renderOpen(shown);
}

function wire() {
  ui.set.addEventListener("change", () => {
    filter({ set: ui.set.value });
  });
  ui.book.addEventListener("change", () => {
    const book = BOOKS.find(([value]) => value === ui.book.value)?.[0];
    if (book !== undefined) filter({ book });
  });
  ui.flaw.addEventListener("change", () => {
    filter({ flaw: ui.flaw.value });
  });
  ui.sort.addEventListener("change", () => {
    const sort = SORTS.find(([value]) => value === ui.sort.value)?.[0];
    if (sort !== undefined) filter({ sort });
  });
  ui.clear.addEventListener("click", () => {
    filter({ ...DEFAULTS, grouped: state.filters.grouped });
  });
  ui.prev.addEventListener("click", () => {
    stepViewer(-1);
  });

  ui.next.addEventListener("click", () => {
    stepViewer(1);
  });
  const close = () => {
    state.viewing = null;
    render();
  };
  wireViewer(viewer, { close });

  document.addEventListener("keydown", (event) => {
    if (state.viewing === null) return;
    if (event.key === "Escape") close();
    else if (event.key === "ArrowLeft") stepViewer(-1);
    else if (event.key === "ArrowRight") stepViewer(1);
  });
}

/** Read the sets and pages, keeping the page open in the viewer. */
async function load() {
  const [entries, cells] = await Promise.all([
    api("/api/entries"),
    api("/api/cells"),
  ]);
  state.entries = /** @type {EntrySummary[]} */ (entries);
  state.cells = /** @type {CellRow[]} */ (cells);
  const open = state.viewing;
  state.viewing =
    open === null
      ? null
      : (state.cells.find((c) => keyOf(c) === keyOf(open)) ?? null);
}

async function start() {
  wire();

  await load();
  state.filters = filtersFor(
    decodeURIComponent(location.hash.slice(1)),
    state.entries,
  );
  render();
  watchChanges(async () => {
    await load();
    render();
  });
}

void start();

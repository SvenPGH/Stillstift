import { api, button, byId, el, json } from "./dom.js";
import {
  KIND_LABEL,
  LAB_PAGES,
  canCreate,
  cardStats,
  contextLine,
  createForm,
  curateLink,
  emptyLine,
  imagesHref,
  kindForPath,
  labSets,
  shortDate,
  shownLine,
  shownSets,
  thumbCells,
} from "./lab-view.js";
import { watchChanges } from "./live.js";
import { mountShell } from "./shell.js";

/** @typedef {import("./rating.js").EntrySummary} EntrySummary */
/** @typedef {import("./lab-view.js").LabCell} LabCell */
/** @typedef {import("./lab-view.js").LabSet} LabSet */
/** @typedef {import("./lab-view.js").StatusFilter} StatusFilter */
/** @typedef {import("./lab-view.js").CreateStatus} CreateStatus */

const KIND = kindForPath(location.pathname);
const PAGE = LAB_PAGES[KIND];
/** @type {readonly (readonly [StatusFilter, string])[]} */
const STATUS_FILTERS = [
  ["all", "All"],
  ["torate", "To rate"],
  ["done", "Done"],
];

const ui = {
  nav: byId("nav", HTMLElement),
  actions: byId("actions", HTMLElement),
  context: byId("context", HTMLElement),
  statusFilter: byId("status-filter", HTMLElement),
  shown: byId("shown", HTMLElement),
  newSet: byId("new-set", HTMLButtonElement),
  intro: byId("intro", HTMLElement),
  create: byId("create", HTMLFormElement),
  createId: byId("create-id", HTMLElement),
  createTitle: byId("create-title", HTMLElement),
  createName: byId("create-name", HTMLInputElement),
  createTests: byId("create-tests", HTMLTextAreaElement),
  createError: byId("create-error", HTMLElement),
  createCancel: byId("create-cancel", HTMLButtonElement),
  createSubmit: byId("create-submit", HTMLButtonElement),
  cards: byId("cards", HTMLElement),
  noResults: byId("no-results", HTMLElement),
};

const state = {
  /** @type {EntrySummary[]} */
  entries: [],
  /** @type {LabCell[]} */
  cells: [],
  /** @type {string | null} */
  fresh: null,
  /** @type {StatusFilter} */
  status: "all",
  creating: false,
  /** @type {CreateStatus} */
  saving: "idle",
};

/**
 * @template {string} V
 * @param {HTMLElement} host
 * @param {readonly (readonly [V, string])[]} choices
 * @param {V} current
 * @param {(value: V) => void} pick
 */
function renderPills(host, choices, current, pick) {
  host.replaceChildren(
    ...choices.map(([value, label]) => {
      const pill = button("pill-opt", label, () => {
        pick(value);
      });
      pill.role = "radio";
      pill.ariaChecked = String(current === value);
      return pill;
    }),
  );
}

/**
 * @param {LabSet} set
 * @param {LabCell} cell
 */
function thumb(set, cell) {
  const link = el("a", "thumb");

  link.href = imagesHref(set.entry);
  link.ariaLabel = `${set.entry} ${cell.cell_id}`;
  const image = el("img", "");
  image.src = cell.thumb;
  image.alt = "";
  image.loading = "lazy";
  link.append(image);
  return link;
}

/** @param {LabSet} set */
function rendered(set) {
  const strip = el("div", "stats");
  strip.append(
    ...cardStats(set).map(({ value, label, tone }) => {
      const box = el("div", "stat");
      box.append(
        el("div", `stat-value mono ${tone}`, value),
        el("div", "stat-label", label),
      );
      return box;
    }),
  );
  const thumbs = el("div", "thumbs");
  thumbs.append(...thumbCells(set).map((c) => thumb(set, c)));
  return [strip, thumbs];
}

/** @param {LabSet} set */
function card(set) {
  const top = el("div", "lab-top");
  top.append(
    el("span", "lab-id mono", set.entry),
    el(
      "span",
      `idea${set.kind === "T" ? " lab-test" : ""}`,
      KIND_LABEL[set.kind],
    ),
    el("span", "lab-date mono", shortDate(set.date)),
  );
  const head = el("div", "lab-head");
  head.append(
    top,
    el("div", "set-card-name", set.name),
    el("div", "set-card-what", set.tests || "—"),
  );
  const curate = curateLink(set);
  const go = el("a", "lab-curate", curate.label);
  go.href = curate.href;
  const images = el("a", "ghost lab-images", "Images");
  images.href = imagesHref(set.entry);
  const links = el("div", "lab-links");
  links.append(go, images);
  const article = el("article", "set-card");
  article.append(
    head,
    ...(set.cells.length === 0
      ? [el("p", "lab-empty", "Nothing rendered yet.")]
      : rendered(set)),
    links,
  );
  return article;
}

function renderForm() {
  ui.create.hidden = !state.creating;
  if (!state.creating) return;
  const form = createForm(state.entries, KIND, state.saving);
  ui.createId.textContent = form.id;
  ui.createTitle.textContent = form.title;
  ui.createSubmit.textContent = form.submit;
  ui.createSubmit.disabled = !canCreate(ui.createName.value, state.saving);
  ui.createCancel.disabled = state.saving === "saving";
  ui.createError.textContent = form.error;
  ui.createError.hidden = form.error === "";
}

const shell = mountShell({
  nav: ui.nav,
  actions: ui.actions,
  page: PAGE.page,
  model: () => ({
    general: [],

    items: [{ label: `New ${PAGE.noun}`, hint: KIND, onClick: openForm }],
  }),
});

function render() {
  const sets = labSets(state.entries, state.cells, KIND, state.fresh);
  const shown = shownSets(sets, state.status);
  ui.context.textContent = contextLine(sets, KIND);
  renderPills(ui.statusFilter, STATUS_FILTERS, state.status, (status) => {
    state.status = status;
    render();
  });
  ui.shown.textContent = shownLine(shown.length, sets.length);
  ui.cards.replaceChildren(...shown.map(card));
  ui.noResults.hidden = shown.length > 0;
  ui.noResults.textContent = emptyLine(sets.length, KIND);
  renderForm();
  shell.render();
}

function openForm() {
  if (state.saving === "saving") return;
  state.creating = true;
  state.saving = "idle";
  render();
  ui.createName.focus();
}

function closeForm() {
  state.creating = false;
  state.saving = "idle";
  ui.createName.value = "";
  ui.createTests.value = "";
  render();
}

async function load() {
  const [entries, cells] = await Promise.all([
    api("/api/entries"),
    api("/api/cells"),
  ]);
  state.entries = /** @type {EntrySummary[]} */ (entries);
  state.cells = /** @type {LabCell[]} */ (cells);
}

async function create() {
  if (!state.creating || !canCreate(ui.createName.value, state.saving)) return;
  state.saving = "saving";
  renderForm();
  const body = {
    kind: KIND,
    name: ui.createName.value.trim(),
    tests: ui.createTests.value.trim(),
  };
  try {
    const made = /** @type {{ entry: string }} */ (
      await api("/api/sets", { method: "POST", ...json(body) })
    );
    state.fresh = made.entry;
  } catch {
    state.saving = "failed";
    renderForm();
    return;
  }
  state.status = "all";
  try {
    await load();
  } finally {
    closeForm();
  }
}

function wire() {
  ui.newSet.addEventListener("click", openForm);
  ui.createName.addEventListener("input", renderForm);
  ui.createCancel.addEventListener("click", closeForm);
  ui.create.addEventListener("submit", (event) => {
    event.preventDefault();
    void create();
  });
}

async function start() {
  document.title = `Stillstift · ${PAGE.page}`;
  ui.newSet.textContent = `+ New ${PAGE.noun}`;
  ui.intro.textContent = PAGE.intro;
  ui.createTests.placeholder = PAGE.field;
  ui.createTests.ariaLabel = PAGE.field;
  wire();
  await load();
  render();
  watchChanges(async () => {
    await load();
    render();
  });
}

void start();

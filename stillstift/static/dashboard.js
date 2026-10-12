import { api, byId, el } from "./dom.js";
import { dashboard } from "./dashboard-view.js";
import { watchChanges } from "./live.js";
import { mountShell } from "./shell.js";

/** @typedef {import("./dashboard-view.js").Bar} Bar */
/** @typedef {import("./dashboard-view.js").Calibration} Calibration */
/** @typedef {import("./dashboard-view.js").CalCell} CalCell */
/** @typedef {import("./dashboard-view.js").SetMatch} SetMatch */
/** @typedef {import("./dashboard-view.js").CellRow} CellRow */
/** @typedef {import("./dashboard-view.js").SetRow} SetRow */
/** @typedef {import("./dashboard-view.js").Stat} Stat */
/** @typedef {import("./dashboard-view.js").VerdictCount} VerdictCount */
/** @typedef {import("./rating.js").EntrySummary} EntrySummary */
/** @typedef {"liked" | "flaw" | "row"} BarKind */

const SET_COLUMNS = [
  "Set",
  "Name",
  "Date",
  "Images",
  "Rated",
  "Avg Liked",
  "Top flaw",
  "",
];

const VERDICT_NAMES = ["fav", "keep", "issue", "kill"];
const DEEP = 0.6;

const ui = {
  nav: byId("nav", HTMLElement),
  actions: byId("actions", HTMLElement),
  context: byId("context", HTMLElement),
  stats: byId("stats", HTMLElement),
  liked: byId("liked", HTMLElement),
  verdictBar: byId("verdict-bar", HTMLElement),
  verdicts: byId("verdicts", HTMLElement),
  flaws: byId("flaws", HTMLElement),
  predictions: byId("predictions", HTMLElement),
  calibration: byId("calibration", HTMLTableElement),
  misses: byId("misses", HTMLOListElement),
  match: byId("match", HTMLElement),
  matchAxis: byId("match-axis", HTMLElement),
  averages: byId("averages", HTMLElement),
  setMeta: byId("set-meta", HTMLElement),
  sets: byId("sets", HTMLElement),
};

const state = {
  /** @type {EntrySummary[]} */
  entries: [],
  /** @type {CellRow[]} */
  cells: [],
  withLab: false,
};

/**
 * A figure with its label and sub-line: a stat card or a prediction column.
 * @param {string} className
 * @param {Stat} stat
 */
function figure(className, stat) {
  const box = el("div", className);
  box.append(
    el("div", `dash-value mono${stat.amber ? " amber" : ""}`, stat.value),
    el("div", "dash-label", stat.label),
    el("div", "dash-sub mono", stat.sub),
  );
  return box;
}

/**
 * @param {Bar} bar
 * @param {BarKind} kind
 */
function barRow(bar, kind) {
  const row = el("div", `dash-bar ${kind}`);
  const track = el("div", "dash-track");
  const fill = el("div", "dash-fill");
  fill.style.width = `${String(bar.width)}%`;
  track.append(fill);
  row.append(
    el("span", "dash-bar-label", bar.label),
    track,
    el("span", "dash-figure mono", bar.figure),
  );
  return row;
}

/** @param {VerdictCount[]} verdicts */
function renderVerdicts(verdicts) {
  ui.verdictBar.replaceChildren(
    ...verdicts
      .filter((v) => v.count > 0)
      .map((v) => {
        const part = el("div", `verdict-part ${v.verdict}`);
        part.style.flexGrow = String(v.count);
        return part;
      }),
  );
  ui.verdicts.replaceChildren(
    ...verdicts.map((v) => {
      const name = el("div", "verdict-name");
      name.append(el("span", `verdict-part ${v.verdict}`), v.verdict);
      const column = el("div", "stat");
      column.append(
        name,
        el("div", "stat-value mono", String(v.count)),
        el("div", "stat-label mono", v.share),
      );
      return column;
    }),
  );
}

/** @param {Bar[]} flaws */
function renderFlaws(flaws) {
  ui.flaws.replaceChildren(...flaws.map((f) => barRow(f, "flaw")));
  if (flaws.length === 0)
    ui.flaws.append(el("p", "dash-none", "No flaws marked yet."));
}

/**
 * A header cell of the calibration grid.
 * @param {string} text
 * @param {"col" | "row"} scope
 */
function calHead(text, scope) {
  const th = el("th", `cal-head ${scope}`, text);
  th.scope = scope;
  return th;
}

/** @param {CalCell} cell */
function calCell(cell) {
  const td = el(
    "td",
    `cal-cell${cell.right ? " right" : ""}${cell.share >= DEEP ? " deep" : ""}`,
  );
  td.style.setProperty("--share", String(cell.share));
  td.title = cell.title;
  td.append(
    el("span", "cal-count mono", String(cell.count)),
    el("span", "cal-share mono", cell.label),
  );
  return td;
}

/** @param {Calibration} cal */
function renderCalibration(cal) {
  const head = el("tr", "");
  head.append(
    calHead("Said ↓", "col"),
    ...VERDICT_NAMES.map((v) => calHead(v, "col")),
    calHead("total", "col"),
  );
  const rows = cal.rows.map((row) => {
    const tr = el("tr", "");
    tr.append(
      calHead(row.predicted, "row"),
      ...row.cells.map(calCell),
      el("td", "cal-total mono", String(row.total)),
    );
    return tr;
  });
  const foot = el("tr", "");
  foot.append(
    calHead("total", "row"),
    ...cal.totals.map((t) => el("td", "cal-total mono", String(t))),
    el("td", "cal-total mono", String(cal.scored)),
  );
  const thead = el("thead", "");
  thead.append(head);
  const tbody = el("tbody", "");
  tbody.append(...rows);
  const tfoot = el("tfoot", "");
  tfoot.append(foot);
  ui.calibration.replaceChildren(thead, tbody, tfoot);
  ui.misses.replaceChildren(...cal.misses.map((m) => el("li", "", m.text)));
  if (cal.misses.length === 0)
    ui.misses.append(
      el(
        "li",
        "dash-none",
        cal.scored === 0 ? "No predicted cells rated yet." : "No wrong calls.",
      ),
    );
}

/** @param {SetMatch[]} trend */
function renderMatch(trend) {
  const last = trend.at(-1);
  ui.match.replaceChildren(
    ...trend.map((set) => {
      const column = el("div", "cal-col");
      column.style.setProperty("--share", String(set.share));
      column.title = set.title;
      column.append(el("div", "cal-bar"));
      if (set === last) column.append(el("span", "cal-latest mono", set.label));
      return column;
    }),
  );
  ui.match.hidden = trend.length === 0;
  const first = trend[0];
  ui.matchAxis.replaceChildren(
    ...(first === undefined || last === undefined
      ? [el("p", "dash-none", "No predicted sets rated yet.")]
      : [
          el("span", "", first.entry),
          el("span", "", trend.length === 1 ? "" : last.entry),
        ]),
  );
}

/**
 * @param {string} className
 * @param {string} text
 * @param {string} href
 */
function link(className, text, href) {
  const a = el("a", className, text);
  a.href = href;
  return a;
}

/** @param {SetRow} set */
function setRow(set) {
  const links = el("span", "set-links");
  links.append(
    link("set-link muted", "Images", set.imagesHref),
    link("set-link", "Curate →", set.cureHref),
  );
  const row = el("div", "set-row");
  row.role = "row";
  row.append(
    el("span", "set-id mono", set.entry),
    el("span", "set-name", set.name),
    el("span", "set-date mono", set.date),
    el("span", "set-num mono", String(set.images)),
    el("span", `set-num mono ${set.complete ? "done" : "amber"}`, set.rated),
    el("span", "set-num mono amber", set.avg),
    el("span", "set-flaw", set.topFlaw),
    links,
  );
  for (const cell of row.children) cell.role = "cell";
  return row;
}

/** @param {SetRow[]} sets */
function renderSets(sets) {
  const head = el("div", "set-row head");
  head.role = "row";
  head.append(
    ...SET_COLUMNS.map((name) => {
      const column = el("span", "", name);
      column.role = "columnheader";
      return column;
    }),
  );
  ui.sets.replaceChildren(head, ...sets.map(setRow));
}

const shell = mountShell({
  nav: ui.nav,
  actions: ui.actions,
  page: "Dashboard",
  model: () => ({
    general: [],
    items: [
      {
        label: state.withLab ? "Leave out experiments" : "Include experiments",
        onClick: () => {
          state.withLab = !state.withLab;
          render();
        },
      },
    ],
  }),
});

function render() {
  const view = dashboard(state.entries, state.cells, state.withLab);
  ui.context.textContent = view.context;
  ui.stats.replaceChildren(...view.stats.map((s) => figure("dash-stat", s)));
  ui.liked.replaceChildren(...view.liked.map((b) => barRow(b, "liked")));
  renderVerdicts(view.verdicts);
  renderFlaws(view.flaws);
  ui.predictions.replaceChildren(
    ...view.predictions.map((p) => figure("dash-pred", p)),
  );
  renderCalibration(view.calibration);
  renderMatch(view.calibration.trend);
  ui.averages.replaceChildren(...view.averages.map((b) => barRow(b, "row")));
  ui.setMeta.textContent = view.setMeta;
  renderSets(view.sets);
  shell.render();
}

async function load() {
  const [entries, cells] = await Promise.all([
    api("/api/entries"),
    api("/api/cells"),
  ]);
  state.entries = /** @type {EntrySummary[]} */ (entries);
  state.cells = /** @type {CellRow[]} */ (cells);
  render();
}

async function start() {
  await load();
  watchChanges(load);
}

void start();

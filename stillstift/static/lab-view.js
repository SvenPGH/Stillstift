/** @typedef {import("./rating.js").EntrySummary} EntrySummary */
/** @typedef {import("./nav.js").PageName} PageName */
/** @typedef {"X" | "T"} LabKind */
/** @typedef {{ taste: number, render: number | null }} LabRating */
/**
 * @typedef {{
 *   entry: string,
 *   cell_id: string,
 *   image: string,
 *   thumb: string,
 *   rating: LabRating | null,
 * }} LabCell
 */
/**
 * @typedef {{
 *   entry: string,
 *   kind: LabKind,
 *   name: string,
 *   date: string,
 *   tests: string,
 *   cells: LabCell[],
 * }} LabSet
 */
/** @typedef {"all" | "torate" | "done"} StatusFilter */
/** @typedef {{ value: string, label: string, tone: "text" | "amber" }} Stat */
/** @typedef {"idle" | "saving" | "failed"} CreateStatus */
/** @typedef {{ id: string, title: string, submit: string, error: string }} CreateForm */
/**
 * One lab page: its menu name, what one set is called, the page's intro and the create form's
 * second field.
 * @typedef {{ page: PageName, path: string, noun: string, intro: string, field: string }} LabPage
 */

const THUMBS = 8;
const MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
const ISO_DATE = /^[0-9]{4}-([0-9]{2})-([0-9]{2})$/;
/** @type {Record<LabKind, string>} */
export const KIND_LABEL = { X: "Experiment", T: "Test" };
const KEPT_OUT =
  "They never feed Dashboard stats, the taste model or prediction recall, and stay out of " +
  "Images unless you filter them in.";
/** @type {Record<LabKind, LabPage>} */
export const LAB_PAGES = {
  X: {
    page: "Experiments",
    path: "/experiments",
    noun: "experiment",
    intro: `An experiment tries an idea. X sets have their own numbering and are rated on Liked, Render and a why. ${KEPT_OUT}`,
    field: "What it tests",
  },
  T: {
    page: "Tests",
    path: "/tests",
    noun: "test",
    intro: `A test checks one craft question. T sets have their own numbering and are rated on Liked, Render and a why. ${KEPT_OUT}`,
    field: "What it tests",
  },
};

/**
 * The kind a lab page lists, from its path; an unknown path lists experiments.
 * @param {string} path
 * @returns {LabKind}
 */
export function kindForPath(path) {
  const kinds = /** @type {LabKind[]} */ (Object.keys(LAB_PAGES));
  return kinds.find((k) => LAB_PAGES[k].path === path) ?? "X";
}

/**
 * @param {string} entry
 * @returns {number}
 */
function numberOf(entry) {
  return Number(/[0-9]+/.exec(entry)?.[0] ?? 0);
}

/**
 * @param {LabSet} a
 * @param {LabSet} b
 * @returns {number}
 */
function newerFirst(a, b) {
  if (a.date !== b.date) return a.date < b.date ? 1 : -1;
  return numberOf(b.entry) - numberOf(a.entry);
}

/**
 * The page's sets of its kind with their rendered cells, newest first; `first` (the set just
 * created) leads.
 * @param {EntrySummary[]} entries
 * @param {LabCell[]} cells
 * @param {LabKind} kind
 * @param {string | null} first
 * @returns {LabSet[]}
 */
export function labSets(entries, cells, kind, first) {
  return entries
    .flatMap((e) =>
      e.kind === kind
        ? [
            {
              entry: e.entry,
              kind,
              name: e.name,
              date: e.date,
              tests: e.tests,
              cells: cells.filter((c) => c.entry === e.entry),
            },
          ]
        : [],
    )
    .sort(
      (a, b) =>
        Number(b.entry === first) - Number(a.entry === first) ||
        newerFirst(a, b),
    );
}

/**
 * The id the server gives the next set of the kind: the highest of that kind, plus one.
 * @param {EntrySummary[]} entries
 * @param {LabKind} kind
 * @returns {string}
 */
export function nextId(entries, kind) {
  const numbers = entries
    .filter((e) => e.kind === kind)
    .map((e) => numberOf(e.entry));
  return `${kind}${String(Math.max(0, ...numbers) + 1)}`;
}

/**
 * Done once something is rendered and every rendered cell is rated.
 * @param {LabSet} set
 * @returns {boolean}
 */
export function isDone(set) {
  return set.cells.length > 0 && set.cells.every((c) => c.rating !== null);
}

/**
 * The sets the status filter leaves; "To rate" keeps a set with nothing rendered.
 * @param {LabSet[]} sets
 * @param {StatusFilter} status
 * @returns {LabSet[]}
 */
export function shownSets(sets, status) {
  return sets.filter(
    (s) => status === "all" || (status === "done") === isDone(s),
  );
}

/**
 * @param {number} n
 * @param {string} noun
 * @returns {string}
 */
function counted(n, noun) {
  return `${String(n)} ${noun}${n === 1 ? "" : "s"}`;
}

/**
 * The header's context: how many sets of the page's kind there are.
 * @param {LabSet[]} sets
 * @param {LabKind} kind
 * @returns {string}
 */
export function contextLine(sets, kind) {
  return counted(sets.length, LAB_PAGES[kind].noun);
}

/**
 * @param {number} shown
 * @param {number} total
 * @returns {string}
 */
export function shownLine(shown, total) {
  return `${String(shown)} of ${String(total)}`;
}

/**
 * What the page says when no card is shown.
 * @param {number} total
 * @param {LabKind} kind
 * @returns {string}
 */
export function emptyLine(total, kind) {
  return total === 0
    ? `No ${LAB_PAGES[kind].noun}s yet.`
    : "Nothing matches that filter.";
}

/**
 * @param {number[]} values
 * @returns {string}
 */
function average(values) {
  if (values.length === 0) return "—";
  const sum = values.reduce((a, b) => a + b, 0);
  return `${(sum / values.length).toFixed(1)}★`;
}

/**
 * The card's strip: images, how many are rated (amber until all are), avg Liked and avg Render.
 * @param {LabSet} set
 * @returns {Stat[]}
 */
export function cardStats(set) {
  const total = set.cells.length;
  const rated = set.cells.flatMap((c) => (c.rating === null ? [] : [c.rating]));
  return [
    { value: String(total), label: "images", tone: "text" },
    {
      value: `${String(rated.length)} / ${String(total)}`,
      label: "rated",
      tone: rated.length < total ? "amber" : "text",
    },
    {
      value: average(rated.map((r) => r.taste)),
      label: "avg Liked",
      tone: "amber",
    },
    {
      value: average(
        rated.flatMap((r) => (r.render === null ? [] : [r.render])),
      ),
      label: "avg Render",
      tone: "amber",
    },
  ];
}

/**
 * @param {LabSet} set
 * @returns {LabCell[]}
 */
export function thumbCells(set) {
  return set.cells.slice(0, THUMBS);
}

/**
 * Where the card's main button goes: Curate on the set, as "Review" once it is done.
 * @param {LabSet} set
 * @returns {{ label: string, href: string }}
 */
export function curateLink(set) {
  return {
    label: isDone(set) ? "Review →" : "Curate →",
    href: `/#${encodeURIComponent(set.entry)}`,
  };
}

/**
 * @param {string} entry
 * @returns {string}
 */
export function imagesHref(entry) {
  return `/images#${encodeURIComponent(entry)}`;
}

/**
 * A set's day as the cards show it, "Oct 8"; any other text as it is.
 * @param {string} date
 * @returns {string}
 */
export function shortDate(date) {
  const found = ISO_DATE.exec(date);
  const month = MONTHS[Number(found?.[1]) - 1];
  if (found === null || month === undefined) return date;
  return `${month} ${String(Number(found[2]))}`;
}

/**
 * The create form's labels for the kind, from the id the next set of it will take.
 * @param {EntrySummary[]} entries
 * @param {LabKind} kind
 * @param {CreateStatus} status
 * @returns {CreateForm}
 */
export function createForm(entries, kind, status) {
  const id = nextId(entries, kind);
  return {
    id,
    title: `New ${LAB_PAGES[kind].noun}`,
    submit: status === "saving" ? "Creating…" : `Create ${id}`,
    error: status === "failed" ? `Couldn't create ${id}. Try again.` : "",
  };
}

/**
 * Whether Create is on: a name is typed and no create is in flight.
 * @param {string} name
 * @param {CreateStatus} status
 * @returns {boolean}
 */
export function canCreate(name, status) {
  return name.trim() !== "" && status !== "saving";
}

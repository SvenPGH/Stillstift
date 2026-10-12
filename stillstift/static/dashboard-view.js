import { isLab, kindOf } from "./kinds.js";
import { PARTS } from "./rating.js";

/** @typedef {import("./rating.js").EntrySummary} EntrySummary */
/** @typedef {"fav" | "keep" | "issue" | "kill"} Verdict */
/**
 * @typedef {{
 *   taste: number,
 *   rows: Record<string, number | null>,
 *   render: number | null,
 *   flaws: string[],
 *   flags?: { book?: "yes" | "candidate" | "no" | null },
 * }} CellRating
 */
/**
 * A rendered cell as `/api/cells` lists it, with what the dashboard reads of it.
 * @typedef {{
 *   entry: string,
 *   cell_id: string,
 *   rating: CellRating | null,
 *   verdict: Verdict | null,
 *   prediction: Verdict | null,
 *   favorite: boolean,
 * }} CellRow
 */
/** @typedef {{ value: string, label: string, sub: string, amber: boolean }} Stat */
/** @typedef {{ label: string, figure: string, width: number }} Bar */
/** @typedef {{ verdict: Verdict, count: number, share: string }} VerdictCount */
/**
 * @typedef {{
 *   entry: string,
 *   name: string,
 *   date: string,
 *   images: number,
 *   rated: string,
 *   complete: boolean,
 *   avg: string,
 *   topFlaw: string,
 *   imagesHref: string,
 *   cureHref: string,
 * }} SetRow
 */
/**
 * One cell of the calibration grid: how often a prediction met this verdict, and its share of
 * the prediction's row.
 * @typedef {{
 *   actual: Verdict,
 *   count: number,
 *   share: number,
 *   label: string,
 *   right: boolean,
 *   title: string,
 * }} CalCell
 */
/** @typedef {{ predicted: Verdict, cells: CalCell[], total: number }} CalRow */
/** @typedef {{ count: number, text: string }} Miss */
/** @typedef {{ entry: string, share: number, label: string, title: string }} SetMatch */
/**
 * @typedef {{
 *   rows: CalRow[],
 *   totals: number[],
 *   scored: number,
 *   misses: Miss[],
 *   trend: SetMatch[],
 * }} Calibration
 */
/**
 * @typedef {{
 *   context: string,
 *   stats: Stat[],
 *   liked: Bar[],
 *   verdicts: VerdictCount[],
 *   flaws: Bar[],
 *   predictions: Stat[],
 *   calibration: Calibration,
 *   averages: Bar[],
 *   setMeta: string,
 *   sets: SetRow[],
 * }} Dashboard
 */

/** @type {readonly Verdict[]} */
const VERDICTS = ["fav", "keep", "issue", "kill"];
const STARS = [5, 4, 3, 2, 1];
const MAX_STARS = 5;
const TOP_FLAWS = 6;
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
/** @typedef {(rating: CellRating) => number | null | undefined} ReadRow */
/** @type {readonly (readonly [string, ReadRow])[]} */
const AVERAGE_ROWS = [
  ...PARTS.map(([part, label]) => {
    /** @type {ReadRow} */
    const read = (r) => r.rows[part];
    return /** @type {const} */ ([label, read]);
  }),
  ["Render", (r) => r.render],
  ["Liked", (r) => r.taste],
];

/**
 * @param {number} count
 * @param {string} noun
 * @returns {string}
 */
function plural(count, noun) {
  return `${String(count)} ${noun}${count === 1 ? "" : "s"}`;
}

/**
 * @param {number} part
 * @param {number} whole
 * @returns {string}
 */
function share(part, whole) {
  return whole === 0 ? "—" : `${String(Math.round((100 * part) / whole))}%`;
}

/**
 * @param {number[]} values
 * @returns {number | null}
 */
function mean(values) {
  if (values.length === 0) return null;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

/**
 * @param {number | null} avg
 * @returns {string}
 */
function starsText(avg) {
  return avg === null ? "—" : `${avg.toFixed(1)}★`;
}

/**
 * A cell counts as rated once it has a rating or a verdict, as on the rating page.
 * @param {CellRow} cell
 * @returns {boolean}
 */
function isRated(cell) {
  return cell.rating !== null || cell.verdict !== null;
}

/**
 * @param {CellRow[]} cells
 * @returns {number[]}
 */
function tastes(cells) {
  return cells.flatMap((c) => (c.rating === null ? [] : [c.rating.taste]));
}

/**
 * Each flaw with the cells marked with it, the most common first, ties by name.
 * @param {CellRow[]} cells
 * @returns {[string, number][]}
 */
function flawCounts(cells) {
  /** @type {Map<string, number>} */
  const counts = new Map();
  for (const flaw of cells.flatMap((c) => c.rating?.flaws ?? []))
    counts.set(flaw, (counts.get(flaw) ?? 0) + 1);
  return [...counts].sort(([a, n], [b, m]) => m - n || a.localeCompare(b));
}

/**
 * Bars sized against the largest count.
 * @param {[string, number][]} counts
 * @returns {Bar[]}
 */
function bars(counts) {
  const most = Math.max(1, ...counts.map(([, n]) => n));
  return counts.map(([label, n]) => ({
    label,
    figure: String(n),
    width: (100 * n) / most,
  }));
}

/**
 * "2026-10-06" as "Oct 6"; any other text as it is.
 * @param {string} iso
 * @returns {string}
 */
function shortDate(iso) {
  const found = /^\d{4}-(\d{2})-(\d{2})$/.exec(iso);
  if (found === null) return iso;
  const month = MONTHS[Number(found[1]) - 1];
  return month === undefined ? iso : `${month} ${String(Number(found[2]))}`;
}

/**
 * @param {CellRow[]} cells
 * @param {(cell: CellRow) => string} keyOf
 * @returns {Map<string, CellRow[]>}
 */
function grouped(cells, keyOf) {
  /** @type {Map<string, CellRow[]>} */
  const groups = new Map();
  for (const cell of cells) {
    const group = groups.get(keyOf(cell));
    if (group === undefined) groups.set(keyOf(cell), [cell]);
    else group.push(cell);
  }
  return groups;
}

/**
 * @param {CellRow[]} images
 * @param {number} sets
 * @returns {Stat[]}
 */
function strip(images, sets) {
  const rated = images.filter(isRated).length;
  const waiting = new Set(
    images.filter((c) => !isRated(c)).map((c) => c.entry),
  );
  const favorites = images.filter((c) => c.favorite).length;
  return [
    {
      value: String(images.length),
      label: "images rendered",
      sub: plural(sets, "set"),
      amber: false,
    },
    {
      value: String(rated),
      label: "rated",
      sub: share(rated, images.length),
      amber: false,
    },
    {
      value: String(images.length - rated),
      label: "to rate",
      sub: `in ${plural(waiting.size, "set")}`,
      amber: false,
    },
    {
      value: starsText(mean(tastes(images))),
      label: "avg Liked",
      sub: plural(favorites, "favorite"),
      amber: true,
    },
    {
      value: String(bookCount(images, "yes")),
      label: "for the book",
      sub: plural(bookCount(images, "candidate"), "candidate"),
      amber: false,
    },
  ];
}

/**
 * How many cells the rater put down for the book with this answer.
 * @param {CellRow[]} cells
 * @param {"yes" | "candidate"} answer
 * @returns {number}
 */
function bookCount(cells, answer) {
  return cells.filter((c) => c.rating?.flags?.book === answer).length;
}

/**
 * @param {CellRow[]} images
 * @returns {VerdictCount[]}
 */
function verdictCounts(images) {
  const judged = images.flatMap((c) => (c.verdict === null ? [] : [c.verdict]));
  return VERDICTS.map((verdict) => {
    const count = judged.filter((v) => v === verdict).length;
    return { verdict, count, share: share(count, judged.length) };
  });
}

/**
 * Kill and fav recall and verdict match, over page-set cells with a prediction and a verdict.
 * @param {CellRow[]} cells
 * @returns {Stat[]}
 */
function predictions(cells) {
  const scored = cells.filter(
    (c) =>
      kindOf(c.entry) === "P" && c.verdict !== null && c.prediction !== null,
  );
  /**
   * @param {Verdict} verdict
   * @param {string} noun
   * @returns {Stat}
   */
  const recall = (verdict, noun) => {
    const judged = scored.filter((c) => c.verdict === verdict);
    const called = judged.filter((c) => c.prediction === verdict).length;
    return {
      value: share(called, judged.length),
      label: `${verdict} recall`,
      sub: `${String(called)} of ${String(judged.length)} ${noun}`,
      amber: true,
    };
  };
  const agree = scored.filter((c) => c.prediction === c.verdict).length;
  return [
    recall("kill", "kills"),
    recall("fav", "favs"),
    {
      value: share(agree, scored.length),
      label: "verdict match",
      sub: `${String(agree)} of ${String(scored.length)} · page sets only`,
      amber: true,
    },
  ];
}

/** @type {Record<Verdict, string>} */
const CALLED = {
  fav: "you made it a fav",
  keep: "you kept it",
  issue: "you marked an issue",
  kill: "you killed it",
};
const MISSES = 3;
const TREND = 15;

/**
 * @param {number} part
 * @param {number} whole
 * @returns {number}
 */
function fraction(part, whole) {
  return whole === 0 ? 0 : part / whole;
}

/**
 * Predicted against actual over page-set cells with both: the 4×4 grid with each
 * cell's share of its prediction, the most common wrong calls, and verdict match per set for
 * the newest sets, oldest first.
 * @param {CellRow[]} cells
 * @param {EntrySummary[]} entries newest first
 * @returns {Calibration}
 */
export function calibration(cells, entries) {
  const scored = cells.filter(
    (c) =>
      kindOf(c.entry) === "P" && c.verdict !== null && c.prediction !== null,
  );
  const rows = VERDICTS.map((predicted) => {
    const said = scored.filter((c) => c.prediction === predicted);
    return {
      predicted,
      total: said.length,
      cells: VERDICTS.map((actual) => {
        const count = said.filter((c) => c.verdict === actual).length;
        return {
          actual,
          count,
          share: fraction(count, said.length),
          label: share(count, said.length),
          right: actual === predicted,
          title: `Predicted ${predicted}, ${CALLED[actual]}: ${String(count)} of ${String(said.length)} (${share(count, said.length)})`,
        };
      }),
    };
  });
  const misses = rows
    .flatMap((row) =>
      row.cells
        .filter((cell) => !cell.right && cell.count > 0)
        .map((cell) => ({
          count: cell.count,
          text: `Predicted ${row.predicted}, ${CALLED[cell.actual]}: ${String(cell.count)} · ${share(cell.count, row.total)} of predicted ${row.predicted}s`,
        })),
    )
    .sort((a, b) => b.count - a.count)
    .slice(0, MISSES);
  const trend = entries
    .flatMap((e) => {
      const own = scored.filter((c) => c.entry === e.entry);
      if (own.length === 0) return [];
      const agree = own.filter((c) => c.prediction === c.verdict).length;
      return [
        {
          entry: e.entry,
          share: fraction(agree, own.length),
          label: share(agree, own.length),
          title: `${e.entry} · ${String(agree)} of ${String(own.length)} match (${share(agree, own.length)})`,
        },
      ];
    })
    .slice(0, TREND)
    .reverse();
  return {
    rows,
    totals: VERDICTS.map(
      (actual) => scored.filter((c) => c.verdict === actual).length,
    ),
    scored: scored.length,
    misses,
    trend,
  };
}

/**
 * Each row's average over the rated cells that have it, as a bar out of five.
 * @param {CellRow[]} cells
 * @returns {Bar[]}
 */
function rowAverages(cells) {
  const ratings = cells.flatMap((c) => (c.rating === null ? [] : [c.rating]));
  return AVERAGE_ROWS.map(([label, read]) => {
    const avg = mean(
      ratings.flatMap((r) => {
        const value = read(r);
        return typeof value === "number" ? [value] : [];
      }),
    );
    return {
      label,
      figure: avg === null ? "—" : avg.toFixed(1),
      width: avg === null ? 0 : (100 * avg) / MAX_STARS,
    };
  });
}

/**
 * @param {EntrySummary} entry
 * @param {CellRow[]} cells its rendered cells
 * @returns {SetRow}
 */
function setRow(entry, cells) {
  const rated = cells.filter(isRated).length;
  const [top] = flawCounts(cells);
  const id = encodeURIComponent(entry.entry);
  return {
    entry: entry.entry,
    name: entry.name,
    date: shortDate(entry.date),
    images: cells.length,
    rated: `${String(rated)} / ${String(cells.length)}`,
    complete: rated === cells.length,
    avg: starsText(mean(tastes(cells))),
    topFlaw: top === undefined ? "—" : `${top[0]} ×${String(top[1])}`,
    imagesHref: `/images#${id}`,
    cureHref: `/#${id}`,
  };
}

/**
 * Everything the dashboard shows, from the sets (newest first) and every rendered cell. Page
 * sets count; experiments and tests count only when included, and never toward predictions.
 * @param {EntrySummary[]} entries
 * @param {CellRow[]} cells
 * @param {boolean} withLab
 * @returns {Dashboard}
 */
export function dashboard(entries, cells, withLab) {
  const counted = (/** @type {string} */ entry) =>
    kindOf(entry) === "P" || (withLab && isLab(entry));
  const sets = entries.filter((e) => counted(e.entry));
  const images = cells.filter((c) => counted(c.entry));
  const labSets = entries.filter((e) => isLab(e.entry)).length;
  const imagesBySet = grouped(images, (c) => c.entry);
  const liked = tastes(images);
  return {
    context: withLab
      ? `${plural(sets.length, "set")} · experiments included`
      : `${plural(sets.length, "page set")} · ${plural(labSets, "experiment set")} left out`,
    stats: strip(images, sets.length),
    liked: bars(
      STARS.map((n) => [
        `${String(n)}★`,
        liked.filter((taste) => taste === n).length,
      ]),
    ),
    verdicts: verdictCounts(images),
    flaws: bars(flawCounts(images).slice(0, TOP_FLAWS)),
    predictions: predictions(cells),
    calibration: calibration(cells, entries),
    averages: rowAverages(images),
    setMeta: `${plural(sets.length, "set")} · newest first`,
    sets: sets.map((e) => setRow(e, imagesBySet.get(e.entry) ?? [])),
  };
}

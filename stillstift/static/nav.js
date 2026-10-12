/** @typedef {"Dashboard" | "Images" | "Curate" | "Experiments" | "Tests"} PageName */
/** @typedef {{ label: PageName, href: string, desc: string, group: string }} Page */
/**
 * @typedef {{
 *   label: PageName,
 *   href: string,
 *   desc: string,
 *   key: string,
 *   current: boolean,
 * }} PageItem
 */
/** @typedef {{ caption: string, items: PageItem[] }} PageGroup */

/** The curator's pages in menu order; the order also gives each its number key. */
/** @type {readonly Page[]} */
export const PAGES = [
  {
    label: "Dashboard",
    href: "/dashboard",
    desc: "Ratings, verdicts, flaws, prediction recall",
    group: "Overview",
  },
  {
    label: "Images",
    href: "/images",
    desc: "Every page, filtered and sorted",
    group: "Overview",
  },
  {
    label: "Curate",
    href: "/",
    desc: "Rate pages cell by cell",
    group: "Curate",
  },
  {
    label: "Experiments",
    href: "/experiments",
    desc: "X sets: an idea tried, kept out of stats",
    group: "Lab",
  },
  {
    label: "Tests",
    href: "/tests",
    desc: "T sets: one craft question, kept out of stats",
    group: "Lab",
  },
];

/**
 * The launcher's groups, each page with its number key and whether it is the one open.
 * @param {PageName} current
 * @returns {PageGroup[]}
 */
export function pageGroups(current) {
  /** @type {PageGroup[]} */
  const groups = [];
  PAGES.forEach((page, at) => {
    const item = {
      label: page.label,
      href: page.href,
      desc: page.desc,
      key: String(at + 1),
      current: page.label === current,
    };
    const group = groups.find((g) => g.caption === page.group);
    if (group === undefined)
      groups.push({ caption: page.group, items: [item] });
    else group.items.push(item);
  });
  return groups;
}

/**
 * Where a number key pressed in the open launcher goes; null for any other key.
 * @param {string} key
 * @returns {string | null}
 */
export function pageForKey(key) {
  if (!/^[1-9]$/.test(key)) return null;
  return PAGES[Number(key) - 1]?.href ?? null;
}

/**
 * Which of the launcher button's dots is lit: the current page's place in the menu.
 * @param {PageName} current
 * @returns {number}
 */
export function litDot(current) {
  return PAGES.findIndex((p) => p.label === current);
}

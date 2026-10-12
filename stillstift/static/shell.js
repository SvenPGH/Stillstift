import { button, el } from "./dom.js";
import { litDot, pageForKey, pageGroups } from "./nav.js";
import { applySavedTheme, mountThemeToggle } from "./theme.js";

/** @typedef {import("./nav.js").PageName} PageName */
/**
 * @typedef {{ label: string, onClick: () => void, hint?: string, disabled?: boolean, danger?: boolean }} Action
 */
/** @typedef {Action | "divider"} ActionLine */
/** @typedef {{ general: Action[], items: ActionLine[] }} ActionsModel */

/** A 3×2 grid of dots, one per page and a spare. */
const DOTS = 6;

/**
 * The launcher: a dot-grid button naming the page, and a panel of every page as a card.
 * @param {HTMLElement} host
 * @param {PageName} page
 * @param {{ open: boolean }} state
 * @param {() => void} rerender
 */
function renderNav(host, page, state, rerender) {
  const dots = el("span", "nav-dots");
  for (let at = 0; at < DOTS; at++)
    dots.append(el("span", `nav-dot${at === litDot(page) ? " on" : ""}`));
  const toggle = button("nav-btn", "", () => {
    state.open = !state.open;
    rerender();
  });
  toggle.ariaHasPopup = "menu";
  toggle.ariaExpanded = String(state.open);
  toggle.append(dots, el("span", "", page));
  host.replaceChildren(toggle);
  if (!state.open) return;
  const panel = el("div", "launcher");
  panel.role = "menu";
  for (const group of pageGroups(page)) {
    const grid = el("div", "launcher-grid");
    for (const item of group.items) {
      const card = el("a", `launcher-card${item.current ? " current" : ""}`);
      card.href = item.href;
      card.role = "menuitem";
      if (item.current) card.ariaCurrent = "page";
      const label = el("span", "launcher-label", item.label);
      if (item.current) label.append(el("span", "launcher-mark", "●"));
      card.append(
        label,
        el("span", "launcher-desc", item.desc),
        el("span", "launcher-key mono", item.key),
      );
      grid.append(card);
    }
    const section = el("div", "launcher-group");
    section.append(el("div", "menu-cap", group.caption), grid);
    panel.append(section);
  }
  const keys = pageGroups(page).flatMap((g) => g.items).length;
  panel.append(
    el("div", "launcher-foot mono", `1–${String(keys)} to jump · esc to close`),
  );
  host.append(panel);
}

/**
 * @param {Action} action
 * @param {() => void} close
 */
function menuItem(action, close) {
  const item = button(
    `menu-item${action.danger === true ? " danger" : ""}`,
    "",
    () => {
      close();
      action.onClick();
    },
  );
  item.role = "menuitem";
  item.disabled = action.disabled === true;
  item.append(
    el("span", "", action.label),
    el("span", "menu-hint mono", action.hint ?? ""),
  );
  return item;
}

/**
 * The Actions menu: the theme and any page-wide actions, then the page's own items.
 * @param {HTMLElement} host
 * @param {PageName} page
 * @param {{ open: boolean }} state
 * @param {{ model: ActionsModel, rerender: () => void }} at
 */
function renderActions(host, page, state, { model, rerender }) {
  const toggle = button("actions-btn", "Actions", () => {
    state.open = !state.open;
    rerender();
  });
  toggle.ariaHasPopup = "menu";
  toggle.ariaExpanded = String(state.open);
  toggle.append(el("span", "caret", "▼"));
  host.replaceChildren(toggle);
  if (!state.open) return;
  const close = () => {
    state.open = false;
    rerender();
  };
  const list = el("div", "actions-list");
  list.role = "menu";
  const theme = el("div", "seg");
  theme.role = "radiogroup";
  theme.ariaLabel = "Theme";
  mountThemeToggle(theme);
  const themeRow = el("div", "menu-theme");
  themeRow.append(el("span", "", "Theme"), theme);
  list.append(el("div", "menu-cap", "General"), themeRow);
  list.append(...model.general.map((a) => menuItem(a, close)));
  if (model.items.length > 0) {
    list.append(el("div", "menu-sep"), el("div", "menu-cap", page));
    list.append(
      ...model.items.map((line) =>
        line === "divider" ? el("div", "menu-sep") : menuItem(line, close),
      ),
    );
  }
  host.append(list);
}

/**
 * Mount the page menu and the Actions menu; the page calls `render` whenever its state changes.
 * @param {{ nav: HTMLElement, actions: HTMLElement, page: PageName, model: () => ActionsModel }} at
 * @returns {{ render: () => void }}
 */
export function mountShell({ nav, actions, page, model }) {
  applySavedTheme();
  const navState = { open: false };
  const actionsState = { open: false };
  const render = () => {
    renderNav(nav, page, navState, render);
    renderActions(actions, page, actionsState, {
      model: model(),
      rerender: render,
    });
  };
  document.addEventListener(
    "click",
    (event) => {
      const target = /** @type {Node} */ (event.target);
      const wasOpen = navState.open || actionsState.open;
      if (navState.open && !nav.contains(target)) navState.open = false;
      if (actionsState.open && !actions.contains(target))
        actionsState.open = false;
      if (wasOpen && !navState.open && !actionsState.open) render();
    },
    true,
  );
  document.addEventListener("keydown", (event) => {
    if (!navState.open && !actionsState.open) return;
    if (event.key === "Escape") {
      navState.open = false;
      actionsState.open = false;
      render();
      return;
    }
    const href = navState.open ? pageForKey(event.key) : null;
    if (href !== null) location.href = href;
  });
  render();
  return { render };
}

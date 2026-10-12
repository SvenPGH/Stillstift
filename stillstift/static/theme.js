/** @typedef {"dark" | "light"} Theme */

const KEY = "stillstift-theme";
/** @type {readonly (readonly [Theme, string, string])[]} */
const OPTIONS = [
  ["dark", "☾︎", "Dark"],
  ["light", "☀︎", "Light"],
];

/**
 * The theme kept in storage; dark when none is kept or storage is out of reach.
 * @param {Pick<Storage, "getItem">} storage
 * @returns {Theme}
 */
export function savedTheme(storage) {
  try {
    return storage.getItem(KEY) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

/**
 * @param {Pick<Storage, "setItem">} storage
 * @param {Theme} theme
 */
function saveTheme(storage, theme) {
  try {
    storage.setItem(KEY, theme);
  } catch {
    // Private windows refuse storage; the choice lasts the page.
  }
}

/** @param {Theme} theme */
function applyTheme(theme) {
  document.documentElement.dataset["theme"] = theme;
}

/** Apply the kept theme to the page, before any menu shows the toggle. */
export function applySavedTheme() {
  applyTheme(savedTheme(localStorage));
}

/**
 * Fill the segmented ☾︎ Dark / ☀︎ Light toggle and apply the kept theme.
 * @param {HTMLElement} group
 */
export function mountThemeToggle(group) {
  const render = () => {
    const current = savedTheme(localStorage);
    applyTheme(current);
    group.replaceChildren(
      ...OPTIONS.map(([theme, glyph, label]) => {
        const button = document.createElement("button");
        button.type = "button";
        button.role = "radio";
        button.className = "seg-btn theme-btn";
        button.textContent = `${glyph} ${label}`;
        button.ariaChecked = String(theme === current);
        button.addEventListener("click", () => {
          saveTheme(localStorage, theme);
          render();
        });
        return button;
      }),
    );
  };
  render();
}

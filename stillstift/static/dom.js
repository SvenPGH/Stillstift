/**
 * @template {HTMLElement} T
 * @param {string} id
 * @param {new () => T} type
 * @returns {T}
 */
export function byId(id, type) {
  const element = document.getElementById(id);
  if (!(element instanceof type)) throw new Error(`#${id} is missing`);
  return element;
}

export class ApiError extends Error {
  /**
   * @param {number} status
   * @param {string} message
   */
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

/**
 * @param {string} url
 * @param {RequestInit} [init]
 * @returns {Promise<unknown>}
 */
export async function api(url, init) {
  const response = await fetch(url, init);
  if (!response.ok) {
    const method = init?.method ?? "GET";
    throw new ApiError(
      response.status,
      `${method} ${url}: ${String(response.status)}`,
    );
  }
  return response.status === 204
    ? null
    : /** @type {unknown} */ (await response.json());
}

/** @param {unknown} body */
export function json(body) {
  return {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

/**
 * @template {keyof HTMLElementTagNameMap} K
 * @param {K} tag
 * @param {string} className
 * @param {string} [text]
 * @returns {HTMLElementTagNameMap[K]}
 */
export function el(tag, className, text) {
  const element = document.createElement(tag);
  element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

/**
 * @param {string} className
 * @param {string} text
 * @param {() => void} onClick
 * @returns {HTMLButtonElement}
 */
export function button(className, text, onClick) {
  const b = el("button", className, text);
  b.type = "button";
  b.addEventListener("click", onClick);
  return b;
}

/**
 * Fill a radio group of pills, the current one checked.
 * @template T
 * @param {HTMLElement} group
 * @param {readonly (readonly [T, string])[]} choices
 * @param {T} current
 * @param {(value: T) => void} pick
 */
export function pills(group, choices, current, pick) {
  group.replaceChildren(
    ...choices.map(([value, label]) => {
      const pill = button("pill-opt", label, () => {
        pick(value);
      });
      pill.role = "radio";
      pill.ariaChecked = String(value === current);
      return pill;
    }),
  );
}

/**
 * Fill a select with its choices, the current one selected.
 * @param {HTMLSelectElement} select
 * @param {readonly (readonly [string, string])[]} choices
 * @param {string} current
 */
export function fillSelect(select, choices, current) {
  select.replaceChildren(
    ...choices.map(([value, label]) => new Option(label, value)),
  );
  select.value = current;
}

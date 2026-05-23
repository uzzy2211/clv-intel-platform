/**
 * kpi-card.js — Animated KPI counter component
 */

/**
 * Animate a number counting up from 0 to target.
 * @param {HTMLElement} el - Element to update
 * @param {number} target - Target value
 * @param {string} [prefix=''] - Prefix (e.g. '$')
 * @param {string} [suffix=''] - Suffix (e.g. '%')
 * @param {number} [decimals=0] - Decimal places
 * @param {number} [duration=1200] - Animation duration ms
 */
export function animateCounter(el, target, prefix = '', suffix = '', decimals = 0, duration = 1200) {
  const start = performance.now();
  const startVal = 0;

  function easeOut(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function tick(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    const current = startVal + (target - startVal) * easeOut(progress);

    const formatted = decimals > 0
      ? current.toFixed(decimals)
      : Math.floor(current).toLocaleString();

    el.textContent = `${prefix}${formatted}${suffix}`;

    if (progress < 1) requestAnimationFrame(tick);
    else el.textContent = `${prefix}${target.toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}${suffix}`;
  }

  requestAnimationFrame(tick);
}

/**
 * Render a KPI card into a container element.
 * @param {HTMLElement} container
 * @param {object} opts
 * @param {string} opts.label
 * @param {number} opts.value
 * @param {string} [opts.prefix]
 * @param {string} [opts.suffix]
 * @param {number} [opts.decimals]
 * @param {string} [opts.sub]
 * @param {string} [opts.color] - CSS color for accent
 * @param {string} [opts.icon] - SVG string
 */
export function renderKpiCard(container, opts) {
  const {
    label, value, prefix = '', suffix = '', decimals = 0,
    sub = '', color = 'var(--accent)', icon = '',
  } = opts;

  container.style.setProperty('--card-accent', color);
  container.style.setProperty('--card-accent-dim', color.replace(')', ', 0.15)').replace('var(', 'rgba('));

  container.innerHTML = `
    <div class="kpi-label">${label}</div>
    <div class="kpi-value" id="kpi-val-${label.replace(/\s+/g, '-').toLowerCase()}">0</div>
    <div class="kpi-sub">${sub}</div>
    ${icon ? `<div class="kpi-icon">${icon}</div>` : ''}
  `;

  const valEl = container.querySelector('.kpi-value');
  // Delay slightly so the page renders first
  setTimeout(() => animateCounter(valEl, value, prefix, suffix, decimals), 100);
}

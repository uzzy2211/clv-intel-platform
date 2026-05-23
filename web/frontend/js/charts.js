/**
 * charts.js — Chart rendering utilities
 * Split-theme: dark sidebar (#0d1117) + white canvas (#ffffff)
 * Accent: #00ff88 terminal green
 */

// ── Chart.js global defaults (white canvas) ────────────────────────────
Chart.defaults.color          = '#64748b';
Chart.defaults.borderColor    = '#e2e8f0';
Chart.defaults.font.family    = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size      = 11;
Chart.defaults.font.weight    = '500';

// ── Palette ────────────────────────────────────────────────────────────
const C = {
  green:   '#00ff88',
  green2:  '#00c96e',
  green3:  '#00a85a',
  violet:  '#7c3aed',
  blue:    '#0ea5e9',
  amber:   '#f59e0b',
  red:     '#ef4444',
  slate:   '#64748b',
  dark:    '#0f172a',
};

const SEGMENT_COLORS = {
  'Champions':            C.green3,
  'Loyal Customers':      C.violet,
  'At Risk':              C.amber,
  'Lost':                 C.slate,
  'New Customers':        C.blue,
  'Hibernating':          '#94a3b8',
  'High Value Customers': C.green3,
  'Low Value / Lost':     C.slate,
};

export function segColor(name) {
  return SEGMENT_COLORS[name] || C.slate;
}

// ── Shared tooltip config ──────────────────────────────────────────────
const TOOLTIP = {
  backgroundColor: '#ffffff',
  titleColor:      '#0f172a',
  bodyColor:       '#64748b',
  borderColor:     '#e2e8f0',
  borderWidth:     1,
  padding:         12,
  cornerRadius:    10,
  boxShadow:       '0 4px 16px rgba(0,0,0,0.08)',
};

// ── Donut Chart ────────────────────────────────────────────────────────
export function renderDonut(canvas, data) {
  if (canvas._chart) canvas._chart.destroy();

  const colors = data.map(d => segColor(d.segment));

  canvas._chart = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: data.map(d => d.segment),
      datasets: [{
        data: data.map(d => d.count),
        backgroundColor: colors.map(c => c + '22'),
        borderColor:     colors,
        borderWidth:     2,
        hoverOffset:     8,
        hoverBorderWidth: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            padding: 16,
            usePointStyle: true,
            pointStyleWidth: 8,
            font: { size: 11, weight: '600' },
            color: '#334155',
          },
        },
        tooltip: {
          ...TOOLTIP,
          callbacks: {
            label: ctx => `  ${ctx.label}: ${ctx.parsed.toLocaleString()} customers`,
          },
        },
      },
    },
  });
}

// ── Horizontal Bar (CLV by segment) ───────────────────────────────────
export function renderClvBar(canvas, data) {
  if (canvas._chart) canvas._chart.destroy();

  const sorted = [...data].sort((a, b) => b.total_clv - a.total_clv);
  const colors = sorted.map(d => segColor(d.segment));

  canvas._chart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: sorted.map(d => d.segment),
      datasets: [{
        label: 'Total CLV ($)',
        data:  sorted.map(d => d.total_clv),
        backgroundColor: colors.map(c => c + '20'),
        borderColor:     colors,
        borderWidth:     2,
        borderRadius:    6,
        borderSkipped:   false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
        tooltip: {
          ...TOOLTIP,
          callbacks: {
            label: ctx => `  $${ctx.parsed.x.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
          },
        },
      },
      scales: {
        x: {
          grid:   { color: '#f1f5f9' },
          border: { display: false },
          ticks:  {
            color: '#94a3b8',
            callback: v => '$' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v),
          },
        },
        y: {
          grid:   { display: false },
          border: { display: false },
          ticks:  { color: '#334155', font: { weight: '600' } },
        },
      },
    },
  });
}

// ── CLV Histogram ──────────────────────────────────────────────────────
export function renderClvHistogram(canvas, bins) {
  if (canvas._chart) canvas._chart.destroy();

  canvas._chart = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: bins.map(b => `$${b.bin_start.toFixed(0)}`),
      datasets: [{
        label: 'Customers',
        data:  bins.map(b => b.count),
        backgroundColor: C.green + '22',
        borderColor:     C.green3,
        borderWidth:     1.5,
        borderRadius:    4,
        borderSkipped:   false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          ...TOOLTIP,
          callbacks: {
            title: items => {
              const b = bins[items[0].dataIndex];
              return `$${b.bin_start.toFixed(0)} – $${b.bin_end.toFixed(0)}`;
            },
            label: ctx => `  ${ctx.parsed.y} customers`,
          },
        },
      },
      scales: {
        x: {
          grid:   { display: false },
          border: { display: false },
          ticks:  { maxTicksLimit: 10, color: '#94a3b8' },
        },
        y: {
          type:   'logarithmic',
          grid:   { color: '#f1f5f9' },
          border: { display: false },
          ticks:  { color: '#94a3b8', callback: v => v },
        },
      },
    },
  });
}

// ── D3 PCA Scatter ─────────────────────────────────────────────────────
export function renderPcaScatter(container, points, onHover) {
  container.innerHTML = '';

  const W = container.clientWidth || 600;
  const H = 420;
  const margin = { top: 20, right: 150, bottom: 44, left: 44 };
  const w = W - margin.left - margin.right;
  const h = H - margin.top - margin.bottom;

  const svg = d3.select(container)
    .append('svg')
    .attr('width', W).attr('height', H)
    .style('overflow', 'visible');

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const xExt = d3.extent(points, d => d.pca_1);
  const yExt = d3.extent(points, d => d.pca_2);
  const pad  = 0.5;

  const xScale = d3.scaleLinear().domain([xExt[0]-pad, xExt[1]+pad]).range([0, w]);
  const yScale = d3.scaleLinear().domain([yExt[0]-pad, yExt[1]+pad]).range([h, 0]);

  // Grid
  g.append('g').attr('class', 'grid')
    .call(d3.axisLeft(yScale).tickSize(-w).tickFormat(''))
    .selectAll('line').style('stroke', '#f1f5f9');
  g.select('.grid .domain').remove();

  g.append('g').attr('class', 'grid2')
    .attr('transform', `translate(0,${h})`)
    .call(d3.axisBottom(xScale).tickSize(-h).tickFormat(''))
    .selectAll('line').style('stroke', '#f1f5f9');
  g.select('.grid2 .domain').remove();

  // Axes
  g.append('g').attr('transform', `translate(0,${h})`)
    .call(d3.axisBottom(xScale).ticks(6))
    .call(ax => ax.select('.domain').style('stroke', '#e2e8f0'))
    .selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');

  g.append('g')
    .call(d3.axisLeft(yScale).ticks(6))
    .call(ax => ax.select('.domain').style('stroke', '#e2e8f0'))
    .selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');

  // Axis labels
  g.append('text').attr('x', w/2).attr('y', h+36)
    .attr('text-anchor', 'middle')
    .style('fill', '#94a3b8').style('font-size', '11px').style('font-weight', '600')
    .text('PCA Component 1');

  g.append('text').attr('transform', 'rotate(-90)').attr('x', -h/2).attr('y', -32)
    .attr('text-anchor', 'middle')
    .style('fill', '#94a3b8').style('font-size', '11px').style('font-weight', '600')
    .text('PCA Component 2');

  // Tooltip
  const tooltip = d3.select(container)
    .append('div')
    .style('position', 'absolute')
    .style('background', '#ffffff')
    .style('border', '1px solid #e2e8f0')
    .style('border-radius', '10px')
    .style('padding', '10px 14px')
    .style('font-size', '11px')
    .style('color', '#0f172a')
    .style('pointer-events', 'none')
    .style('opacity', 0)
    .style('font-family', "'Inter', sans-serif")
    .style('box-shadow', '0 4px 16px rgba(0,0,0,0.1)')
    .style('z-index', 10);

  // Points
  g.selectAll('circle')
    .data(points)
    .enter()
    .append('circle')
    .attr('cx', d => xScale(d.pca_1))
    .attr('cy', d => yScale(d.pca_2))
    .attr('r', 4)
    .attr('fill', d => segColor(d.segment) + '55')
    .attr('stroke', d => segColor(d.segment))
    .attr('stroke-width', 1)
    .style('cursor', 'pointer')
    .on('mouseover', function(event, d) {
      d3.select(this).attr('r', 7).attr('stroke-width', 2)
        .attr('fill', segColor(d.segment) + 'aa');
      tooltip.style('opacity', 1).html(`
        <div style="font-weight:700;color:${segColor(d.segment)};margin-bottom:4px">${d.segment}</div>
        <div style="color:#64748b">ID: <strong style="color:#0f172a">${d.customer_id}</strong></div>
        <div style="color:#64748b">CLV: <strong style="color:#00a85a">$${d.clv.toFixed(2)}</strong></div>
      `);
      if (onHover) onHover(d);
    })
    .on('mousemove', function(event) {
      const rect = container.getBoundingClientRect();
      tooltip
        .style('left', (event.clientX - rect.left + 14) + 'px')
        .style('top',  (event.clientY - rect.top  - 32) + 'px');
    })
    .on('mouseout', function(event, d) {
      d3.select(this).attr('r', 4).attr('stroke-width', 1)
        .attr('fill', segColor(d.segment) + '55');
      tooltip.style('opacity', 0);
    });

  // Legend
  const segments = [...new Set(points.map(d => d.segment))];
  const legend = svg.append('g')
    .attr('transform', `translate(${margin.left + w + 16}, ${margin.top + 10})`);

  segments.forEach((seg, i) => {
    const row = legend.append('g').attr('transform', `translate(0, ${i * 22})`);
    row.append('circle').attr('r', 5)
      .attr('fill', segColor(seg) + '55')
      .attr('stroke', segColor(seg))
      .attr('stroke-width', 1.5);
    row.append('text').attr('x', 12).attr('y', 4)
      .style('fill', '#334155').style('font-size', '10px').style('font-weight', '600')
      .text(seg);
  });
}

// ── D3 Alive Probability Heatmap ───────────────────────────────────────
export function renderAliveHeatmap(container, data) {
  container.innerHTML = '';

  const { frequency_range, recency_range, matrix } = data;
  if (!matrix || matrix.length === 0) return;

  const W = container.clientWidth || 560;
  const H = 360;
  const margin = { top: 20, right: 80, bottom: 50, left: 60 };
  const w = W - margin.left - margin.right;
  const h = H - margin.top - margin.bottom;

  const svg = d3.select(container)
    .append('svg').attr('width', W).attr('height', H);

  const g = svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const cellW = w / frequency_range.length;
  const cellH = h / recency_range.length;

  // Color scale: white → green → dark
  const colorScale = d3.scaleSequential()
    .domain([0, 1])
    .interpolator(d3.interpolateRgbBasis([
      '#f8fafc', '#d1fae5', '#00c96e', '#00a85a', '#0d1117'
    ]));

  recency_range.forEach((rec, ri) => {
    frequency_range.forEach((freq, fi) => {
      g.append('rect')
        .attr('x', fi * cellW).attr('y', ri * cellH)
        .attr('width', cellW).attr('height', cellH)
        .attr('fill', colorScale(matrix[ri][fi]))
        .attr('rx', 1);
    });
  });

  // Axes
  const xScale = d3.scaleLinear().domain([0, frequency_range.length-1]).range([0, w]);
  const yScale = d3.scaleLinear().domain([0, recency_range.length-1]).range([0, h]);

  g.append('g').attr('transform', `translate(0,${h})`)
    .call(d3.axisBottom(xScale).ticks(6)
      .tickFormat(i => frequency_range[Math.round(i)] ?? ''))
    .call(ax => ax.select('.domain').style('stroke', '#e2e8f0'))
    .selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');

  g.append('g')
    .call(d3.axisLeft(yScale).ticks(6)
      .tickFormat(i => recency_range[Math.round(i)] ?? ''))
    .call(ax => ax.select('.domain').style('stroke', '#e2e8f0'))
    .selectAll('text').style('fill', '#94a3b8').style('font-size', '10px');

  g.append('text').attr('x', w/2).attr('y', h+40)
    .attr('text-anchor', 'middle')
    .style('fill', '#94a3b8').style('font-size', '11px').style('font-weight', '600')
    .text('Historical Purchases (Frequency)');

  g.append('text').attr('transform', 'rotate(-90)').attr('x', -h/2).attr('y', -46)
    .attr('text-anchor', 'middle')
    .style('fill', '#94a3b8').style('font-size', '11px').style('font-weight', '600')
    .text('Recency (Days)');

  // Color legend
  const defs = svg.append('defs');
  const grad = defs.append('linearGradient').attr('id', 'heatmap-grad')
    .attr('x1','0%').attr('x2','0%').attr('y1','100%').attr('y2','0%');
  [0, 0.25, 0.5, 0.75, 1].forEach(t => {
    grad.append('stop').attr('offset', `${t*100}%`).attr('stop-color', colorScale(t));
  });

  const lx = margin.left + w + 14;
  svg.append('rect').attr('x', lx).attr('y', margin.top)
    .attr('width', 12).attr('height', h).attr('fill', 'url(#heatmap-grad)').attr('rx', 4);
  svg.append('text').attr('x', lx+16).attr('y', margin.top+8)
    .style('fill','#94a3b8').style('font-size','9px').style('font-weight','600').text('1.0');
  svg.append('text').attr('x', lx+16).attr('y', margin.top+h)
    .style('fill','#94a3b8').style('font-size','9px').style('font-weight','600').text('0.0');
  svg.append('text').attr('x', lx+16).attr('y', margin.top+h/2)
    .style('fill','#94a3b8').style('font-size','9px').style('font-weight','600').text('P(alive)');
}

// ── Radar Chart ────────────────────────────────────────────────────────
export function renderRadar(canvas, customer, maxVals) {
  if (canvas._chart) canvas._chart.destroy();

  const normalize = (val, max) => max > 0 ? Math.min(val / max, 1) : 0;

  canvas._chart = new Chart(canvas, {
    type: 'radar',
    data: {
      labels: ['Frequency', 'Monetary', 'Tenure', 'CLV', 'Activity'],
      datasets: [{
        label: `Customer ${customer.customer_id}`,
        data: [
          normalize(customer.frequency,  maxVals.frequency),
          normalize(customer.monetary,   maxVals.monetary),
          normalize(customer.tenure,     maxVals.tenure),
          normalize(customer.clv,        maxVals.clv),
          normalize(maxVals.recency - customer.recency, maxVals.recency),
        ],
        backgroundColor: 'rgba(0,201,110,0.1)',
        borderColor:     C.green3,
        borderWidth:     2,
        pointBackgroundColor: C.green3,
        pointBorderColor:     '#ffffff',
        pointBorderWidth:     2,
        pointRadius:          5,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          min: 0, max: 1,
          ticks: { display: false },
          grid:  { color: '#e2e8f0' },
          pointLabels: { color: '#334155', font: { size: 10, weight: '600' } },
          angleLines:  { color: '#e2e8f0' },
        },
      },
      plugins: { legend: { display: false } },
    },
  });
}

// ── Segment Rings (D3) ─────────────────────────────────────────────────
export function renderSegmentRings(container, segments) {
  container.innerHTML = '';

  const size = Math.min(container.clientWidth || 280, 280);
  const cx = size / 2, cy = size / 2;
  const maxR = size / 2 - 24;

  const svg = d3.select(container)
    .append('svg').attr('width', size).attr('height', size);

  const maxCount = Math.max(...segments.map(s => s.customer_count));
  const maxClv   = Math.max(...segments.map(s => s.avg_clv));

  segments.forEach((seg) => {
    const r       = maxR * (0.28 + 0.72 * (seg.customer_count / maxCount));
    const strokeW = 2.5 + 7 * (seg.avg_clv / maxClv);
    const color   = seg.color || C.slate;

    // Background ring
    svg.append('circle')
      .attr('cx', cx).attr('cy', cy).attr('r', r)
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', strokeW + 4)
      .attr('stroke-opacity', 0.07);

    // Arc
    const arc = d3.arc()
      .innerRadius(r - strokeW / 2)
      .outerRadius(r + strokeW / 2)
      .startAngle(-Math.PI / 2)
      .endAngle(-Math.PI / 2 + 2 * Math.PI * (seg.customer_count / maxCount));

    svg.append('path')
      .attr('transform', `translate(${cx},${cy})`)
      .attr('d', arc())
      .attr('fill', color)
      .attr('opacity', 0.85);

    // Label
    const labelAngle = -Math.PI / 2 + Math.PI * (seg.customer_count / maxCount);
    const lx = cx + (r + 16) * Math.cos(labelAngle);
    const ly = cy + (r + 16) * Math.sin(labelAngle);

    svg.append('text')
      .attr('x', lx).attr('y', ly)
      .attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
      .style('fill', color).style('font-size', '8px').style('font-weight', '700')
      .style('font-family', "'Inter', sans-serif")
      .text(seg.name.split(' ')[0]);
  });

  // Center total
  svg.append('text').attr('x', cx).attr('y', cy - 9)
    .attr('text-anchor', 'middle')
    .style('fill', '#0f172a').style('font-size', '22px').style('font-weight', '800')
    .style('font-family', "'Inter', sans-serif")
    .text(segments.reduce((s, x) => s + x.customer_count, 0).toLocaleString());

  svg.append('text').attr('x', cx).attr('y', cy + 12)
    .attr('text-anchor', 'middle')
    .style('fill', '#94a3b8').style('font-size', '10px').style('font-weight', '600')
    .text('customers');
}

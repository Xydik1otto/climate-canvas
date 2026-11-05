// climate-canvas dashboard (vanilla JS, no build step)
const $ = (s) => document.querySelector(s);
let timelineChart = null, seasonsChart = null;

const api = (path) => fetch(path).then((r) => r.json());
// Colors for Chart.js read from CSS variables, so charts follow the theme.
const themeColors = () => {
  const s = getComputedStyle(document.body);
  return { fg: s.getPropertyValue("--fg").trim() || "#e6e1cf", grid: s.getPropertyValue("--border").trim() || "#22303c" };
};

function comfortClass(t, [min, max]) {
  if (t == null) return "";
  if (t < min) return "comfort-cold";
  if (t > max) return "comfort-hot";
  return "comfort-ok";
}

// ---------- Rooms ----------
async function loadRooms() {
  const data = await api("/api/rooms");
  $("#mode-badge").textContent = data.demo ? "demo mode" : "Home Assistant";
  const grid = $("#room-grid");
  grid.innerHTML = "";
  for (const [room, st] of Object.entries(data.rooms)) {
    const cls = comfortClass(st.temperature, st.comfort);
    const card = document.createElement("div");
    card.className = "room-card";
    const co2 = st.co2 != null ? `<div class="hum">🫁 ${st.co2} ppm</div>` : "";
    const voc = st.voc != null ? `<div class="hum">🧪 ${st.voc} ppb VOC</div>` : "";
    card.innerHTML = `<h3>${room}</h3>
      <div class="temp ${cls}">${st.temperature ?? "—"}°C</div>
      <div class="hum">💧 ${st.humidity ?? "—"}% · комфорт ${st.comfort[0]}–${st.comfort[1]}°C</div>${co2}${voc}`;
    grid.appendChild(card);
  }
  const names = Object.keys(data.rooms);
  for (const sel of ["#tl-room", "#hm-room", "#se-room", "#en-room"]) {
    $(sel).innerHTML = names.map((n) => `<option>${n}</option>`).join("");
  }
}

// ---------- Timeline with day/night shading ----------
function nightBands(points) {
  // Build day/night shading bands (night = 22:00–07:00 UTC approximation of local evening).
  const bands = [];
  let start = null;
  for (const [ts] of points) {
    const h = new Date(ts).getHours();
    const night = h >= 22 || h < 7;
    if (night && start === null) start = ts;
    if (!night && start !== null) { bands.push([start, ts]); start = null; }
  }
  if (start !== null && points.length) bands.push([start, points[points.length - 1][0]]);
  return bands;
}

async function loadTimeline() {
  const room = $("#tl-room").value, metric = $("#tl-metric").value, days = $("#tl-days").value;
  const [data, ann] = await Promise.all([
    api(`/api/timeline?room=${encodeURIComponent(room)}&metric=${metric}&days=${days}`),
    api(`/api/annotations?room=${encodeURIComponent(room)}&days=${days}`),
  ]);
  const points = data.points;
  const annotations = ann.annotations || [];
  $("#tl-annotations").innerHTML = annotations.length
    ? "Мітки: " + annotations.map((a) =>
        `<span class="ann"><b>${a.label}</b> <small>${a.ts.slice(0, 16).replace("T", " ")}</small>` +
        `<button data-id="${a.id}" class="ann-del" title="видалити">✕</button></span>`).join(" ")
    : "";
  $("#tl-annotations").querySelectorAll(".ann-del").forEach((btn) =>
    btn.addEventListener("click", async () => {
      await fetch(`/api/annotations/${btn.dataset.id}`, { method: "DELETE" });
      loadTimeline();
    }));
  const labels = points.map(([ts]) => new Date(ts).toLocaleString("uk-UA", { day: "2-digit", month: "2-digit", hour: "2-digit" }));
  const ctx = $("#timeline-chart");
  if (timelineChart) timelineChart.destroy();
  timelineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{ label: `${room} · ${metric}`, data: points.map(([, v]) => v), pointRadius: 0, borderWidth: 1.5, borderColor: "#4ecdc4", tension: 0.2 }],
    },
    options: {
      scales: { y: { grid: { color: themeColors().grid } }, x: { grid: { display: false }, ticks: { maxTicksLimit: 14 } } },
      plugins: { legend: { labels: { color: themeColors().fg } } },
    },
    plugins: [
      {
        id: "nightShading",
        beforeDatasetsDraw(chart, args, opts) {
          const { ctx, chartArea, scales: { x } } = chart;
          if (!chartArea) return;
          const bands = nightBands(points);
          ctx.save();
          ctx.fillStyle = "rgba(10,16,26,0.45)";
          for (const [a, b] of bands) {
            const x1 = x.getPixelForValue(labels.indexOf(new Date(a).toLocaleString("uk-UA", { day: "2-digit", month: "2-digit", hour: "2-digit" })));
            const x2 = x.getPixelForValue(labels.indexOf(new Date(b).toLocaleString("uk-UA", { day: "2-digit", month: "2-digit", hour: "2-digit" })));
            if (x2 > x1) ctx.fillRect(x1, chartArea.top, x2 - x1, chartArea.bottom - chartArea.top);
          }
          ctx.restore();
        },
      },
      {
        id: "annotationLines",
        afterDatasetsDraw(chart) {
          const { ctx, chartArea, scales: { x } } = chart;
          if (!chartArea || !annotations.length) return;
          ctx.save();
          ctx.strokeStyle = "#e5c07b";
          ctx.setLineDash([4, 3]);
          ctx.font = "10px system-ui";
          for (const a of annotations) {
            // nearest hourly bucket to the annotation timestamp
            let idx = points.findIndex(([ts]) => new Date(ts) >= new Date(a.ts));
            if (idx < 0) idx = points.length - 1;
            if (idx < 0) continue;
            const px = x.getPixelForValue(idx);
            if (px < chartArea.left || px > chartArea.right) continue;
            ctx.beginPath();
            ctx.moveTo(px, chartArea.top);
            ctx.lineTo(px, chartArea.bottom);
            ctx.stroke();
            ctx.fillStyle = "#e5c07b";
            ctx.fillText(a.label, px + 2, chartArea.top + 10);
          }
          ctx.restore();
        },
      },
    ],
  });
  // Click on the chart → add an annotation at that timestamp.
  ctx.onclick = async (evt) => {
    if (!timelineChart) return;
    const px = evt.x != null ? evt.x : evt.offsetX;
    const idx = Math.round(timelineChart.scales.x.getValueForPixel(px));
    if (idx == null || idx < 0 || idx >= points.length) return;
    const label = prompt("Мітка (напр. «відкрито вікно»):");
    if (!label || !label.trim()) return;
    await fetch("/api/annotations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ room, ts: points[idx][0], label: label.trim() }),
    });
    loadTimeline();
  };
}

// ---------- Heatmap (SVG days × hours, temperature or humidity) ----------
const tempColor = (v) => {
  if (v == null) return "#1a2129";
  const t = Math.max(10, Math.min(32, v)); // clamp 10–32 °C
  const f = (t - 10) / 22;
  const r = Math.round(40 + 200 * f), g = Math.round(120 - 60 * f), b = Math.round(200 - 150 * f);
  return `rgb(${r},${g},${b})`;
};
// Humidity scale: 25% (dry, sandy) → 40% comfortable → 70%+ (wet, blue).
const humColor = (v) => {
  if (v == null) return "#1a2129";
  const h = Math.max(20, Math.min(90, v));
  if (h <= 40) { const f = (h - 20) / 20; return `rgb(${Math.round(220 - 60 * f)},${Math.round(180 - 30 * f)},${Math.round(120 + 40 * f)})`; }
  const f = Math.min(1, (h - 40) / 40);
  return `rgb(${Math.round(160 - 110 * f)},${Math.round(150 + 30 * f)},${Math.round(160 + 95 * f)})`;
};

async function loadHeatmap() {
  const room = $("#hm-room").value, metric = $("#hm-metric").value, days = $("#hm-days").value;
  const data = await api(`/api/heatmap?room=${encodeURIComponent(room)}&metric=${metric}&days=${days}`);
  const cell = 14, labelW = 62;
  const color = metric === "humidity" ? humColor : tempColor;
  const unit = metric === "humidity" ? "%" : "°C";
  const w = labelW + 24 * cell, h = 20 + data.days.length * cell;
  let svg = `<svg width="${w}" height="${h}" xmlns="http://www.w3.org/2000/svg">`;
  data.hours.forEach((hr) => { svg += `<text x="${labelW + hr * cell + 3}" y="12" font-size="9" fill="#7a8a99">${hr}</text>`; });
  data.days.forEach((d, i) => {
    const y = 18 + i * cell;
    svg += `<text x="0" y="${y + 11}" font-size="9" fill="#7a8a99">${d}</text>`;
    data.values[i].forEach((v, hr) => {
      svg += `<rect x="${labelW + hr * cell}" y="${y}" width="${cell - 1}" height="${cell - 1}" fill="${color(v)}"><title>${d} ${hr}:00 — ${v ?? "немає даних"}${unit}</title></rect>`;
    });
  });
  svg += "</svg>";
  $("#heatmap").innerHTML = svg;
  const legend = metric === "humidity"
    ? `Сухо <span style="display:inline-block;width:60px;height:10px;background:linear-gradient(to right, rgb(220,180,120), rgb(50,180,255))"></span> Вологo · ${data.days.length} днів`
    : `Холодно <span style="display:inline-block;width:60px;height:10px;background:linear-gradient(to right, rgb(40,120,200), rgb(240,60,50))"></span> Спекотно · ${data.days.length} днів`;
  $("#hm-legend").innerHTML = legend;
}

// ---------- Seasons ----------
async function loadSeasons() {
  const room = $("#se-room").value, month = $("#se-month").value;
  const data = await api(`/api/seasons?room=${encodeURIComponent(room)}&month=${month}`);
  const years = Object.keys(data.by_year);
  const ctx = $("#seasons-chart");
  if (seasonsChart) seasonsChart.destroy();
  seasonsChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: years,
      datasets: [{ label: `Середня ${metricName(data.metric)}, ${monthName(month)}`, data: years.map((y) => data.by_year[y]), backgroundColor: "#4ecdc4" }],
    },
    options: { plugins: { legend: { labels: { color: themeColors().fg } } }, scales: { y: { grid: { color: themeColors().grid } }, x: { grid: { display: false } } } },
  });
}

const metricName = (m) => ({temperature: "температура", humidity: "вологість", co2: "CO₂", voc: "VOC"}[m] || m);
const monthName = (m) => ["січень","лютий","березень","квітень","травень","червень","липень","серпень","вересень","жовтень","листопад","грудень"][m - 1];

// ---------- Energy (kWh + cost) ----------
let energyChart = null;

async function loadEnergy() {
  const room = $("#en-room").value, days = $("#en-days").value;
  const price = parseFloat($("#en-price").value) || 0;
  const data = await api(`/api/energy?room=${encodeURIComponent(room)}&days=${days}&price=${price}`);
  $("#energy-total").textContent =
    `Всього: ${data.total_kwh} kWh · ≈ ${data.cost} (за ${data.price}/kWh) · ${room}, ${days} дн.`;
  const labels = data.daily.map(([d]) => d.slice(5)); // MM-DD
  const ctx = $("#energy-chart");
  if (energyChart) energyChart.destroy();
  energyChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ label: `kWh/день · ${room}`, data: data.daily.map(([, v]) => v), backgroundColor: "#e5c07b" }],
    },
    options: { plugins: { legend: { labels: { color: themeColors().fg } } }, scales: { y: { beginAtZero: true, grid: { color: themeColors().grid } }, x: { grid: { display: false }, ticks: { maxTicksLimit: 14 } } } },
  });
}

// ---------- Tabs & wiring ----------
document.querySelectorAll("nav button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("nav button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    btn.classList.add("active");
    $(`#view-${btn.dataset.view}`).classList.add("active");
    const loaders = { rooms: loadRooms, timeline: loadTimeline, heatmap: loadHeatmap, seasons: loadSeasons, energy: loadEnergy };
    loaders[btn.dataset.view]();
  });
});
["#tl-room", "#tl-metric", "#tl-days"].forEach((s) => $(s).addEventListener("change", loadTimeline));
["#hm-room", "#hm-metric", "#hm-days"].forEach((s) => $(s).addEventListener("change", loadHeatmap));
["#se-room", "#se-month"].forEach((s) => $(s).addEventListener("change", loadSeasons));
["#en-room", "#en-days"].forEach((s) => $(s).addEventListener("change", loadEnergy));
$("#en-price").addEventListener("change", () => {
  localStorage.setItem("cc-energy-price", $("#en-price").value);
  loadEnergy();
});
$("#en-price").value = localStorage.getItem("cc-energy-price") ?? "7.5";

$("#se-month").innerHTML = Array.from({ length: 12 }, (_, i) => `<option value="${i + 1}">${monthName(i + 1)}</option>`).join("");

// ---------- Theme toggle (dark/light, persisted in localStorage) ----------
function applyTheme(t) {
  document.body.classList.toggle("light", t === "light");
  const btn = $("#theme-toggle");
  if (btn) btn.textContent = t === "light" ? "🌙" : "☀️";
  localStorage.setItem("cc-theme", t);
}

$("#theme-toggle").addEventListener("click", () => {
  const next = document.body.classList.contains("light") ? "dark" : "light";
  applyTheme(next);
  // re-render the active view so Chart.js picks up the new colors
  const active = document.querySelector("nav button.active");
  if (active) ({ rooms: loadRooms, timeline: loadTimeline, heatmap: loadHeatmap, seasons: loadSeasons, energy: loadEnergy })[active.dataset.view]?.();
});
applyTheme(localStorage.getItem("cc-theme") || "dark");

loadRooms();

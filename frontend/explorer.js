// Runs the agent's playbooks in the browser over the same JSON that gets
// indexed into Elasticsearch. There's no LLM here, so each panel shows the
// tool calls the real agent makes for that question.
(() => {
  "use strict";

  const FILES = ["products", "product_history", "shrinkflation_alerts", "categories"];
  const STOP = new Set(
    ("has have my the a an of is did does gotten get got smaller shrunk shrink bag box pack " +
      "check these show me all from what are which worst this year with it any how much").split(" "),
  );
  const sev = (level) => `<span class="sev-${level}">${level}</span>`;
  const TIPS = {
    high: "Compare the shelf tag's unit price (per oz / per count), not the sticker price. Also check the store brand, which often kept the old size.",
    medium: "Buy by unit price. Larger packs and store brands frequently beat the shrunk name-brand pack.",
    low: "Small cut, but it compounds: check the unit price on the shelf tag before restocking.",
    none: "No size cut on record. Keep an eye on the unit price, since size cuts are rarely announced.",
  };

  const $ = (sel, root = document) => root.querySelector(sel);
  const esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const money = (n) => `$${n.toFixed(2)}`;
  const ppu = (n, unit) => `$${n.toFixed(3)}/${unit}`;
  const pct = (n) => `${n > 0 ? "+" : ""}${n.toFixed(1)}%`;
  const avg = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
  const verifiedBadge = (a) =>
    a.verified ? `<span class="badge ok">Verified · ${esc(a.source)}</span>`
               : `<span class="badge warn">Unverified · ${esc(a.source)}</span>`;

  let DB = null;

  // Approximates multi_match(name^3, brand^2, description, fuzziness AUTO).
  const norm = (s) => s.toLowerCase().replace(/['’&]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
  const words = (s) => norm(s).split(" ").filter(Boolean);

  function lev(a, b) {
    const dp = Array.from({ length: b.length + 1 }, (_, i) => i);
    for (let i = 1; i <= a.length; i++) {
      let prev = dp[0];
      dp[0] = i;
      for (let j = 1; j <= b.length; j++) {
        const tmp = dp[j];
        dp[j] = Math.min(dp[j] + 1, dp[j - 1] + 1, prev + (a[i - 1] === b[j - 1] ? 0 : 1));
        prev = tmp;
      }
    }
    return dp[b.length];
  }

  function tokenHits(token, fieldWords) {
    const fuzz = token.length <= 2 ? 0 : token.length <= 5 ? 1 : 2; // Elasticsearch "AUTO"
    return fieldWords.some((w) => w.startsWith(token) || lev(token, w) <= fuzz);
  }

  function search(query, limit = 5) {
    const tokens = words(query).filter((t) => !STOP.has(t));
    if (!tokens.length) return [];
    const ranked = DB.products
      .map((p) => {
        const fields = [[words(p.name), 3], [words(p.brand), 2], [words(p.description), 1]];
        let score = 0;
        for (const t of tokens) score += Math.max(0, ...fields.map(([fw, wt]) => (tokenHits(t, fw) ? wt : 0)));
        return { p, score };
      })
      .filter((r) => r.score >= Math.max(2, tokens.length * 1.5))
      .sort((a, b) => b.score - a.score);
    const best = ranked.length ? ranked[0].score : 0;
    return ranked.filter((r) => r.score >= best * 0.7).slice(0, limit).map((r) => r.p);
  }

  const historyOf = (id) => DB.product_history.filter((h) => h.product_id === id)
    .sort((a, b) => a.record_date.localeCompare(b.record_date));
  const alertOf = (id) => DB.shrinkflation_alerts.find((a) => a.product_id === id);
  const agentBox = (code) =>
    `<details class="agent"><summary>What the agent runs for this</summary><pre>${esc(code.trim())}</pre></details>`;

  // Price per unit over time, as an SVG step line.
  function ppuChart(hist, alert) {
    const W = 640, H = 210, L = 92, R = 16, T = 18, B = 30;
    const t = (d) => new Date(d).getTime();
    const xs = hist.map((h) => t(h.record_date)), ys = hist.map((h) => h.price_per_unit);
    const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
    const pad = (Math.max(...ys) - Math.min(...ys)) * 0.25 || Math.max(...ys) * 0.05;
    const [y0, y1] = [Math.min(...ys) - pad, Math.max(...ys) + pad];
    const X = (v) => L + ((v - x0) / (x1 - x0 || 1)) * (W - L - R);
    const Y = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
    let d = `M${X(xs[0])},${Y(ys[0])}`;
    for (let i = 1; i < xs.length; i++) d += ` H${X(xs[i])} V${Y(ys[i])}`;
    const unit = hist[0].size_unit;
    const dots = hist.map((h, i) => {
      const cut = alert && h.record_date === alert.date_changed;
      return `<circle cx="${X(xs[i])}" cy="${Y(ys[i])}" r="${cut ? 6 : 4}" class="${cut ? "cut" : "pt"}">
        <title>${esc(h.record_date)}: ${h.size} ${esc(unit)} @ ${money(h.price)} = ${ppu(h.price_per_unit, unit)}</title></circle>`;
    }).join("");
    // Label each record's year under its point (records are about a year apart).
    const xl = hist.map((h, i) => `<text x="${X(xs[i])}" y="${H - 8}">${h.record_date.slice(0, 4)}</text>`).join("");
    const cutHist = alert && hist.find((h) => h.record_date === alert.date_changed);
    const cutLabel = cutHist
      ? `<text x="${X(t(cutHist.record_date))}" y="${Y(cutHist.price_per_unit) - 12}" class="cutlbl">size cut</text>` : "";
    return `<svg viewBox="0 0 ${W} ${H}" class="chart" role="img" aria-label="Price per ${esc(unit)} over time">
      <text x="${L - 8}" y="${Y(y1 - pad) + 4}" class="yl">${ppu(y1 - pad, unit)}</text>
      <text x="${L - 8}" y="${Y(y0 + pad) + 4}" class="yl">${ppu(y0 + pad, unit)}</text>
      <line x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}" class="base"/>
      <path d="${d}" class="line"/>${dots}${xl}${cutLabel}</svg>`;
  }

  // Playbook 1: product lookup
  function renderProduct(p, others = []) {
    const hist = historyOf(p.product_id);
    const a = alertOf(p.product_id);
    const unit = p.current_size_unit;
    let findings;
    if (a) {
      const oldPpu = a.old_price / a.old_size, newPpu = a.new_price / a.new_size;
      findings = `
        <div class="verdict bad">Shrinkflation, ${esc(a.severity)} severity</div>
        <dl class="facts">
          <dt>Size change</dt><dd><s>${a.old_size} ${esc(unit)}</s> → <b>${a.new_size} ${esc(unit)}</b> (−${a.shrinkage_pct.toFixed(1)}%) on ${esc(a.date_changed)}</dd>
          <dt>Price impact</dt><dd>${money(a.old_price)} → ${money(a.new_price)} sticker · ${ppu(oldPpu, unit)} → ${ppu(newPpu, unit)}</dd>
          <dt>Effective price increase</dt><dd class="big">${pct(a.effective_price_increase_pct)}</dd>
          <dt>Evidence</dt><dd>${verifiedBadge(a)}</dd>
        </dl>
        <p class="tip">${TIPS[a.severity]}</p>`;
    } else {
      const first = hist[0], last = hist[hist.length - 1];
      const drift = ((last.price_per_unit - first.price_per_unit) / first.price_per_unit) * 100;
      findings = `
        <div class="verdict good">No size change on record</div>
        <dl class="facts">
          <dt>Size</dt><dd>${p.current_size} ${esc(unit)} since ${esc(first.record_date)}</dd>
          <dt>Price-per-unit drift</dt><dd>${ppu(first.price_per_unit, unit)} → ${ppu(last.price_per_unit, unit)} (${pct(drift)}), an ordinary price change with no size cut</dd>
        </dl>
        <p class="tip">${TIPS.none}</p>`;
    }
    const alsoMatched = others.length
      ? `<p class="also">Also matched: ${others.map((o) => `<button class="link" data-pid="${esc(o.product_id)}">${esc(o.name)}</button>`).join(", ")}</p>` : "";
    return `
      <article class="report">
        <header><h4>${esc(p.name)}</h4><span class="meta">${esc(p.brand)}, ${esc(p.category)}, ${esc(p.retailer)}</span></header>
        ${findings}
        ${ppuChart(hist, a)}
        <p class="next">Next check: <button class="link" data-brand="${esc(p.brand)}">all ${esc(p.brand)} products</button></p>
        ${alsoMatched}
      </article>
      ${agentBox(`
search  products  {"multi_match": {"query": "…", "fields": ["name^3","brand^2","description"], "fuzziness": "AUTO"}}
esql    FROM product_history | WHERE product_id == "${p.product_id}"
        | EVAL ppu = price / size | SORT record_date ASC
search  shrinkflation_alerts  {"term": {"product_id": "${p.product_id}"}}`)}`;
  }

  function lookup(query) {
    const hits = search(query);
    $("#out-lookup").innerHTML = hits.length
      ? renderProduct(hits[0], hits.slice(1))
      : `<p class="empty">I don't have data on “${esc(query)}” yet. Try a related brand or category, or pick one of the examples.</p>`;
  }

  // Playbook 2: brand investigation
  function renderBrand(brand) {
    const prods = DB.products.filter((p) => p.brand === brand);
    const alerts = DB.shrinkflation_alerts.filter((a) => a.brand === brand)
      .sort((a, b) => b.shrinkage_pct - a.shrinkage_pct);
    const rows = alerts.map((a) => `<tr><td>${esc(a.product_name)}</td><td>${a.old_size} → ${a.new_size} ${esc(a.size_unit)}</td>
      <td class="num">−${a.shrinkage_pct.toFixed(1)}%</td><td class="num">${pct(a.effective_price_increase_pct)}</td><td>${sev(a.severity)}</td><td>${verifiedBadge(a)}</td></tr>`).join("");
    $("#out-brand").innerHTML = `
      <div class="kpis">
        <div><b>${prods.length}</b><span>products tracked</span></div>
        <div><b>${alerts.length}</b><span>shrunk</span></div>
        <div><b>${alerts.length ? "−" + avg(alerts.map((a) => a.shrinkage_pct)).toFixed(1) + "%" : "—"}</b><span>avg shrinkage</span></div>
        <div><b>${alerts.length ? pct(avg(alerts.map((a) => a.effective_price_increase_pct))) : "—"}</b><span>avg hidden increase</span></div>
      </div>
      ${alerts.length ? `<div class="scroll"><table><thead><tr><th>Product</th><th>Size</th><th>Shrink</th><th>Hidden increase</th><th>Severity</th><th>Evidence</th></tr></thead><tbody>${rows}</tbody></table></div>`
                      : `<p class="empty">No size cuts on record for ${esc(brand)}.</p>`}
      ${agentBox(`
esql  FROM shrinkflation_alerts | WHERE brand == "${brand}"
      | STATS products = COUNT(*), avg_shrink = AVG(shrinkage_pct),
              avg_increase = AVG(effective_price_increase_pct) BY brand`)}`;
  }

  // Playbook 3: category analysis, verified events only
  function renderCategories(selected) {
    const verified = DB.shrinkflation_alerts.filter((a) => a.verified);
    const groups = {};
    for (const a of verified) (groups[a.category] ||= []).push(a);
    const ranking = Object.entries(groups)
      .map(([cat, alerts]) => ({ cat, alerts, avg: avg(alerts.map((a) => a.shrinkage_pct)), worst: Math.max(...alerts.map((a) => a.shrinkage_pct)) }))
      .sort((a, b) => b.avg - a.avg);
    const pick = ranking.find((r) => r.cat === selected) || ranking[0];
    const maxAvg = ranking[0].avg;
    const rows = ranking.map((r) => `<tr class="${r === pick ? "sel" : ""}"><td><button class="link" data-cat="${esc(r.cat)}">${esc(r.cat)}</button></td>
      <td><span class="bar" style="--w:${(r.avg / maxAvg) * 100}%"></span> −${r.avg.toFixed(1)}%</td><td class="num">${r.alerts.length}</td><td class="num">−${r.worst.toFixed(1)}%</td></tr>`).join("");
    const top = [...pick.alerts].sort((a, b) => b.shrinkage_pct - a.shrinkage_pct).slice(0, 3)
      .map((a) => `<li><b>${esc(a.product_name)}</b>: ${a.old_size} → ${a.new_size} ${esc(a.size_unit)} (−${a.shrinkage_pct.toFixed(1)}%, ${pct(a.effective_price_increase_pct)} per unit)</li>`).join("");
    $("#out-category").innerHTML = `
      <div class="scroll"><table><thead><tr><th>Category</th><th>Avg shrinkage</th><th>Events</th><th>Worst</th></tr></thead><tbody>${rows}</tbody></table></div>
      <h5>Worst offenders · ${esc(pick.cat)}</h5><ol class="offenders">${top}</ol>
      ${agentBox(`
esql  FROM shrinkflation_alerts | WHERE verified == true
      | STATS avg_shrinkage = AVG(shrinkage_pct), events = COUNT(*),
              worst = MAX(shrinkage_pct) BY category
      | SORT avg_shrinkage DESC`)}`;
  }

  // Playbook 4: shopping list audit
  function renderList(text) {
    const items = text.split(/[,\n]/).map((s) => s.trim()).filter(Boolean).slice(0, 20);
    let total = 0, shrunk = 0;
    const rows = items.map((item) => {
      const p = search(item, 1)[0];
      if (!p) return `<tr><td>${esc(item)}</td><td colspan="4" class="dim">no data yet</td></tr>`;
      const a = alertOf(p.product_id);
      if (!a) return `<tr><td>${esc(item)}</td><td>${esc(p.name)}</td><td>no change</td><td class="num">—</td><td class="num">$0.00</td></tr>`;
      // Extra paid per purchase today vs. buying the same amount at the pre-shrink unit price.
      const extra = a.new_price - (a.old_price / a.old_size) * a.new_size;
      total += extra;
      shrunk++;
      return `<tr><td>${esc(item)}</td><td>${esc(p.name)}</td><td>−${a.shrinkage_pct.toFixed(1)}% · ${sev(a.severity)}</td>
        <td class="num">${pct(a.effective_price_increase_pct)}</td><td class="num">${money(extra)}</td></tr>`;
    }).join("");
    $("#out-list").innerHTML = `
      <div class="scroll"><table><thead><tr><th>You typed</th><th>Matched</th><th>Shrank?</th><th>Hidden increase</th><th>Extra / purchase</th></tr></thead>
      <tbody>${rows}</tbody><tfoot><tr><td colspan="4">${shrunk} of ${items.length} items shrank · hidden cost per shopping trip</td><td class="num"><b>${money(total)}</b></td></tr></tfoot></table></div>
      <p class="fine">“Extra / purchase” = today's price minus what the same amount cost at the pre-shrink unit price.</p>
      ${agentBox("for each item: playbook 1 (search → esql history → search alerts), then sum the hidden cost")}`;
  }

  // Playbook 5: trend dashboard
  function renderTrends() {
    const verified = DB.shrinkflation_alerts.filter((a) => a.verified);
    const top = [...verified].sort((a, b) => b.shrinkage_pct - a.shrinkage_pct).slice(0, 10);
    const byYear = {};
    for (const a of verified) (byYear[a.date_changed.slice(0, 4)] ||= []).push(a.shrinkage_pct);
    const years = Object.keys(byYear).sort();
    const maxN = Math.max(...years.map((y) => byYear[y].length));
    const bars = years.map((y) => `<div class="yr"><span class="col" style="--h:${(byYear[y].length / maxN) * 100}%"><em>${byYear[y].length}</em></span>
      <b>${y}</b><small>avg −${avg(byYear[y]).toFixed(1)}%</small></div>`).join("");
    const rows = top.map((a, i) => `<tr><td class="num">${i + 1}</td><td>${esc(a.product_name)}</td><td>${esc(a.brand)}</td>
      <td class="num">−${a.shrinkage_pct.toFixed(1)}%</td><td class="num">${pct(a.effective_price_increase_pct)}</td><td>${esc(a.date_changed.slice(0, 7))}</td></tr>`).join("");
    $("#out-trends").innerHTML = `
      <h5>Verified size cuts per year</h5><div class="years">${bars}</div>
      <h5>Top 10 verified events</h5>
      <div class="scroll"><table><thead><tr><th>#</th><th>Product</th><th>Brand</th><th>Shrink</th><th>Hidden increase</th><th>When</th></tr></thead><tbody>${rows}</tbody></table></div>
      ${agentBox(`
esql  FROM shrinkflation_alerts | WHERE verified == true
      | EVAL year = DATE_EXTRACT("year", date_changed)
      | STATS events = COUNT(*), avg_shrink = AVG(shrinkage_pct) BY year | SORT year ASC`)}`;
  }

  function showTab(name) {
    document.querySelectorAll("[role=tab]").forEach((t) => t.setAttribute("aria-selected", t.dataset.tab === name));
    document.querySelectorAll("[role=tabpanel]").forEach((p) => (p.hidden = p.id !== `panel-${name}`));
  }

  function selectBrand(brand) {
    $("#brand-select").value = brand;
    renderBrand(brand);
    showTab("brand");
  }

  function init() {
    const brands = [...new Set(DB.products.map((p) => p.brand))].sort();
    $("#brand-select").innerHTML = brands.map((b) => `<option>${esc(b)}</option>`).join("");
    $("#stat-line").textContent =
      `${DB.products.length} products, ${DB.product_history.length} history records, ` +
      `${DB.shrinkflation_alerts.length} documented size cuts, ${DB.categories.length} categories`;

    $("#lookup-form").addEventListener("submit", (e) => { e.preventDefault(); lookup($("#lookup-q").value); });
    $("#list-form").addEventListener("submit", (e) => { e.preventDefault(); renderList($("#list-q").value); });
    $("#brand-select").addEventListener("change", (e) => renderBrand(e.target.value));
    document.querySelectorAll("[role=tab]").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
    document.querySelectorAll(".chip").forEach((c) =>
      c.addEventListener("click", () => { $("#lookup-q").value = c.textContent; lookup(c.textContent); }));

    $("#explorer").addEventListener("click", (e) => {
      const b = e.target.closest("button.link");
      if (!b) return;
      if (b.dataset.brand) selectBrand(b.dataset.brand);
      else if (b.dataset.cat) renderCategories(b.dataset.cat);
      else if (b.dataset.pid) $("#out-lookup").innerHTML = renderProduct(DB.products.find((p) => p.product_id === b.dataset.pid));
    });

    lookup($("#lookup-q").value);
    renderBrand("Frito-Lay");
    $("#brand-select").value = "Frito-Lay";
    renderCategories();
    renderList($("#list-q").value);
    renderTrends();
  }

  Promise.all(FILES.map((f) => fetch(`data/${f}.json`).then((r) => {
    if (!r.ok) throw new Error(`${f}: HTTP ${r.status}`);
    return r.json();
  })))
    .then((sets) => { DB = Object.fromEntries(FILES.map((f, i) => [f, sets[i]])); init(); })
    .catch((err) => {
      $("#explorer-status").innerHTML =
        `Couldn't load the dataset (${esc(err.message)}). Serve the site over HTTP, e.g. <code>make serve</code>.`;
    });
})();

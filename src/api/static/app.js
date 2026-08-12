const LIMIT = 20;

const state = {
  offset: 0,
  total: 0,
  loading: false,
};

const els = {
  list: document.getElementById("list"),
  loadMore: document.getElementById("load-more"),
  status: document.getElementById("status"),
  courtCode: document.getElementById("court_code"),
  propType: document.getElementById("prop_type"),
  detail: document.getElementById("detail"),
  detailBody: document.getElementById("detail-body"),
  detailClose: document.getElementById("detail-close"),
};

function qs(params) {
  const usp = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== "" && value !== null && value !== undefined) {
      usp.set(key, value);
    }
  }
  return usp.toString();
}

function fmtMoney(n) {
  if (n === null || n === undefined) return "—";
  return "NT$ " + Number(n).toLocaleString("en-US");
}

function fmtArea(n) {
  if (n === null || n === undefined) return "—";
  return `${Number(n).toLocaleString("en-US")} ping`;
}

function fmtDate(d) {
  if (!d) return "—";
  return d;
}

function ynBadge(label, value) {
  const span = document.createElement("span");
  span.className = "badge" + (value === "Y" ? " good" : value === "N" ? " bad" : "");
  span.textContent = value ? `${label}: ${value}` : `${label}: ?`;
  return span;
}

function currentFilters() {
  return {
    status: els.status.value,
    court_code: els.courtCode.value,
    prop_type: els.propType.value,
  };
}

async function loadCourts() {
  try {
    const res = await fetch("/api/courts");
    if (!res.ok) return;
    const courts = await res.json();
    for (const c of courts) {
      const opt = document.createElement("option");
      opt.value = c.code;
      opt.textContent = `${c.code} — ${c.name}`;
      els.courtCode.appendChild(opt);
    }
  } catch (err) {
    console.warn("Could not load courts", err);
  }
}

function renderCard(a) {
  const card = document.createElement("article");
  card.className = "card";
  card.addEventListener("click", () => openDetail(a.id));

  const top = document.createElement("div");
  top.className = "card-top";
  const court = document.createElement("span");
  court.className = "card-court";
  court.textContent = `${a.court_code} · ${a.county_name || ""} ${a.district || ""}`.trim();
  const dateEl = document.createElement("span");
  dateEl.className = "card-date";
  dateEl.textContent = fmtDate(a.auction_date);
  top.append(court, dateEl);

  const addr = document.createElement("p");
  addr.className = "card-address";
  addr.textContent = a.address || "(no address on file)";

  const bottom = document.createElement("div");
  bottom.className = "card-bottom";

  const price = document.createElement("div");
  price.className = "card-price";
  const label = document.createElement("span");
  label.className = "label";
  const isHistorical = a.sale_type === 5;
  label.textContent = isHistorical ? "Hammer" : "Reserve";
  price.appendChild(label);
  price.appendChild(document.createTextNode(
    fmtMoney(isHistorical ? a.hammer_price : a.reserve_price)
  ));

  const badges = document.createElement("div");
  badges.className = "badges";
  badges.appendChild(ynBadge("Delivery", a.delivery_yn));
  badges.appendChild(ynBadge("Vacant", a.vacant_yn));

  bottom.append(price, badges);

  card.append(top, addr, bottom);
  return card;
}

async function loadAuctions(reset) {
  if (state.loading) return;
  state.loading = true;

  if (reset) {
    state.offset = 0;
    els.list.innerHTML = "";
  }

  const params = { ...currentFilters(), limit: LIMIT, offset: state.offset };

  try {
    const res = await fetch(`/api/auctions?${qs(params)}`);
    if (!res.ok) throw new Error(`API returned ${res.status}`);
    const data = await res.json();

    state.total = data.total;
    state.offset += data.items.length;

    if (reset && data.items.length === 0) {
      const empty = document.createElement("p");
      empty.className = "empty";
      empty.textContent = "No auctions match these filters.";
      els.list.appendChild(empty);
    }

    for (const auction of data.items) {
      els.list.appendChild(renderCard(auction));
    }

    els.loadMore.hidden = state.offset >= state.total;
  } catch (err) {
    console.error(err);
    const error = document.createElement("p");
    error.className = "error";
    error.textContent = "Could not reach the API. Check you're on the same Wi-Fi as the server.";
    els.list.appendChild(error);
    els.loadMore.hidden = true;
  } finally {
    state.loading = false;
  }
}

function detailRow(k, v) {
  const row = document.createElement("div");
  row.className = "detail-row";
  const kEl = document.createElement("span");
  kEl.className = "k";
  kEl.textContent = k;
  const vEl = document.createElement("span");
  vEl.className = "v";
  vEl.textContent = v ?? "—";
  row.append(kEl, vEl);
  return row;
}

async function openDetail(id) {
  els.detail.hidden = false;
  els.detailBody.innerHTML = '<p class="loading">Loading…</p>';

  try {
    const res = await fetch(`/api/auctions/${id}`);
    if (!res.ok) throw new Error(`API returned ${res.status}`);
    const a = await res.json();

    els.detailBody.innerHTML = "";

    const h2 = document.createElement("h2");
    h2.textContent = a.address || `${a.court_name} case ${a.case_no}`;
    els.detailBody.appendChild(h2);

    const isHistorical = a.sale_type === 5;
    els.detailBody.append(
      detailRow("Court", a.court_name),
      detailRow("Case No.", `${a.case_year} ${a.case_type} ${a.case_no} (round ${a.auction_round})`),
      detailRow("Auction date", fmtDate(a.auction_date)),
      detailRow("Reserve price", fmtMoney(a.reserve_price)),
      ...(isHistorical ? [detailRow("Hammer price", fmtMoney(a.hammer_price))] : []),
      detailRow("Area", fmtArea(a.total_area_ping)),
      detailRow("Delivery (點交)", a.delivery_yn),
      detailRow("Vacant (空屋)", a.vacant_yn),
      detailRow("Remote bidding", a.remote_bid_yn),
    );

    if (a.detail && a.detail.pdf_url) {
      const link = document.createElement("a");
      link.href = a.detail.pdf_url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = "Open original auction notice (PDF)";
      link.style.display = "block";
      link.style.marginTop = "1rem";
      link.style.color = "#f59e0b";
      els.detailBody.appendChild(link);
    }

    const note = document.createElement("p");
    note.className = "detail-note";
    note.textContent =
      "Decision-support data only — not a formal appraisal or guaranteed valuation. Verify against the original court notice before bidding.";
    els.detailBody.appendChild(note);
  } catch (err) {
    console.error(err);
    els.detailBody.innerHTML = '<p class="error">Could not load this listing.</p>';
  }
}

function closeDetail() {
  els.detail.hidden = true;
}

els.status.addEventListener("change", () => loadAuctions(true));
els.courtCode.addEventListener("change", () => loadAuctions(true));
els.propType.addEventListener("change", () => loadAuctions(true));
els.loadMore.addEventListener("click", () => loadAuctions(false));
els.detailClose.addEventListener("click", closeDetail);
els.detail.addEventListener("click", (e) => {
  if (e.target === els.detail) closeDetail();
});

loadCourts();
loadAuctions(true);

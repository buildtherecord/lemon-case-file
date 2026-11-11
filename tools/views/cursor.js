(function (root) {
"use strict";
var MS = 86400000;
function days(a, b) { return Math.round((b - a) / MS); }
// One counting rule for a span: days after its start date, so its end date is day M of M. build_home.py counts the same way (span_days).
function spanTotal(s, e) { return days(s, e); }
function spanDay(s, t) { return days(s, t); }
function plural(n, w, many) { return n + " " + (n === 1 ? w : (many || w + "s")); }
// Cut at a word boundary and mark the cut. Never adds quotation marks.
function cutWords(s, n) {
  s = String(s).replace(/\s+/g, " ").replace(/^ | $/g, "");
  if (s.length <= n) { return s; }
  var c = s.slice(0, n).replace(/\s+\S*$/, "");
  return (c || s.slice(0, n)).replace(/[ ,;:\-–—]+$/, "") + " …";
}
var api = { days: days, spanTotal: spanTotal, spanDay: spanDay, plural: plural, cutWords: cutWords };
if (typeof module !== "undefined" && module.exports) { module.exports = api; }
if (typeof document === "undefined") { return; }

var sw = document.getElementById("sw"), raw = document.getElementById("swdata");
if (!sw || !raw) { return; }
var D = JSON.parse(raw.textContent), d0 = Date.parse(D.d0);
var scroller = sw.querySelector(".sw"), earlier = sw.querySelector(".earlier"), tip = document.getElementById("swtip"), strip = document.getElementById("swstrip");
var svgs = [].slice.call(sw.querySelectorAll("svg.sv"));
var lanes = {}, byId = {};
D.lanes.forEach(function (l) { lanes[l.id] = l; });
var F = D.facts.map(function (f) {
  return { id: f.id, t: Date.parse(f.d), e: f.e ? Date.parse(f.e) : null, l: f.l, tx: f.t, x: f.x, k: f.k, w: f.w, when: f.when, a: !!f.a };
}).sort(function (a, b) { return a.t - b.t; });
F.forEach(function (f) { byId[f.id] = f; });
var DAYF = F.filter(function (f) { return !f.a; });
var S = D.spans.map(function (s) { return { s: Date.parse(s.s), e: Date.parse(s.e), label: s.label, note: s.note }; });

function el(tag, cls, text) { var n = document.createElement(tag); if (cls) { n.className = cls; } if (text != null) { n.textContent = text; } return n; }
function fmt(t) { return new Date(t).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }); }
function line(cls) { var s = el("span", cls); for (var i = 1; i < arguments.length; i++) { var a = arguments[i]; s.appendChild(typeof a === "string" ? document.createTextNode(a) : a); } return s; }
function bold(t) { return el("b", null, t); }

// The marks: one per lane and day. Every width of the chart has the same marks, so a mark is known by the id of its first entry.
var meta = {}, els = svgs.map(function () { return {}; }), order = [];
svgs.forEach(function (svg, si) {
  [].forEach.call(svg.querySelectorAll("a.mk"), function (a) {
    var ids = a.getAttribute("data-ids").split(" "), key = ids[0];
    els[si][key] = a;
    if (!meta[key]) { meta[key] = { key: key, ids: ids, t: Date.parse(a.getAttribute("data-d")), n: order.push(key) }; }
  });
});
order = order.map(function (k) { return meta[k]; }).sort(function (a, b) { return a.t - b.t || a.n - b.n; });
order.forEach(function (m, i) { m.i = i; });

function active() { for (var i = 0; i < svgs.length; i++) { if (svgs[i].getClientRects().length) { return i; } } return -1; }
function geo() {
  var si = active();
  if (si < 0) { return null; }
  var svg = svgs[si], v = D.v[svg.getAttribute("data-v")], r = svg.getBoundingClientRect();
  return { si: si, v: v, r: r, k: r.width / v.W };
}
function tAt(g, cx) { var x = (cx - g.r.left) / g.k; return d0 + Math.round((x - g.v.X0) / (g.v.X1 - g.v.X0) * D.span) * MS; }
function inRange(g, cx) { var x = (cx - g.r.left) / g.k; return x >= g.v.X0 - 8 && x <= g.v.X1 + 8; }
function laneAt(g, cy) { var y = (cy - g.r.top) / g.k, L = null; g.v.lanes.forEach(function (l) { if (y >= l.y0 && y <= l.y1) { L = lanes[l.id]; } }); return L; }
function laneOf(m) { return lanes[byId[m.ids[0]].l] || null; }
function nearest(g, cx, cy, radius) {
  var best = null, bd = radius + 1;
  Object.keys(els[g.si]).forEach(function (key) {
    var b = els[g.si][key].getBoundingClientRect();
    var dx = Math.max(b.left - cx, 0, cx - b.right), dy = Math.max(b.top - cy, 0, cy - b.bottom), d = Math.sqrt(dx * dx + dy * dy);
    if (d < bd) { bd = d; best = meta[key]; }
  });
  return best;
}

// What the reading says about a date. Only counts and dates. The words of an entry are shown as written on the page, never inside quotation marks.
function pieces(t, lane, hasMark) {
  var out = [], same = DAYF.filter(function (f) { return f.t === t; }), running = DAYF.filter(function (f) { return f.t < t && f.e && f.e >= t; }), p = null, n = null, i;
  for (i = 0; i < DAYF.length; i++) { if (DAYF[i].t < t) { p = DAYF[i]; } else if (DAYF[i].t > t) { n = DAYF[i]; break; } }
  if (same.length && !hasMark) {
    out.push(line("q", bold("On this date: "), same[0].tx + (same.length > 1 ? " (and " + plural(same.length - 1, "more entry", "more entries") + " on this date)" : "")));
  } else if (running.length) {
    out.push(line("q", bold("Within an entry that runs from " + fmt(running[0].t) + " to " + fmt(running[0].e) + ": "), running[0].tx));
  } else if (hasMark || (p && n)) {
    if (p) { out.push(line("q", plural(days(p.t, t), "day") + " after " + fmt(p.t) + ": " + p.tx)); }
    if (n) { out.push(line("q", plural(days(t, n.t), "day") + " before " + fmt(n.t) + ": " + n.tx)); }
  } else if (n) {
    out.push(line("q", "Before the first entry. The first is on " + fmt(n.t) + ": " + n.tx));
  } else if (p) {
    out.push(line("q", plural(days(p.t, t), "day") + " after the latest entry, dated " + fmt(p.t) + ": " + p.tx));
  }
  if (lane) {
    var LF = DAYF.filter(function (f) { return f.l === lane.id; }), a = null, c = null, covers = null, onday = null, txt;
    LF.forEach(function (f) {
      var end = f.e || f.t;
      if (f.e && f.t <= t && f.e >= t) { covers = f; }
      else if (f.t === t) { onday = f; }
      else if (f.t < t && (!a || end > (a.e || a.t))) { a = f; }
      if (f.t > t && !c) { c = f; }
    });
    if (covers) { txt = "an entry here runs from " + fmt(covers.t) + " to " + fmt(covers.e); }
    else if (onday) { txt = hasMark ? "" : "an entry is dated this day"; }
    else if (a && c) {
      var gap = days(a.e || a.t, c.t);
      txt = gap > 60 ? "no entry for " + plural(gap, "day") + " (" + fmt(a.e || a.t) + " to " + fmt(c.t) + ")" : "the entries before and after are " + plural(gap, "day") + " apart";
    } else if (c) { txt = "no earlier entry; the first is on " + fmt(c.t); }
    else if (a) { txt = "no later entry since " + fmt(a.e || a.t); }
    else { txt = "no entries"; }
    if (txt) { out.push(line("st", bold(lane.label + ": "), txt)); }
  }
  var near = DAYF.filter(function (f) { return Math.abs(days(t, f.t)) <= 14; }).length;
  if (near) { out.push(line("st", plural(near, "entry", "entries") + " within four weeks (14 days either side)")); }
  S.forEach(function (sp) {
    if (t >= sp.s && t <= sp.e) { out.push(line("st", bold(sp.label), " — day " + spanDay(sp.s, t) + " of " + spanTotal(sp.s, sp.e) + "." + (sp.note ? " " + sp.note : ""))); }
  });
  return out;
}

// ----- cursor line, floating reading (mouse), reading strip (touch, keyboard) -----
var hoverT = null, pinned = null, ptype = "";
function drawCursor() {
  var t = hoverT != null ? hoverT : pinned ? pinned.t : null;
  svgs.forEach(function (svg) {
    var c = svg.querySelector(".cur"), v = D.v[svg.getAttribute("data-v")];
    if (!c) { return; }
    if (t == null) { c.style.display = "none"; return; }
    var x = v.X0 + days(d0, t) / D.span * (v.X1 - v.X0);
    c.setAttribute("x1", x); c.setAttribute("x2", x); c.style.display = "";
  });
}
function hideTip() { tip.hidden = true; hoverT = null; drawCursor(); }
function showTip(t, lane, m, cx, cy) {
  tip.textContent = "";
  tip.appendChild(bold(fmt(t)));
  if (m) { m.ids.slice(0, 3).forEach(function (id) { var f = byId[id]; tip.appendChild(line("q", bold(f.w + ": "), cutWords(f.x, 110))); }); }
  pieces(t, lane, !!m).forEach(function (p) { tip.appendChild(p); });
  tip.hidden = false;
  var wr = sw.getBoundingClientRect(), w = tip.offsetWidth, lx = cx - wr.left + 14;
  if (lx + w > wr.width - 6) { lx = cx - wr.left - w - 14; }
  if (lx < 4) { lx = 4; }
  tip.style.left = lx + "px"; tip.style.top = Math.max(4, cy - wr.top + 16) + "px";
}
function button(act, text, label) { var b = el("button", null, text); b.type = "button"; b.setAttribute("data-act", act); if (label) { b.setAttribute("aria-label", label); } return b; }
// The reading is a live region (announced when it changes); the buttons beside it are not, so they are not read out again each time.
var rd = el("div", "rd"), acts = el("div", "acts");
rd.setAttribute("role", "status"); rd.setAttribute("aria-live", "polite"); rd.setAttribute("aria-atomic", "true");
strip.textContent = ""; strip.appendChild(rd); strip.appendChild(acts);
function fillStrip(t, lane, m) {
  rd.textContent = ""; acts.textContent = "";
  if (t == null) { rd.appendChild(el("p", "hint", D.hint)); return; }
  var many = m && m.ids.length > 1;
  var rh = el("div", "rh");
  rh.appendChild(bold(m ? (many ? plural(m.ids.length, "entry", "entries") + " on " + fmt(t) : byId[m.ids[0]].when) : fmt(t)));
  if (lane && m) { rh.appendChild(el("span", "d", lane.label)); }
  rd.appendChild(rh);
  if (m) {
    m.ids.forEach(function (id) {
      var f = byId[id], ent = el("p", "ent");
      ent.appendChild(el("span", "s s-" + f.k, f.w));
      ent.appendChild(document.createTextNode(" " + f.x + " "));
      if (many) { var a = el("a", "go", "Go to entry"); a.href = "#e-" + id; a.setAttribute("aria-label", "Go to entry: " + cutWords(f.x, 50)); ent.appendChild(el("br")); ent.appendChild(a); }
      rd.appendChild(ent);
    });
  }
  var ctx = el("div", "ctx");
  pieces(t, lane, !!m).forEach(function (p) { ctx.appendChild(p); });
  rd.appendChild(ctx);
  if (m && !many) { var go = el("a", "go", "Go to entry"); go.href = "#e-" + m.ids[0]; acts.appendChild(go); }
  if (m) { acts.appendChild(button("prev", "‹ Earlier entry")); acts.appendChild(button("next", "Later entry ›")); }
  if (pinned) { acts.appendChild(button("close", "Close")); }
}
function setSel(key) {
  var first = order.length ? order[0].key : null;
  svgs.forEach(function (svg) {
    [].forEach.call(svg.querySelectorAll("a.mk"), function (a) {
      var k = a.getAttribute("data-ids").split(" ")[0];
      a.classList.toggle("sel", k === key);
      a.setAttribute("tabindex", k === (key || first) ? "0" : "-1");
    });
  });
}
function pin(m, t, lane, focus) {
  pinned = { t: t, key: m ? m.key : null };
  hideTip(); setSel(m ? m.key : null); drawCursor(); fillStrip(t, lane, m);
  if (ptype === "touch" || ptype === "pen") { var sr = strip.getBoundingClientRect(); if (sr.bottom > window.innerHeight - 8 || sr.top < 0) { strip.scrollIntoView({ block: "nearest", behavior: "auto" }); } }
  if (m && focus) { var g = geo(); if (g && els[g.si][m.key]) { els[g.si][m.key].focus(); } }
}
function unpin() { if (!pinned) { return; } pinned = null; setSel(null); drawCursor(); fillStrip(null); }
function step(d) {
  var m = pinned && pinned.key ? meta[pinned.key] : null;
  var ni = m ? Math.max(0, Math.min(order.length - 1, m.i + d)) : (d > 0 ? 0 : order.length - 1);
  pin(order[ni], order[ni].t, laneOf(order[ni]), true);
}

svgs.forEach(function (svg) { svg.setAttribute("aria-describedby", "swhelp"); });
if (order.length) { setSel(null); }
fillStrip(null); strip.hidden = false;

sw.addEventListener("pointerdown", function (e) { ptype = e.pointerType; });
document.addEventListener("keydown", function (e) { ptype = "key"; if (e.key === "Escape") { hideTip(); unpin(); } }, true);
sw.addEventListener("pointermove", function (e) {
  if (e.pointerType !== "mouse") { return; }
  var g = geo();
  if (!g || !e.target.closest || !e.target.closest("svg.sv") || !inRange(g, e.clientX)) { hideTip(); return; }
  var m = nearest(g, e.clientX, e.clientY, 12), t = m ? m.t : tAt(g, e.clientX);
  hoverT = t; drawCursor(); showTip(t, m ? laneOf(m) : laneAt(g, e.clientY), m, e.clientX, e.clientY);
});
sw.addEventListener("pointerleave", function (e) { if (e.pointerType === "mouse") { hideTip(); } });
sw.addEventListener("click", function (e) {
  if (!e.target.closest || !e.target.closest("svg.sv")) { return; }
  var kind = e.pointerType || ptype, g = geo();
  if (kind === "key" || !g) { return; }
  var onMark = e.target.closest("a.mk");
  if (kind === "touch" || kind === "pen") {
    e.preventDefault();
    var m = nearest(g, e.clientX, e.clientY, 22);
    if (m) { pin(m, m.t, laneOf(m), false); } else if (inRange(g, e.clientX)) { pin(null, tAt(g, e.clientX), laneAt(g, e.clientY), false); } else { unpin(); }
    return;
  }
  if (onMark) { return; }
  var m2 = nearest(g, e.clientX, e.clientY, 12);
  if (m2) { els[g.si][m2.key].dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window })); }
});
sw.addEventListener("keydown", function (e) {
  var a = e.target.closest && e.target.closest("a.mk");
  if (!a) { return; }
  var d = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
  if (d) { e.preventDefault(); step(d); }
  else if (e.key === "Home") { e.preventDefault(); pin(order[0], order[0].t, laneOf(order[0]), true); }
  else if (e.key === "End") { var z = order[order.length - 1]; e.preventDefault(); pin(z, z.t, laneOf(z), true); }
});
sw.addEventListener("focusin", function (e) {
  var a = e.target.closest && e.target.closest("a.mk");
  if (!a) { return; }
  var m = meta[a.getAttribute("data-ids").split(" ")[0]];
  if (!pinned || pinned.key !== m.key) { pin(m, m.t, laneOf(m), false); }
});
sw.addEventListener("focusout", function (e) { if (!e.relatedTarget || !sw.contains(e.relatedTarget)) { if (ptype === "key") { unpin(); } } });
strip.addEventListener("click", function (e) {
  var b = e.target.closest && e.target.closest("button[data-act]");
  if (!b) { return; }
  var act = b.getAttribute("data-act");
  if (act === "close") { unpin(); } else { step(act === "next" ? 1 : -1); }
});
document.addEventListener("pointerdown", function (e) { if (!sw.contains(e.target)) { hideTip(); unpin(); } });
window.addEventListener("scroll", function () { hideTip(); }, { passive: true });
if ("IntersectionObserver" in window) { new IntersectionObserver(function (en) { if (!en[0].isIntersecting) { hideTip(); unpin(); } }).observe(sw); }

// If the chart is ever wider than its box (a very narrow window, a large text size), open on the latest dates and say so.
var opened = false;
function checkScroll() {
  if (scroller.scrollWidth > scroller.clientWidth + 2) {
    if (!opened) { opened = true; scroller.scrollLeft = scroller.scrollWidth; }
    earlier.hidden = scroller.scrollLeft < 8;
  } else { earlier.hidden = true; }
}
scroller.addEventListener("scroll", checkScroll, { passive: true });
earlier.addEventListener("click", function () { scroller.scrollBy({ left: -Math.round(scroller.clientWidth * 0.8), behavior: "smooth" }); });
var rz = 0;
window.addEventListener("resize", function () { cancelAnimationFrame(rz); rz = requestAnimationFrame(function () { drawCursor(); checkScroll(); }); });
window.addEventListener("load", checkScroll);
checkScroll();
})(this);

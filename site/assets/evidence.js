// VeluneOS — Evidence Window interactions (progressive enhancement).
// 1. Selecting a stream row in the report excerpt shows that finding.
// 2. Window highlights are drawn once when they enter view (skipped for reduced motion).
(function () {
  "use strict";
  var doc = document.documentElement;
  doc.classList.add("js");

  var rows = document.querySelectorAll("#tracks button.trow");
  var what = document.getElementById("d-what");
  var when = document.getElementById("d-when");
  var ev = document.getElementById("d-ev");
  Array.prototype.forEach.call(rows, function (row) {
    row.addEventListener("click", function () {
      Array.prototype.forEach.call(rows, function (r) { r.setAttribute("aria-pressed", "false"); });
      row.setAttribute("aria-pressed", "true");
      if (what) what.textContent = row.getAttribute("data-what");
      if (when) when.textContent = row.getAttribute("data-when");
      if (ev) ev.textContent = row.getAttribute("data-ev");
    });
  });

  var reveal = document.querySelectorAll(".reveal");
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce || !("IntersectionObserver" in window)) {
    Array.prototype.forEach.call(reveal, function (el) { el.classList.add("on"); });
    return;
  }
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add("on"); io.unobserve(e.target); }
    });
  }, { threshold: 0.4 });
  Array.prototype.forEach.call(reveal, function (el) { io.observe(el); });
})();

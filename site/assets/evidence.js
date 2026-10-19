// VeluneOS — Evidence Window interactions (progressive enhancement).
// 1. Selecting a stream row in the report excerpt shows that finding.
(function () {
  "use strict";
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

})();

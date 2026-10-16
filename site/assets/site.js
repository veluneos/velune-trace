// VeluneOS site — Change Review request form.
// Builds a mailto: draft from the form fields. Nothing is stored or sent
// to any server by this page; the visitor's own email client sends it.
(function () {
  "use strict";

  var form = document.getElementById("review-form");
  if (!form) return;

  var status = document.getElementById("form-status");
  // The address is split so that Cloudflare email obfuscation, which
  // rewrites addresses it finds in the page, leaves it intact.
  var address =
    form.getAttribute("data-mail-user") +
    "@" +
    form.getAttribute("data-mail-domain");
  var subject = form.getAttribute("data-subject");
  var footer = form.getAttribute("data-footer") || "";
  var missingText = form.getAttribute("data-missing");
  var openingText = form.getAttribute("data-opening");
  var emptyText = form.getAttribute("data-empty") || "-";

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var missing = [];
    var lines = [subject, ""];

    Array.prototype.forEach.call(
      form.querySelectorAll("[data-label]"),
      function (field) {
        var label = field.getAttribute("data-label");
        var value;
        if (field.tagName === "FIELDSET") {
          var checked = field.querySelector("input:checked");
          value = checked ? checked.getAttribute("data-value") : "";
        } else {
          value = field.value.trim();
        }
        if (field.hasAttribute("data-required") && !value) {
          missing.push(label);
        }
        lines.push("[" + label + "]", value || emptyText, "");
      }
    );

    if (missing.length) {
      status.textContent = missingText + " " + missing.join(", ");
      status.className = "form-status error";
      return;
    }

    if (footer) lines.push(footer);

    var href =
      "mailto:" +
      address +
      "?subject=" +
      encodeURIComponent(subject) +
      "&body=" +
      encodeURIComponent(lines.join("\n"));

    status.textContent = openingText;
    status.className = "form-status";
    window.location.href = href;
  });
})();

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
  var invalidText = form.getAttribute("data-invalid");
  var fallbackText = form.getAttribute("data-fallback");
  var openingText = form.getAttribute("data-opening");
  var emptyText = form.getAttribute("data-empty") || "-";

  form.addEventListener("submit", function (event) {
    event.preventDefault();

    var missing = [];
    var invalid = [];
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
        var bad = false;
        if (field.hasAttribute("data-required") && !value) {
          missing.push(label);
          bad = true;
        } else if (field.type === "email" && value && !field.checkValidity()) {
          invalid.push(label);
          bad = true;
        }
        if (field.tagName !== "FIELDSET") {
          if (bad) field.setAttribute("aria-invalid", "true");
          else field.removeAttribute("aria-invalid");
        }
        lines.push("[" + label + "]", value || emptyText, "");
      }
    );

    if (missing.length || invalid.length) {
      var problems = [];
      if (missing.length) problems.push(missingText + " " + missing.join(", "));
      if (invalid.length) problems.push(invalidText + " " + invalid.join(", "));
      status.textContent = problems.join(" ");
      status.className = "form-status error";
      var first = form.querySelector("[aria-invalid='true']");
      if (first) first.focus();
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

    // Fallback for visitors without a mail client: show the address as text.
    status.textContent =
      openingText + (fallbackText ? " " + fallbackText + " " + address + "." : "");
    status.className = "form-status";
    window.location.href = href;
  });
})();

// Kredibel mocks: just enough behaviour to click through them like a prototype.
// Not app code: the React app implements the same interactions with real data (docs/11 §6).
(function () {
  "use strict";

  // Segmented controls: <button data-group="fw" data-value="IFRS"> shows every
  // [data-show-group="fw"][data-show-value="IFRS"] and hides the others in the same group.
  function select(group, value) {
    document.querySelectorAll('[data-group="' + group + '"]').forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.value === value));
    });
    document.querySelectorAll('[data-show-group="' + group + '"]').forEach(function (p) {
      p.hidden = p.dataset.showValue !== value;
    });
    document.querySelectorAll('[data-text-group="' + group + '"]').forEach(function (t) {
      var text = t.getAttribute("data-text-" + value.toLowerCase());
      if (text) t.textContent = text;
    });
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-group][data-value]");
    if (b) { e.preventDefault(); select(b.dataset.group, b.dataset.value); return; }

    // Radio cards (review candidates): pick one, rename the primary action.
    var c = e.target.closest(".candidate");
    if (c) {
      c.parentElement.querySelectorAll(".candidate").forEach(function (o) {
        o.classList.toggle("is-picked", o === c);
        o.setAttribute("aria-checked", String(o === c));
      });
      var target = document.querySelector("[data-picked-label]");
      if (target && c.dataset.label) target.lastChild.textContent = c.dataset.label;
      return;
    }

    // Selectable rows (labels table): open the side panel for the row.
    var r = e.target.closest("tr[data-row]");
    if (r && !e.target.closest("a, input, button")) {
      r.parentElement.querySelectorAll("tr[data-row]").forEach(function (o) { o.classList.toggle("is-selected", o === r); });
    }
  });

  // Escape closes the More sheet.
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && location.hash === "#more") history.back();
  });
})();

/* Postdiluvian — shared UI helpers. Loaded by index.html and editor.html.
   Adds a hover/focus "×" clear button to single-line text/search inputs.
   Auto-applies to input[type=search] and input[data-clear]; call
   window.PDClearable(inputEl) for inputs created after load. */
(function () {
  "use strict";

  var CLEARABLE_TYPES = ["text", "search", "url", "email", "tel", ""];

  function clearable(input) {
    if (!input || input.tagName !== "INPUT" || input.dataset.clearReady === "1") return;
    if (CLEARABLE_TYPES.indexOf(input.getAttribute("type") || "") < 0) return;
    if (input.readOnly || input.disabled) return;
    input.dataset.clearReady = "1";

    var wrap = document.createElement("span");
    wrap.className = "clearable";
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "clearx";
    btn.tabIndex = -1;
    btn.setAttribute("aria-label", "Clear");
    btn.textContent = "×";
    wrap.appendChild(btn);

    function sync() { wrap.classList.toggle("has-value", input.value !== ""); }
    input.addEventListener("input", sync);
    input.addEventListener("change", sync);
    // don't let the input blur before the click lands
    btn.addEventListener("mousedown", function (e) { e.preventDefault(); });
    btn.addEventListener("click", function (e) {
      e.preventDefault(); e.stopPropagation();
      input.value = "";
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.focus();
      sync();
    });
    sync();
  }

  window.PDClearable = clearable;

  function initAll() {
    document.querySelectorAll("input[type=search], input[data-clear]").forEach(clearable);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initAll);
  else initAll();
})();

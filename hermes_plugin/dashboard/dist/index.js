// Accounting tab for the Hermes dashboard. No build step: plain IIFE using the
// dashboard's Plugin SDK. Pages are rendered server-side (escaped by Jinja) and
// shown inside a shadow root so their styles never touch Hermes. The page
// refreshes itself every few seconds, so records your agent adds appear live.
(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  var React = SDK.React;
  var h = React.createElement;
  var useState = SDK.hooks.useState;
  var useEffect = SDK.hooks.useEffect;
  var useRef = SDK.hooks.useRef;

  var REFRESH_MS = 5000;
  var DROP = ["script", "iframe", "object", "embed", "link", "meta", "style", "base", "form"];

  // Defense in depth: the server already escapes every ledger value.
  function clean(html) {
    var doc = new DOMParser().parseFromString("<div>" + html + "</div>", "text/html");
    var root = doc.body.firstChild;
    DROP.forEach(function (tag) {
      root.querySelectorAll(tag).forEach(function (el) { el.remove(); });
    });
    root.querySelectorAll("*").forEach(function (el) {
      Array.prototype.slice.call(el.attributes).forEach(function (attr) {
        var name = attr.name.toLowerCase();
        var value = String(attr.value).trim().toLowerCase();
        if (name.indexOf("on") === 0 || ((name === "href" || name === "src") && value.indexOf("#") !== 0)) {
          el.removeAttribute(attr.name);
        }
      });
    });
    return root.innerHTML;
  }

  function clock(date) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  }

  function AccountingPage() {
    var host = useRef(null);
    var lastHtml = useRef("");
    var _v = useState({ view: "", filter: "" }), page = _v[0], setPage = _v[1];
    var _d = useState(false), demo = _d[0], setDemo = _d[1];
    var _e = useState(null), error = _e[0], setError = _e[1];
    var _u = useState(null), updated = _u[0], setUpdated = _u[1];
    var setPageRef = useRef(setPage);
    setPageRef.current = setPage;

    useEffect(function () {
      var cancelled = false;
      var timer = null;
      lastHtml.current = "";

      function load() {
        var url = "/api/plugins/accounting-starter/page?view=" + encodeURIComponent(page.view) +
          (page.filter ? "&filter=" + encodeURIComponent(page.filter) : "") + (demo ? "&demo=true" : "");
        return SDK.fetchJSON(url).then(function (data) {
          if (cancelled || !host.current) return;
          var shadow = host.current.shadowRoot || host.current.attachShadow({ mode: "open" });
          var html = "<style>" + data.css + "</style>" + clean(data.html);
          if (html !== lastHtml.current) {
            lastHtml.current = html;
            shadow.innerHTML = html;
          }
          if (!shadow.__accountingLinks) {
            shadow.__accountingLinks = true;
            shadow.addEventListener("click", function (event) {
              var link = event.target.closest && event.target.closest("a[data-view]");
              if (!link) return;
              event.preventDefault();
              setPageRef.current({ view: link.getAttribute("data-view") || "", filter: link.getAttribute("data-filter") || "" });
              if (host.current) host.current.scrollIntoView({ block: "start", behavior: "smooth" });
            });
          }
          setError(null);
          setUpdated(new Date());
        }).catch(function (err) {
          if (!cancelled) setError(String((err && err.message) || err));
        });
      }

      function tick() {
        if (cancelled) return;
        var work = document.hidden ? Promise.resolve() : load();
        work.then(function () { if (!cancelled) timer = setTimeout(tick, REFRESH_MS); });
      }

      tick();
      return function () { cancelled = true; if (timer) clearTimeout(timer); };
    }, [page.view, page.filter, demo]);

    function segment(label, active, onClick) {
      return h("button", {
        type: "button", onClick: onClick, "aria-pressed": active,
        className: "acct-seg" + (active ? " acct-seg-on" : "")
      }, label);
    }

    return h("div", { className: "acct-root" },
      h("div", { className: "acct-bar" },
        h("div", { className: "acct-segs", role: "group", "aria-label": "Which books" },
          segment("My books", !demo, function () { setDemo(false); }),
          segment("Demo data", demo, function () { setDemo(true); })
        ),
        h("span", { className: "acct-live" + (error ? " acct-live-off" : "") },
          h("span", { className: "acct-pulse", "aria-hidden": "true" }),
          error ? "Not updating" : updated ? "Live, updated " + clock(updated) : "Loading…")
      ),
      error ? h("p", { className: "acct-error" }, "Could not load the ledger: " + error) : null,
      h("div", { ref: host })
    );
  }

  window.__HERMES_PLUGINS__.register("accounting-starter", AccountingPage);
})();

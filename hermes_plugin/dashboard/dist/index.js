// Accounting tab for the Hermes dashboard. No build step: plain IIFE using the
// dashboard's Plugin SDK. The ledger pages are rendered server-side (escaped by
// Jinja) and shown inside a shadow root so their styles never touch Hermes.
(function () {
  "use strict";

  var SDK = window.__HERMES_PLUGIN_SDK__;
  var React = SDK.React;
  var h = React.createElement;
  var useState = SDK.hooks.useState;
  var useEffect = SDK.hooks.useEffect;
  var useRef = SDK.hooks.useRef;
  var Button = SDK.components.Button;

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

  function AccountingPage() {
    var host = useRef(null);
    var _v = useState(""), view = _v[0], setView = _v[1];
    var _d = useState(false), demo = _d[0], setDemo = _d[1];
    var _e = useState(null), error = _e[0], setError = _e[1];
    var _l = useState(true), loading = _l[0], setLoading = _l[1];
    var setViewRef = useRef(setView);
    setViewRef.current = setView;

    useEffect(function () {
      var cancelled = false;
      setLoading(true);
      var url = "/api/plugins/accounting-starter/page?view=" + encodeURIComponent(view) + (demo ? "&demo=true" : "");
      SDK.fetchJSON(url).then(function (data) {
        if (cancelled || !host.current) return;
        var shadow = host.current.shadowRoot || host.current.attachShadow({ mode: "open" });
        shadow.innerHTML = "<style>" + data.css + "</style>" + clean(data.html);
        if (!shadow.__accountingLinks) {
          shadow.__accountingLinks = true;
          shadow.addEventListener("click", function (event) {
            var link = event.target.closest && event.target.closest("a[data-view]");
            if (!link) return;
            event.preventDefault();
            setViewRef.current(link.getAttribute("data-view") || "");
          });
        }
        setError(null);
        setLoading(false);
      }).catch(function (err) {
        if (cancelled) return;
        setError(String((err && err.message) || err));
        setLoading(false);
      });
      return function () { cancelled = true; };
    }, [view, demo]);

    return h("div", { className: "flex flex-col gap-3" },
      h("div", { className: "flex items-center gap-2" },
        h(Button, { variant: demo ? "outline" : "default", size: "sm", onClick: function () { setDemo(false); } }, "My books"),
        h(Button, { variant: demo ? "default" : "outline", size: "sm", onClick: function () { setDemo(true); } }, "Demo data"),
        loading ? h("span", { className: "text-sm text-muted-foreground" }, "Loading…") : null
      ),
      error ? h("p", { className: "text-sm text-destructive" }, "Could not load the ledger: " + error) : null,
      h("div", { ref: host })
    );
  }

  window.__HERMES_PLUGINS__.register("accounting-starter", AccountingPage);
})();

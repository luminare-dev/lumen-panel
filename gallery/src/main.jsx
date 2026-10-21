import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import bulmaLtr from "bulma/css/bulma.min.css?url";
import bulmaRtl from "bulma/css/bulma-rtl.min.css?url";
import skeleton from "./panel-skeleton.css?url";
import { App } from "./App.jsx";

// Order matters and mirrors the panel: Bulma, then the panel layout skeleton (standing in for the
// default theme's own stylesheet, which is not part of this repository), then Lumen.
const link = document.createElement("link");
link.rel = "stylesheet";
link.href = skeleton;
document.getElementById("lumen-css").before(link);

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App bulma={{ ltr: bulmaLtr, rtl: bulmaRtl }} />
  </StrictMode>,
);

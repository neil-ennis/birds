"use strict";

window.activateBirdComments = function () {
  const widget = document.querySelector("comentario-comments");
  if (!widget) return;

  if (["localhost", "127.0.0.1"].includes(window.location.hostname)) {
    document.getElementById("comments-preview-note").hidden = false;
    widget.hidden = true;
    return;
  }

  const script = document.createElement("script");
  script.src = "https://comments.neilennis.com/comentario.js";
  script.defer = true;
  document.head.append(script);
};

if (document.body.classList.contains("about-page")) {
  window.activateBirdComments();
}

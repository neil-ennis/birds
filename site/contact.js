"use strict";

const contactForm = document.getElementById("contact-form");
const contactButton = document.getElementById("contact-submit");
const contactStatus = document.getElementById("contact-status");

function showContactStatus(message, kind) {
  contactStatus.textContent = message;
  contactStatus.className = `contact-status contact-status-${kind}`;
  contactStatus.hidden = false;
}

contactForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!contactForm.reportValidity()) return;

  contactButton.disabled = true;
  contactButton.textContent = "Sending…";
  showContactStatus("Sending your message…", "sending");

  try {
    const response = await fetch(contactForm.action, {
      method: "POST",
      body: new FormData(contactForm),
    });
    if (!response.ok) {
      showContactStatus("The message was not accepted. Please use the other contact page below.", "error");
      return;
    }

    const result = await response.json();
    if (result && result.status === "ok") {
      contactForm.reset();
      showContactStatus("Thanks, your message has been sent.", "success");
    } else {
      showContactStatus("The message was not accepted. Please use the other contact page below.", "error");
    }
  } catch {
    // A cross-origin response can be unreadable even after the POST reaches Google.
    // Do not retry automatically or claim that delivery succeeded.
    showContactStatus("We couldn’t confirm whether your message arrived. Please don’t send it again immediately. The other contact page is linked below if you need it.", "error");
  } finally {
    contactButton.disabled = false;
    contactButton.innerHTML = 'Send message <span aria-hidden="true">↗</span>';
  }
});

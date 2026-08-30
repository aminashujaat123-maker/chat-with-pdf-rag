// Auth pages — front-end logic.
// Shared between login.html and signup.html; the mode (which
// determines which API endpoint to call) comes from the script
// tag's data-mode attribute.

const authForm = document.getElementById("auth-form");
const usernameInput = document.getElementById("username");
const passwordInput = document.getElementById("password");
const authError = document.getElementById("auth-error");
const authSubmit = document.getElementById("auth-submit");

const mode = document.currentScript.dataset.mode; // "login" or "signup"
const endpoint = mode === "signup" ? "/api/signup" : "/api/login";

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  authError.classList.add("hidden");
  authSubmit.disabled = true;
  authSubmit.textContent =
    mode === "signup" ? "Creating account..." : "Logging in...";

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Something went wrong.");
    }

    // On success, redirect to the main chat page
    window.location.href = "/";
  } catch (error) {
    authError.textContent = error.message;
    authError.classList.remove("hidden");
    authSubmit.disabled = false;
    authSubmit.textContent = mode === "signup" ? "Sign Up" : "Log In";
  }
});

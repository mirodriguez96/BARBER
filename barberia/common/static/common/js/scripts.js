document.addEventListener("DOMContentLoaded", function () {
  document.body.classList.add("js-ready");

  const toasts = document.querySelectorAll("[data-toast-message]");
  toasts.forEach((toast) => {
    window.setTimeout(() => {
      toast.remove();
    }, 2500);
  });
});

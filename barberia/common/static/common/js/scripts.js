document.addEventListener("DOMContentLoaded", function () {
  document.body.classList.add("js-ready");

  const toasts = document.querySelectorAll("[data-toast-message]");
  toasts.forEach((toast) => {
    window.setTimeout(() => {
      toast.remove();
    }, 2500);
  });

  const kindSelect = document.getElementById("id_kind");
  const commissionField = document.getElementById("id_barber_commission_percent");
  if (kindSelect && commissionField) {
    const toggleCommission = () => {
      if (kindSelect.value === "product") {
        commissionField.value = "0.00";
        commissionField.disabled = true;
      } else {
        commissionField.disabled = false;
      }
    };
    kindSelect.addEventListener("change", toggleCommission);
    toggleCommission();
  }

  const serviceSelect = document.querySelector('[data-service-selector="true"]');
  const servicePrice = document.getElementById("id_service_price");
  const commissionAmount = document.getElementById("id_commission_amount");

  if (serviceSelect && servicePrice && commissionAmount) {
    const applyServiceValues = () => {
      const option = serviceSelect.selectedOptions[0];
      const price = option?.dataset?.price || "";
      const commission = option?.dataset?.commission || "";
      servicePrice.value = price;
      commissionAmount.value = commission;
    };
    serviceSelect.addEventListener("change", applyServiceValues);
    applyServiceValues();
  }
});

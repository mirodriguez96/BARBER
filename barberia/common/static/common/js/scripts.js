document.addEventListener("DOMContentLoaded", function () {
  document.body.classList.add("js-ready");

  const toasts = document.querySelectorAll("[data-toast-message]");
  toasts.forEach((toast) => {
    window.setTimeout(() => {
      toast.remove();
    }, 2500);
  });

  const kindSelect = document.getElementById("id_kind");
  const commissionField = document.getElementById(
    "id_barber_commission_percent",
  );
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

  const serviceSelect = document.querySelector(
    '[data-service-selector="true"]',
  );
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

  const productSelect = document.querySelector(
    '[data-product-selector="true"]',
  );
  const productQuantity = document.getElementById("id_quantity");
  const productPrice = document.getElementById("id_service_price");

  if (productSelect && productQuantity && productPrice) {
    const applyProductValues = () => {
      const idx = productSelect.selectedIndex;
      const option = productSelect.options[idx];
      const unitPrice = parseFloat(option?.getAttribute("data-price") || "0");
      const qty = parseInt(productQuantity.value, 10) || 1;
      productPrice.value = (unitPrice * qty).toFixed(2);
    };
    productSelect.addEventListener("change", applyProductValues);
    productQuantity.addEventListener("change", applyProductValues);
    productQuantity.addEventListener("input", applyProductValues);
    applyProductValues();
  }

  const barberField = document.getElementById("id_barber");
  const servicesForm = document.querySelector(".dashboard-form");
  if (barberField && servicesForm) {
    servicesForm.addEventListener("submit", function (e) {
      if (!barberField.value) {
        e.preventDefault();
        alert("Debes seleccionar un colaborador para registrar un servicio.");
        barberField.focus();
      }
    });
  }
});

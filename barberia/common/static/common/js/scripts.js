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
  const servicePrice = document.getElementById("id_product_price");
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
  const productPrice = document.getElementById("id_product_price");

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

  document
    .querySelectorAll(".dashboard-filters__form")
    .forEach(function (form) {
      form
        .querySelectorAll("select, input:not([type=hidden])")
        .forEach(function (el) {
          el.addEventListener("change", function () {
            form.requestSubmit();
          });
        });
    });

  const barberField = document.getElementById("id_employee");
  const salesForm = document.querySelector(".dashboard-form");
  if (barberField && salesForm) {
    salesForm.addEventListener("submit", function (e) {
      if (!barberField.value) {
        e.preventDefault();
        alert("Debes seleccionar un colaborador para registrar un servicio.");
        barberField.focus();
      }
    });
  }

  const supplyCheck = document.getElementById("id_is_supply");
  const notesField = document.getElementById("id_notes");
  if (supplyCheck && notesField) {
    supplyCheck.addEventListener("change", function () {
      if (supplyCheck.checked) {
        notesField.value = "Insumo de la empresa";
      } else {
        notesField.value = "";
      }
    });
  }

  // Mobile nav toggle
  var sidebar = document.getElementById("dashboardSidebar");
  var navToggle = document.getElementById("navToggle");
  var navClose = document.getElementById("navClose");

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove("is-open");
    if (navToggle) navToggle.setAttribute("aria-label", "Abrir men\u00fa");
  }

  if (navToggle && sidebar) {
    navToggle.addEventListener("click", function () {
      sidebar.classList.toggle("is-open");
      var isOpen = sidebar.classList.contains("is-open");
      navToggle.setAttribute(
        "aria-label",
        isOpen ? "Cerrar men\u00fa" : "Abrir men\u00fa",
      );
    });
  }

  if (navClose && sidebar) {
    navClose.addEventListener("click", closeSidebar);
  }

  // Close sidebar when a menu item is clicked
  if (sidebar) {
    sidebar.querySelectorAll(".dashboard-menu__item").forEach(function (item) {
      item.addEventListener("click", closeSidebar);
    });
  }
});

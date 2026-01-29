(function () {
  // Wait until Django admin has fully loaded jQuery
  document.addEventListener("DOMContentLoaded", function () {

    if (typeof django === "undefined" || typeof django.jQuery === "undefined") {
      console.warn("prefill_staff_facility: django.jQuery not available");
      return;
    }

    var $ = django.jQuery;

    // Only run inside popup
    if (window.location.search.indexOf("_popup=1") === -1) return;

    var params = new URLSearchParams(window.location.search);
    var facilityId = params.get("facility");
    if (!facilityId) return;

    var $facility = $("select[name='hfname']");
    if ($facility.length) {
      $facility.val(facilityId);
    }

  });
})();

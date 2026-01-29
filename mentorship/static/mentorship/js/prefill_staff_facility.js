(function ($) {
  $(document).ready(function () {

    // This file should NEVER crash
    // Only run if popup exists
    var isPopup = window.location.search.indexOf("_popup=1") !== -1;
    if (!isPopup) return;

    // Facility is passed as ?facility=<id>
    var params = new URLSearchParams(window.location.search);
    var facilityId = params.get("facility");

    if (!facilityId) return;

    var $facilitySelect = $("select[name='hfname']");
    if ($facilitySelect.length) {
      $facilitySelect.val(facilityId);
    }

  });
})(django.jQuery);

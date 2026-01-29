(function () {
  // Always use Django Admin's jQuery safely
  var $ = (window.django && django.jQuery) ? django.jQuery : null;
  if (!$) {
    console.warn("[prefill_staff_facility] django.jQuery not found");
    return;
  }

  function getFacilityId() {
    return $("#id_facilityfk").val();
  }

  function addFacilityParam(href, facId) {
    if (!facId) return href;

    try {
      var url = new URL(href, window.location.origin);
      url.searchParams.set("facility", facId);
      return url.pathname + url.search;
    } catch (e) {
      // fallback
      if (href.indexOf("facility=") !== -1) return href;
      return href + (href.indexOf("?") === -1 ? "?" : "&") + "facility=" + encodeURIComponent(facId);
    }
  }

  // Update the "+" popup link for mentee only
  $(document).on("mousedown", "a.related-widget-wrapper-link.add-related", function () {
    var facId = getFacilityId();
    if (!facId) return;

    // only apply when clicking "+" next to menteename in inline row
    var isMenteeField = $(this).closest("td, .related-widget-wrapper").closest(".form-row, td").hasClass("field-menteename")
      || $(this).closest("td").hasClass("field-menteename")
      || $(this).closest(".form-row").hasClass("field-menteename");

    if (!isMenteeField) return;

    var href = $(this).attr("href");
    if (!href) return;

    $(this).attr("href", addFacilityParam(href, facId));
  });

  console.log("[prefill_staff_facility] loaded");
})();

(function ($) {
  $(document).ready(function () {

    function getFacilityId() {
      return $("#id_facilityfk").val();
    }

    function addFacilityParamToHref(href, facId) {
      try {
        var url = new URL(href, window.location.origin);
        url.searchParams.set("facility", facId);
        return url.pathname + url.search;
      } catch (e) {
        // fallback (very rare)
        if (href.indexOf("facility=") !== -1) return href;
        return href + (href.indexOf("?") === -1 ? "?" : "&") + "facility=" + encodeURIComponent(facId);
      }
    }

    // Update the add popup link when user clicks "+" (works even if DOM changes)
    $(document).on("mousedown click", "a.related-widget-wrapper-link.add-related", function () {
      var facId = getFacilityId();
      if (!facId) return;

      // Only apply to the menteename field "+" (so we don't affect other add popups)
      // In tabular inline, the select is inside td.field-menteename
      var isMenteeField = $(this).closest("td.field-menteename, .form-row.field-menteename").length > 0;
      if (!isMenteeField) return;

      var href = $(this).attr("href");
      if (!href) return;

      var newHref = addFacilityParamToHref(href, facId);
      $(this).attr("href", newHref);
    });

  });
})(django.jQuery);

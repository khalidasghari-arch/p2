(function ($) {
  $(document).ready(function () {
    function updateAddStaffLinks() {
      var fac = $("#id_facilityfk").val();
      if (!fac) return;

      $(".field-menteename .related-widget-wrapper-link.add-related").each(function () {
        var href = $(this).attr("href");
        if (!href) return;

        try {
          var url = new URL(href, window.location.origin);
          url.searchParams.set("facility", fac);
          $(this).attr("href", url.pathname + url.search);
        } catch (e) {}
      });
    }

    updateAddStaffLinks();
    $("#id_facilityfk").on("change", updateAddStaffLinks);

    $(document).on("formset:added", function () {
      updateAddStaffLinks();
    });
  });
})(django.jQuery);

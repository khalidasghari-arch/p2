(function ($) {
  $(document).ready(function () {

    // Correct endpoint (NO object id in the URL)
    // Always: /admin/mentorship/mentorshipvisit/topics-by-thematic/
    function endpoint() {
      var p = window.location.pathname;

      // Change page example:
      // /admin/mentorship/mentorshipvisit/2/change/
      // Add page example:
      // /admin/mentorship/mentorshipvisit/add/
      // List page example:
      // /admin/mentorship/mentorshipvisit/
      //
      // We want base: /admin/mentorship/mentorshipvisit/
      var base = p
        .replace(/\/\d+\/change\/?$/, "/")   // remove "<id>/change/"
        .replace(/\/add\/?$/, "/");         // remove "add/"

      // ensure trailing slash
      if (!base.endsWith("/")) base += "/";

      return base + "topics-by-thematic/";
    }

    function setEmpty($topic) {
      $topic.empty().append($("<option>").val("").text("---------"));
    }

    function setLoading($topic) {
      $topic.empty().append($("<option>").val("").text("Loading..."));
    }

    function setOptions($topic, items, selectedId) {
      $topic.empty().append($("<option>").val("").text("---------"));
      items.forEach(function (item) {
        var opt = $("<option>").val(item.id).text(item.label);
        if (selectedId && String(item.id) === String(selectedId)) {
          opt.prop("selected", true);
        }
        $topic.append(opt);
      });
    }

    // Map thematic select to topic select by ID suffix in the same inline row
    function findTopicForThematic($thematic) {
      var tid = $thematic.attr("id");
      if (!tid || tid.indexOf("__prefix__") !== -1) return null;
      var topicId = tid.replace(/-thematicname$/, "-topicname");
      var $topic = $("#" + topicId);
      return $topic.length ? $topic : null;
    }

    function loadTopics($thematic) {
      var thematicId = $thematic.val();
      var $topic = findTopicForThematic($thematic);
      if (!$topic) return;

      if (!thematicId) {
        setEmpty($topic);
        return;
      }

      var current = $topic.val();
      setLoading($topic);

      $.getJSON(endpoint(), { thematic_id: thematicId })
        .done(function (resp) {
          var items = (resp && resp.results) ? resp.results : [];

          // If backend returns empty, show only "---------" (not blank)
          var keep = items.some(function (x) { return String(x.id) === String(current); })
            ? current
            : "";

          setOptions($topic, items, keep);
        })
        .fail(function () {
          // Request failed -> revert to empty list
          setEmpty($topic);
        });
    }

    // Change thematic => refresh topic instantly
    $(document).on("change", "select[id$='-thematicname']", function () {
      loadTopics($(this));
    });

    // Initialize existing rows on load
    $("select[id$='-thematicname']").each(function () {
      var $t = $(this);
      if ($t.attr("id").indexOf("__prefix__") !== -1) return;

      var $topic = findTopicForThematic($t);
      if ($topic) setEmpty($topic);

      if ($t.val()) loadTopics($t);
    });

    // New inline row added
    $(document).on("formset:added", function (event, $row) {
      var $t = $row.find("select[id$='-thematicname']");
      if ($t.length) {
        var $topic = findTopicForThematic($t);
        if ($topic) setEmpty($topic);
        if ($t.val()) loadTopics($t);
      }
    });

  });
})(django.jQuery);

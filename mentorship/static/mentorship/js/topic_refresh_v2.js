(function ($) {
  $(document).ready(function () {

    /* =========================================================
       AJAX ENDPOINT (STABLE – NOT ADMIN-DEPENDENT)
       ========================================================= */
    function endpoint() {
      return "/mentorship/ajax/topics-by-thematic/";
    }

    /* =========================================================
       HELPERS
       ========================================================= */
    function clearTopic($topic) {
      $topic.empty();
      $topic.append($("<option>").val("").text("---------"));
    }

    function showLoading($topic) {
      $topic.empty();
      $topic.append($("<option>").val("").text("Loading..."));
    }

    function populateTopics($topic, items, selectedId) {
      $topic.empty();
      $topic.append($("<option>").val("").text("---------"));

      items.forEach(function (item) {
        var opt = $("<option>").val(item.id).text(item.label);
        if (selectedId && String(item.id) === String(selectedId)) {
          opt.prop("selected", true);
        }
        $topic.append(opt);
      });
    }

    /* =========================================================
       FIND MATCHING TOPIC FIELD FOR A THEMATIC FIELD
       (SAME INLINE ROW)
       ========================================================= */
    function findTopicSelect($thematic) {
      var id = $thematic.attr("id");
      if (!id || id.indexOf("__prefix__") !== -1) return null;

      var topicId = id.replace("-thematicname", "-topicname");
      var $topic = $("#" + topicId);

      return $topic.length ? $topic : null;
    }

    /* =========================================================
       LOAD TOPICS VIA AJAX
       ========================================================= */
    function loadTopics($thematic) {
      var thematicId = $thematic.val();
      var $topic = findTopicSelect($thematic);

      if (!$topic) return;

      if (!thematicId) {
        clearTopic($topic);
        return;
      }

      var previouslySelected = $topic.val();
      showLoading($topic);

      $.ajax({
        url: endpoint(),
        data: { thematic_id: thematicId },
        method: "GET",
        dataType: "json",
        success: function (resp) {
          var items = resp && resp.results ? resp.results : [];

          // Keep selection ONLY if still valid
          var keep = items.some(function (x) {
            return String(x.id) === String(previouslySelected);
          }) ? previouslySelected : "";

          populateTopics($topic, items, keep);
        },
        error: function () {
          // On error, NEVER leave blank
          clearTopic($topic);
        }
      });
    }

    /* =========================================================
       EVENTS
       ========================================================= */

    // When thematic changes → reload topic
    $(document).on("change", "select[id$='-thematicname']", function () {
      loadTopics($(this));
    });

    // Initialize existing rows on page load
    $("select[id$='-thematicname']").each(function () {
      var $thematic = $(this);
      if ($thematic.attr("id").indexOf("__prefix__") !== -1) return;

      var $topic = findTopicSelect($thematic);
      if ($topic) clearTopic($topic);

      if ($thematic.val()) {
        loadTopics($thematic);
      }
    });

    // When new inline row is added
    $(document).on("formset:added", function (event, $row) {
      var $thematic = $row.find("select[id$='-thematicname']");
      if ($thematic.length) {
        var $topic = findTopicSelect($thematic);
        if ($topic) clearTopic($topic);
      }
    });

  });
})(django.jQuery);

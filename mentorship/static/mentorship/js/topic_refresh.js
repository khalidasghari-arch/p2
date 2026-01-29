(function ($) {
  $(document).ready(function () {

    function getEndpointUrl() {
      // We are inside /admin/mentorship/mentorshipvisit/<id>/change/
      // so relative URL works:
      return "topics-by-thematic/";
    }

    function setOptions($topic, items, selectedId) {
      $topic.empty();
      $topic.append($("<option></option>").val("").text("---------"));

      items.forEach(function (item) {
        var opt = $("<option></option>").val(item.id).text(item.label);
        if (selectedId && String(item.id) === String(selectedId)) {
          opt.prop("selected", true);
        }
        $topic.append(opt);
      });
    }

    function clearTopic($topic) {
      $topic.empty();
      $topic.append($("<option></option>").val("").text("---------"));
    }

    function updateRowTopics($thematicSelect) {
      var thematicId = $thematicSelect.val();

      // Find matching topic select in the same inline row
      // In TabularInline, both selects are in same <tr>
      var $row = $thematicSelect.closest("tr");
      var $topic = $row.find("select[id$='-topicname']");

      if ($topic.length === 0) return;

      if (!thematicId) {
        clearTopic($topic);
        return;
      }

      // Keep current topic selection if still valid
      var currentTopic = $topic.val();

      $.getJSON(getEndpointUrl(), { thematic_id: thematicId })
        .done(function (resp) {
          var items = (resp && resp.results) ? resp.results : [];
          // If currentTopic exists, try keep it (only if in list)
          var keep = items.some(function (x) { return String(x.id) === String(currentTopic); })
            ? currentTopic
            : "";

          setOptions($topic, items, keep);
        })
        .fail(function () {
          // If request fails, don’t break admin UI
          clearTopic($topic);
        });
    }

    // 1) On change of thematic in ANY row -> update that row topics
    $(document).on("change", "select[id$='-thematicname']", function () {
      updateRowTopics($(this));
    });

    // 2) On page load, initialize all existing rows with thematic selected
    $("select[id$='-thematicname']").each(function () {
      var $thematic = $(this);
      if ($thematic.val()) {
        updateRowTopics($thematic);
      }
    });

    // 3) When a new inline row is added -> initialize it too
    $(document).on("formset:added", function (event, $row, formsetName) {
      // find thematic select in new row and update
      var $thematic = $row.find("select[id$='-thematicname']");
      if ($thematic.length && $thematic.val()) {
        updateRowTopics($thematic);
      } else if ($thematic.length) {
        // ensure topic starts empty
        var $topic = $row.find("select[id$='-topicname']");
        if ($topic.length) clearTopic($topic);
      }
    });

  });
})(django.jQuery);

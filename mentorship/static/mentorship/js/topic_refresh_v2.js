(function ($) {
  $(document).ready(function () {

    function endpoint() {
      return "/mentorship/ajax/topics-by-thematic/";
    }

    console.log("[topic_refresh_v2] loaded");

    function clearTopic($topic) {
      $topic.empty().append($("<option>").val("").text("---------"));
    }

    function showLoading($topic) {
      $topic.empty().append($("<option>").val("").text("Loading..."));
    }

    function populateTopics($topic, items, selectedId) {
      $topic.empty().append($("<option>").val("").text("---------"));

      items.forEach(function (item) {
        var opt = $("<option>").val(item.id).text(item.label);
        if (selectedId && String(item.id) === String(selectedId)) {
          opt.prop("selected", true);
        }
        $topic.append(opt);
      });
    }

    // Find topic select in SAME inline row (by name suffix)
    function findTopicSelectFromThematic($thematic) {
      var $row = $thematic.closest("tr, .form-row, fieldset, .inline-related");
      if (!$row.length) return null;

      // most reliable: name ends with "-topicname"
      var $topic = $row.find("select[name$='-topicname']");
      if ($topic.length) return $topic;

      // fallback: if your field name differs, try "topicname"
      $topic = $row.find("select[name*='topicname']");
      if ($topic.length) return $topic;

      return null;
    }

    function loadTopics($thematic) {
      var thematicId = $thematic.val();
      var $topic = findTopicSelectFromThematic($thematic);

      // DEBUG line to confirm it finds the topic select
      console.log("[topic_refresh_v2] thematic:", thematicId, "topic_found:", !!($topic && $topic.length));

      if (!$topic || !$topic.length) return;

      if (!thematicId) {
        clearTopic($topic);
        return;
      }

      var prev = $topic.val();
      showLoading($topic);

      $.ajax({
        url: endpoint(),
        data: { thematic_id: thematicId },
        method: "GET",
        dataType: "json",
        success: function (resp) {
          var items = (resp && resp.results) ? resp.results : [];
          var keep = items.some(function (x) {
            return String(x.id) === String(prev);
          }) ? prev : "";
          populateTopics($topic, items, keep);
        },
        error: function () {
          clearTopic($topic);
        }
      });
    }

    // listen by NAME (not ID)
    $(document).on("change", "select[name$='-thematicname'], select[name*='thematicname']", function () {
      loadTopics($(this));
    });

    // init existing rows
    $("select[name$='-thematicname'], select[name*='thematicname']").each(function () {
      var $t = $(this);
      var $topic = findTopicSelectFromThematic($t);
      if ($topic && $topic.length) clearTopic($topic);
      if ($t.val()) loadTopics($t);
    });

    // new inline rows
    $(document).on("formset:added", function (event, $row) {
      var $t = $row.find("select[name$='-thematicname'], select[name*='thematicname']");
      if ($t.length) {
        var $topic = findTopicSelectFromThematic($t);
        if ($topic && $topic.length) clearTopic($topic);
      }
    });

  });
})(django.jQuery);

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

    function populate($topic, items) {
      $topic.empty().append($("<option>").val("").text("---------"));
      items.forEach(function (item) {
        $topic.append($("<option>").val(item.id).text(item.label));
      });
    }

    // Finds the topic select in the SAME inline row as the thematic select
    function findTopicSelect($thematic) {
      var $row = $thematic.closest("tr.form-row, tr, .inline-related, fieldset, .form-row");
      if (!$row.length) return null;

      // try exact model field name first
      var $topic = $row.find("select[name$='-topicname']");
      if ($topic.length) return $topic;

      // fallback: contains topicname
      $topic = $row.find("select[name*='topicname']");
      if ($topic.length) return $topic;

      // last fallback: any select in the Topic Code column (3rd select after mentee+thematic)
      var selects = $row.find("select");
      if (selects.length >= 3) return $(selects.get(2));

      return null;
    }

    function loadTopics($thematic) {
      var thematicId = $thematic.val();
      var $topic = findTopicSelect($thematic);

      console.log("[topic_refresh_v2] thematic:", thematicId, "topic_found:", !!($topic && $topic.length));

      if (!$topic || !$topic.length) return;

      if (!thematicId) {
        clearTopic($topic);
        return;
      }

      showLoading($topic);

      $.ajax({
        url: endpoint(),
        method: "GET",
        dataType: "json",
        data: { thematic_id: thematicId },
        success: function (resp) {
          console.log("[topic_refresh_v2] ajax ok", resp);

          var items = (resp && resp.results) ? resp.results : [];
          populate($topic, items);
        },
        error: function (xhr) {
          console.error("[topic_refresh_v2] ajax error", xhr.status, xhr.responseText);
          clearTopic($topic);
        }
      });
    }

    // ✅ IMPORTANT: Catch BOTH possible names (some admin themes change it)
    $(document).on(
      "change",
      "select[name$='-thematicname'], select[name*='thematicname'], select[id$='-thematicname']",
      function () {
        loadTopics($(this));
      }
    );

    // Init rows on load
    $("select[name$='-thematicname'], select[name*='thematicname'], select[id$='-thematicname']").each(function () {
      var $t = $(this);
      if ($t.val()) loadTopics($t);
    });

  });
})(django.jQuery);

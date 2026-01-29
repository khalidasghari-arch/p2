(function ($) {
  $(document).ready(function () {

    // Build endpoint from current admin change page:
    // /admin/mentorship/mentorshipvisit/<id>/change/
    // -> /admin/mentorship/mentorshipvisit/<id>/topics-by-thematic/
    function endpoint() {
      return window.location.pathname.replace(/\/change\/?$/, "/topics-by-thematic/");
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

    // Map thematic select to topic select using ID suffix
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

      // clear immediately to prevent wrong topic
      if (!thematicId) {
        setEmpty($topic);
        return;
      }

      var current = $topic.val();
      setLoading($topic);

      $.getJSON(endpoint(), { thematic_id: thematicId })
        .done(function (resp) {
          var items = (resp && resp.results) ? resp.results : [];
          var keep = items.some(function (x) { return String(x.id) === String(current); })
            ? current
            : "";
          setOptions($topic, items, keep);
        })
        .fail(function () {
          setEmpty($topic);
        });
    }

    // On change: instant refresh
    $(document).on("change", "select[id$='-thematicname']", function () {
      loadTopics($(this));
    });

    // On page load: initialize existing rows
    $("select[id$='-thematicname']").each(function () {
      var $t = $(this);
      if ($t.attr("id").indexOf("__prefix__") !== -1) return;

      var $topic = findTopicForThematic($t);
      if ($topic) setEmpty($topic);
      if ($t.val()) loadTopics($t);
    });

    // When new inline row is added
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

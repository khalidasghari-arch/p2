(function ($) {
  $(document).ready(function () {

    function endpoint() {
      return window.TOPICS_ENDPOINT_URL || "";
    }

    function isTemplateRowId(id) {
      return id && id.indexOf("__prefix__") !== -1;
    }

    function getTopicSelectForThematic($thematic) {
      // Example: id_items-0-thematicname  -> id_items-0-topicname
      var tid = $thematic.attr("id");
      if (!tid || isTemplateRowId(tid)) return null;

      var topicId = tid.replace(/-thematicname$/, "-topicname");
      var $topic = $("#" + topicId);
      return $topic.length ? $topic : null;
    }

    function setEmpty($topic) {
      $topic.empty();
      $topic.append($("<option></option>").val("").text("---------"));
    }

    function setLoading($topic) {
      $topic.empty();
      $topic.append($("<option></option>").val("").text("Loading..."));
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

    function updateTopicsForThematic($thematic) {
      var url = endpoint();
      if (!url) return;

      var thematicId = $thematic.val();
      var $topic = getTopicSelectForThematic($thematic);
      if (!$topic) return;

      // Clear immediately to avoid wrong topic remaining
      if (!thematicId) {
        setEmpty($topic);
        return;
      }

      var current = $topic.val();
      setLoading($topic);

      $.getJSON(url, { thematic_id: thematicId })
        .done(function (resp) {
          var items = (resp && resp.results) ? resp.results : [];

          // keep current if still valid
          var keep = items.some(function (x) { return String(x.id) === String(current); })
            ? current
            : "";

          setOptions($topic, items, keep);
        })
        .fail(function () {
          setEmpty($topic);
        });
    }

    // On thematic change -> update its paired topic select
    $(document).on("change", "select[id$='-thematicname']", function () {
      updateTopicsForThematic($(this));
    });

    // On page load -> initialize all existing inline rows
    $("select[id$='-thematicname']").each(function () {
      var $t = $(this);
      if (isTemplateRowId($t.attr("id"))) return;

      // If thematic already selected, load its topics
      if ($t.val()) {
        updateTopicsForThematic($t);
      } else {
        var $topic = getTopicSelectForThematic($t);
        if ($topic) setEmpty($topic);
      }
    });

    // When new inline row added -> initialize its topic field
    $(document).on("formset:added", function (event, $row) {
      var $t = $row.find("select[id$='-thematicname']");
      if (!$t.length || isTemplateRowId($t.attr("id"))) return;

      if ($t.val()) {
        updateTopicsForThematic($t);
      } else {
        var $topic = getTopicSelectForThematic($t);
        if ($topic) setEmpty($topic);
      }
    });

  });
})(django.jQuery);

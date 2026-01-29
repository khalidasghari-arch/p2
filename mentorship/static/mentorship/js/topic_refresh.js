(function ($) {
  $(document).ready(function () {

    function endpoint() {
      // Provided by change_form.html
      return window.TOPICS_ENDPOINT_URL || "";
    }

    function setLoading($topic) {
      $topic.empty();
      $topic.append($("<option></option>").val("").text("Loading..."));
    }

    function setEmpty($topic) {
      $topic.empty();
      $topic.append($("<option></option>").val("").text("---------"));
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

    function updateRowTopics($thematic) {
      var url = endpoint();
      if (!url) return;   // endpoint missing -> do nothing safely

      var thematicId = $thematic.val();
      var $row = $thematic.closest("tr");
      var $topic = $row.find("select[id$='-topicname']");

      if (!$topic.length) return;

      // Clear immediately to avoid wrong selection
      if (!thematicId) {
        setEmpty($topic);
        return;
      }

      var current = $topic.val();
      setLoading($topic);

      $.getJSON(url, { thematic_id: thematicId })
        .done(function (resp) {
          var items = (resp && resp.results) ? resp.results : [];
          // keep current if it exists in returned list
          var keep = items.some(function (x) { return String(x.id) === String(current); })
            ? current
            : "";
          setOptions($topic, items, keep);
        })
        .fail(function () {
          setEmpty($topic);
        });
    }

    // On thematic change
    $(document).on("change", "select[id$='-thematicname']", function () {
      updateRowTopics($(this));
    });

    // On page load initialize existing rows
    $("select[id$='-thematicname']").each(function () {
      var $t = $(this);
      if ($t.val()) updateRowTopics($t);
      else {
        // ensure topic is empty
        var $row = $t.closest("tr");
        var $topic = $row.find("select[id$='-topicname']");
        if ($topic.length) setEmpty($topic);
      }
    });

    // When a new inline row is added
    $(document).on("formset:added", function (event, $row) {
      var $t = $row.find("select[id$='-thematicname']");
      if ($t.length) {
        if ($t.val()) updateRowTopics($t);
        else {
          var $topic = $row.find("select[id$='-topicname']");
          if ($topic.length) setEmpty($topic);
        }
      }
    });

  });
})(django.jQuery);

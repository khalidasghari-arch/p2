(function ($) {
  $(document).ready(function () {

    function endpoint() {
      return window.TOPICS_ENDPOINT_URL || "";
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

    function updateRow($thematic) {
      var url = endpoint();
      if (!url) return;

      var thematicId = $thematic.val();
      var $row = $thematic.closest("tr");

      // Find topic select ONLY in same row
      var $topic = $row.find("select").filter(function () {
        return this.id && this.id.match(/-topicname$/);
      });

      if (!$topic.length) return;

      if (!thematicId) {
        setEmpty($topic);
        return;
      }

      var current = $topic.val();
      setLoading($topic);

      $.getJSON(url, { thematic_id: thematicId })
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

    // Change handler (instant refresh)
    $(document).on("change", "select", function () {
      if (this.id && this.id.match(/-thematicname$/)) {
        updateRow($(this));
      }
    });

    // Initialize on page load for all existing rows
    $("select").each(function () {
      if (this.id && this.id.match(/-thematicname$/)) {
        var $t = $(this);

        // ignore template row
        if ($t.attr("id").indexOf("__prefix__") !== -1) return;

        // load topics if thematic is already selected
        if ($t.val()) updateRow($t);
        else {
          // ensure topic empty
          var $row = $t.closest("tr");
          var $topic = $row.find("select").filter(function () {
            return this.id && this.id.match(/-topicname$/);
          });
          if ($topic.length) setEmpty($topic);
        }
      }
    });

    // Initialize newly added inline row
    $(document).on("formset:added", function (event, $row) {
      var $t = $row.find("select").filter(function () {
        return this.id && this.id.match(/-thematicname$/);
      });

      if ($t.length && $t.val()) {
        updateRow($t);
      } else if ($t.length) {
        var $topic = $row.find("select").filter(function () {
          return this.id && this.id.match(/-topicname$/);
        });
        if ($topic.length) setEmpty($topic);
      }
    });

  });
})(django.jQuery);

(function ($) {
  $(function () {
    var URL_ENDPOINT = "/mentorship/ajax/topics-by-thematic/";

    function log() {
      if (window && window.console) console.log.apply(console, arguments);
    }
    function err() {
      if (window && window.console) console.error.apply(console, arguments);
    }

    // ✅ Always select topic dropdown from the SAME <tr> as the changed thematic dropdown
    function getTopicSelect($thematic) {
      var $tr = $thematic.closest("tr");
      if (!$tr.length) return null;

      // Most reliable selectors (admin inlines)
      var $topic =
        $tr.find("select[name$='-topicname']").first();

      if ($topic.length) return $topic;

      $topic =
        $tr.find("select[id$='-topicname']").first();

      if ($topic.length) return $topic;

      // fallback: 3rd select in row (mentee, thematic, topic)
      var $sels = $tr.find("select");
      if ($sels.length >= 3) return $($sels.get(2));

      return null;
    }

    function setOptions($topic, items) {
      // Use pure DOM for reliability
      var el = $topic.get(0);
      if (!el) return;

      // Clear all options
      while (el.options.length) el.remove(0);

      // Add blank option
      el.add(new Option("---------", ""), undefined);

      // Add items
      for (var i = 0; i < items.length; i++) {
        el.add(new Option(items[i].label, items[i].id), undefined);
      }

      // Some admin themes need change trigger
      $topic.trigger("change");
    }

    function setLoading($topic) {
      var el = $topic.get(0);
      if (!el) return;
      while (el.options.length) el.remove(0);
      el.add(new Option("Loading...", ""), undefined);
    }

    function loadTopics($thematic) {
      var thematicId = $thematic.val();
      var $topic = getTopicSelect($thematic);

      log("[topic_refresh_v3] thematic:", thematicId, "topic_found:", !!($topic && $topic.length));

      if (!$topic || !$topic.length) return;

      if (!thematicId) {
        setOptions($topic, []); // will show "---------"
        return;
      }

      setLoading($topic);

      $.ajax({
        url: URL_ENDPOINT,
        method: "GET",
        dataType: "json",
        data: { thematic_id: thematicId },
        success: function (resp) {
          var items = (resp && resp.results) ? resp.results : [];
          log("[topic_refresh_v3] ajax ok len=", items.length, resp);
          setOptions($topic, items);
        },
        error: function (xhr) {
          err("[topic_refresh_v3] ajax error", xhr.status, xhr.responseText);
          setOptions($topic, []);
        },
      });
    }

    // Listen for changes on thematic dropdowns (inline formset)
    $(document).on("change", "select[name$='-thematicname'], select[id$='-thematicname']", function () {
      loadTopics($(this));
    });

    // Init existing rows on load (for edit page)
    $("select[name$='-thematicname'], select[id$='-thematicname']").each(function () {
      var $t = $(this);
      if ($t.val()) loadTopics($t);
    });

    log("[topic_refresh_v3] loaded");
  });
})(django.jQuery);

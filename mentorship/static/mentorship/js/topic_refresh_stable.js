(function () {
  var ENDPOINT = "/mentorship/ajax/topics-by-thematic/";

  function getAdminJQ() {
    // Django admin standard
    if (window.django && window.django.jQuery) return window.django.jQuery;

    // Some admin themes expose jQuery globally
    if (window.jQuery) return window.jQuery;
    if (window.$ && typeof window.$ === "function") return window.$;

    return null;
  }

  function boot() {
    var $ = getAdminJQ();
    if (!$) return false; // not ready yet

    function setOptions($select, items, selectedId) {
      var el = $select.get(0);
      if (!el) return;

      while (el.options.length) el.remove(0);

      el.add(new Option("---------", ""), undefined);

      (items || []).forEach(function (item) {
        var opt = new Option(item.label, item.id);
        if (selectedId && String(item.id) === String(selectedId)) opt.selected = true;
        el.add(opt, undefined);
      });

      $select.trigger("change");
    }

    function setLoading($select) {
      var el = $select.get(0);
      if (!el) return;

      while (el.options.length) el.remove(0);
      el.add(new Option("Loading...", ""), undefined);
    }

    function getTopicSelect($thematic) {
      // Inline row container
      var $row = $thematic.closest("tr.form-row, tr, .inline-related, fieldset");
      if (!$row.length) $row = $thematic.closest("tr");

      // Must match your model field name = topicname
      var $topic = $row.find("select[name$='-topicname']");
      if ($topic.length) return $topic;

      $topic = $row.find("select[id$='-topicname']");
      if ($topic.length) return $topic;

      return null;
    }

    function loadTopics($thematic) {
      var thematicId = $thematic.val();
      var $topic = getTopicSelect($thematic);

      if (!$topic || !$topic.length) return;

      if (!thematicId) {
        setOptions($topic, []);
        return;
      }

      var prev = $topic.val();
      setLoading($topic);

      $.ajax({
        url: ENDPOINT,
        method: "GET",
        dataType: "json",
        data: { thematic_id: thematicId },
        success: function (resp) {
          var items = (resp && resp.results) ? resp.results : [];
          setOptions($topic, items, prev);
        },
        error: function (xhr) {
          console.error("[topic_refresh_stable] ajax error", xhr.status, xhr.responseText);
          setOptions($topic, []);
        },
      });
    }

    // attach events
    $(document).on(
      "change",
      "select[name$='-thematicname'], select[id$='-thematicname']",
      function () {
        loadTopics($(this));
      }
    );

    // init existing rows
    $("select[name$='-thematicname'], select[id$='-thematicname']").each(function () {
      var $t = $(this);
      if ($t.val()) loadTopics($t);
    });

    console.log("[topic_refresh_stable] loaded with jQuery:", !!$);
    return true;
  }

  // Retry boot until admin jQuery is available (solves your screenshot error)
  (function retry(attempt) {
    attempt = attempt || 0;
    if (boot()) return;

    if (attempt < 50) {
      setTimeout(function () {
        retry(attempt + 1);
      }, 100);
    } else {
      console.error("[topic_refresh_stable] jQuery still not found after retries");
    }
  })();
})();

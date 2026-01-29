(function ($) {
  $(function () {
    var ENDPOINT = "/mentorship/ajax/topics-by-thematic/";

    function isTemplate(el) {
      var n = (el.getAttribute("name") || "") + (el.getAttribute("id") || "");
      return n.indexOf("__prefix__") !== -1;
    }

    // Get the topic select in the SAME ROW as the thematic select
    function getTopicSelect($thematic) {
      var thematicEl = $thematic.get(0);
      if (!thematicEl || isTemplate(thematicEl)) return null;

      // Best: same prefix mapping by name
      var thematicName = $thematic.attr("name") || "";
      if (thematicName) {
        var topicName = thematicName.replace(/thematicname$/, "topicname");
        var $topicByName = $("select[name='" + topicName + "']");
        if ($topicByName.length) return $topicByName.first();
      }

      // Fallback: same <tr>
      var $tr = $thematic.closest("tr");
      if (!$tr.length) return null;

      var $topic = $tr.find("select[name$='-topicname'], select[id$='-topicname']").first();
      return $topic.length ? $topic : null;
    }

    function setLoading($topic) {
      var el = $topic.get(0);
      if (!el) return;
      el.disabled = true;
      el.options.length = 0;
      el.add(new Option("Loading...", ""), undefined);
    }

    function setOptionsKeepSelection($topic, items) {
      var el = $topic.get(0);
      if (!el) return;

      // Keep whatever user already selected (if it still exists)
      var prev = $topic.val();

      el.options.length = 0;
      el.add(new Option("---------", ""), undefined);

      for (var i = 0; i < items.length; i++) {
        el.add(new Option(items[i].label, String(items[i].id)), undefined);
      }

      // restore previous selection if still valid
      if (prev && el.querySelector("option[value='" + prev + "']")) {
        $topic.val(prev);
      } else {
        $topic.val("");
      }

      el.disabled = false;

      // IMPORTANT: do NOT trigger change on topic (prevents reset loops)
    }

    function loadTopicsForThematic($thematic) {
      var thematicId = $thematic.val();
      var $topic = getTopicSelect($thematic);
      if (!$topic || !$topic.length) return;

      // prevent reloading if thematic didn't actually change
      var last = $thematic.data("lastThematic") || "";
      if (String(last) === String(thematicId)) return;
      $thematic.data("lastThematic", String(thematicId || ""));

      if (!thematicId) {
        setOptionsKeepSelection($topic, []);
        return;
      }

      setLoading($topic);

      $.ajax({
        url: ENDPOINT,
        method: "GET",
        dataType: "json",
        data: { thematic_id: thematicId },
        success: function (resp) {
          var items = (resp && resp.results) ? resp.results : [];
          setOptionsKeepSelection($topic, items);
        },
        error: function () {
          setOptionsKeepSelection($topic, []);
        }
      });
    }

    // ✅ Only listen to THEMATIC changes
    $(document).on("change", "select[name$='-thematicname'], select[id$='-thematicname']", function () {
      loadTopicsForThematic($(this));
    });

    // Init: load topics for rows that already have thematic selected
    $("select[name$='-thematicname'], select[id$='-thematicname']").each(function () {
      var $t = $(this);
      if ($t.val()) loadTopicsForThematic($t);
    });

    // When a new inline row is added
    $(document).on("formset:added", function (event, $row) {
      $row.find("select[name$='-thematicname'], select[id$='-thematicname']").each(function () {
        var $t = $(this);
        // store empty lastThematic so first selection triggers load
        $t.data("lastThematic", "");
      });
    });

    console.log("[topic_refresh_stable] loaded");
  });
})(django.jQuery);

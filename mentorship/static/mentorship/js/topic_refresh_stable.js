(function () {
  // Always use Django Admin's jQuery safely
  var $ = (window.django && django.jQuery) ? django.jQuery : null;
  if (!$) {
    console.warn("[topic_refresh_stable] django.jQuery not found");
    return;
  }

  var ENDPOINT = "/mentorship/ajax/topics-by-thematic/"; // your working endpoint

  function setOptions($select, items, selectedId) {
    var el = $select.get(0);
    if (!el) return;

    // clear all options
    while (el.options.length) el.remove(0);

    // add blank option
    el.add(new Option("---------", ""), undefined);

    // add items
    (items || []).forEach(function (item) {
      var opt = new Option(item.label, item.id);
      if (selectedId && String(item.id) === String(selectedId)) opt.selected = true;
      el.add(opt, undefined);
    });

    // some admin themes need change trigger
    $select.trigger("change");
  }

  function setLoading($select) {
    var el = $select.get(0);
    if (!el) return;
    while (el.options.length) el.remove(0);
    el.add(new Option("Loading...", ""), undefined);
  }

  // find topic select in same inline row as the thematic select
  function getTopicSelect($thematic) {
    var $row = $thematic.closest("tr.form-row, tr, fieldset, .inline-related");
    if (!$row.length) return null;

    // best: field name ends with "-topicname"
    var $topic = $row.find("select[name$='-topicname']");
    if ($topic.length) return $topic;

    // fallback: id ends with "-topicname"
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

    // keep previous selection if still valid
    var prev = $topic.val();
    setLoading($topic);

    $.ajax({
      url: ENDPOINT (/* no concat */),
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

  // When thematic changes, reload topics
  $(document).on("change", "select[name$='-thematicname'], select[id$='-thematicname']", function () {
    loadTopics($(this));
  });

  // On page load, initialize existing rows (edit page)
  $("select[name$='-thematicname'], select[id$='-thematicname']").each(function () {
    var $t = $(this);
    if ($t.val()) loadTopics($t);
  });

  console.log("[topic_refresh_stable] loaded");
})();

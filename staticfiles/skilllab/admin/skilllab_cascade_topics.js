(function () {
  "use strict";

  const TOPICS_URL = "/admin/skill_lab/skilllabsession/topics-by-thematic/";

  function getRowFromElement(element) {
    return element.closest("tr.dynamic-participant_records");
  }

  function findTopicSelect(thematicSelect) {
    const row = getRowFromElement(thematicSelect);

    if (row) {
      return row.querySelector('select[name$="-topic"]');
    }

    return document.querySelector('select[name="topic"]');
  }

  function resetTopicSelect(topicSelect) {
    if (!topicSelect) return;

    topicSelect.innerHTML = "";

    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = "---------";
    topicSelect.appendChild(emptyOption);

    topicSelect.value = "";

    if (window.django && window.django.jQuery) {
      window.django.jQuery(topicSelect).trigger("change");
    } else {
      topicSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function populateTopics(topicSelect, topics) {
    resetTopicSelect(topicSelect);

    topics.forEach(function (topic) {
      const option = document.createElement("option");
      option.value = topic.id;
      option.textContent = topic.text;
      topicSelect.appendChild(option);
    });

    if (window.django && window.django.jQuery) {
      window.django.jQuery(topicSelect).trigger("change");
    } else {
      topicSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  function loadTopics(thematicSelect) {
    const thematicId = thematicSelect.value;
    const topicSelect = findTopicSelect(thematicSelect);

    if (!topicSelect) return;

    resetTopicSelect(topicSelect);

    if (!thematicId) return;

    topicSelect.disabled = true;

    fetch(`${TOPICS_URL}?thematic_id=${encodeURIComponent(thematicId)}`, {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then(function (response) {
        return response.json();
      })
      .then(function (data) {
        populateTopics(topicSelect, data.results || []);
      })
      .catch(function (error) {
        console.error("Skill Lab topic loading error:", error);
      })
      .finally(function () {
        topicSelect.disabled = false;
      });
  }

  function bindCascadeEvents(context) {
    const root = context || document;

    const thematicSelects = root.querySelectorAll(
      'select[name$="-thematic_area"], select[name="thematic_area"]'
    );

    thematicSelects.forEach(function (select) {
      if (select.dataset.skilllabCascadeBound === "1") return;

      select.dataset.skilllabCascadeBound = "1";

      select.addEventListener("change", function () {
        loadTopics(select);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindCascadeEvents(document);
  });

  document.addEventListener("formset:added", function (event) {
    bindCascadeEvents(event.target);
  });

  if (window.django && window.django.jQuery) {
    window.django.jQuery(document).on("formset:added", function (event, row) {
      bindCascadeEvents(row);
    });
  }
})();
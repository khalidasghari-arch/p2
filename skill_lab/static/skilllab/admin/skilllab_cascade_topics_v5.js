(function () {
  "use strict";

  const TOPICS_URL = "/admin/skill_lab/skilllabsession/topics-by-thematic/";

  function isThematicSelect(el) {
    if (!el || el.tagName !== "SELECT") return false;
    const name = el.getAttribute("name") || "";
    return name.includes("thematic_area");
  }

  function findTopicSelect(thematicSelect) {
    const row = thematicSelect.closest("tr");

    if (row) {
      const topicSelect = row.querySelector('select[name*="topic"]');
      if (topicSelect) return topicSelect;
    }

    const name = thematicSelect.getAttribute("name") || "";
    const topicName = name.replace("thematic_area", "topic");
    return document.querySelector(`[name="${topicName}"]`);
  }

  function resetTopicSelect(topicSelect) {
    topicSelect.innerHTML = "";

    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = "---------";
    topicSelect.appendChild(emptyOption);

    topicSelect.value = "";
  }

  async function loadTopics(thematicSelect) {
    const thematicId = thematicSelect.value;
    const topicSelect = findTopicSelect(thematicSelect);

    console.log("SkillLab selected thematic ID:", thematicId);

    if (!topicSelect) {
      console.warn("SkillLab topic dropdown not found.");
      return;
    }

    resetTopicSelect(topicSelect);

    if (!thematicId) return;

    topicSelect.disabled = true;

    try {
      const response = await fetch(
        `${TOPICS_URL}?thematic_id=${encodeURIComponent(thematicId)}`,
        {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
        }
      );

      const data = await response.json();

      console.log("SkillLab topics JSON:", data);

      resetTopicSelect(topicSelect);

      if (data.results && data.results.length > 0) {
        data.results.forEach((topic) => {
          const option = document.createElement("option");
          option.value = topic.id;
          option.textContent = topic.text;
          topicSelect.appendChild(option);
        });
      }

      topicSelect.disabled = false;
      topicSelect.dispatchEvent(new Event("change", { bubbles: true }));
    } catch (error) {
      console.error("SkillLab topic cascade failed:", error);
      topicSelect.disabled = false;
    }
  }

  document.addEventListener(
    "change",
    function (event) {
      if (isThematicSelect(event.target)) {
        loadTopics(event.target);
      }
    },
    true
  );

  // Also watch value changes because Django admin widgets sometimes do not fire normal change event
  let previousValues = new WeakMap();

  setInterval(function () {
    document.querySelectorAll("select").forEach(function (select) {
      if (!isThematicSelect(select)) return;

      const oldValue = previousValues.get(select);
      const newValue = select.value;

      if (oldValue === undefined) {
        previousValues.set(select, newValue);
        return;
      }

      if (oldValue !== newValue) {
        previousValues.set(select, newValue);
        loadTopics(select);
      }
    });
  }, 400);

  console.log("SkillLab topic cascade v5 loaded.");
})();
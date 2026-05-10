(function () {
  "use strict";

  const TOPICS_URL = "/admin/skill_lab/skilllabsession/topics-by-thematic/";

  function isThematicSelect(el) {
    if (!el || el.tagName !== "SELECT") return false;
    const name = el.getAttribute("name") || "";
    const id = el.getAttribute("id") || "";
    return name.includes("thematic_area") || id.includes("thematic_area");
  }

  function findTopicSelect(thematicSelect) {
    const name = thematicSelect.getAttribute("name") || "";
    const id = thematicSelect.getAttribute("id") || "";

    if (name.includes("thematic_area")) {
      const topicName = name.replace("thematic_area", "topic");
      const byName = document.querySelector(`[name="${topicName}"]`);
      if (byName) return byName;
    }

    if (id.includes("thematic_area")) {
      const topicId = id.replace("thematic_area", "topic");
      const byId = document.getElementById(topicId);
      if (byId) return byId;
    }

    const row = thematicSelect.closest("tr");
    if (row) {
      const rowTopic = row.querySelector('select[name*="topic"], select[id*="topic"]');
      if (rowTopic) return rowTopic;
    }

    return null;
  }

  function resetTopicSelect(topicSelect) {
    if (!topicSelect) return;

    topicSelect.innerHTML = "";

    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "---------";
    topicSelect.appendChild(empty);

    topicSelect.value = "";
  }

  function loadTopics(thematicSelect) {
    const thematicId = thematicSelect.value;
    const topicSelect = findTopicSelect(thematicSelect);

    console.log("SkillLab thematic changed:", thematicId);

    if (!topicSelect) {
      console.warn("SkillLab topic dropdown not found for:", thematicSelect);
      return;
    }

    resetTopicSelect(topicSelect);

    if (!thematicId) return;

    topicSelect.disabled = true;

    const url = `${TOPICS_URL}?thematic_id=${encodeURIComponent(thematicId)}`;
    console.log("Loading SkillLab topics:", url);

    fetch(url, {
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Topic request failed: " + response.status);
        }
        return response.json();
      })
      .then((data) => {
        console.log("Topics returned:", data.results);

        resetTopicSelect(topicSelect);

        (data.results || []).forEach((topic) => {
          const option = document.createElement("option");
          option.value = topic.id;
          option.textContent = topic.text;
          topicSelect.appendChild(option);
        });

        topicSelect.disabled = false;
      })
      .catch((error) => {
        console.error("SkillLab topic loading failed:", error);
        topicSelect.disabled = false;
      });
  }

  function bindEvents() {
    document.addEventListener(
      "change",
      function (event) {
        if (isThematicSelect(event.target)) {
          loadTopics(event.target);
        }
      },
      true
    );

    document.addEventListener(
      "input",
      function (event) {
        if (isThematicSelect(event.target)) {
          loadTopics(event.target);
        }
      },
      true
    );
  }

  function watchValueChanges() {
    const previousValues = new WeakMap();

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
    }, 500);
  }

  function init() {
    bindEvents();
    watchValueChanges();
    console.log("SkillLab topic cascade watcher loaded.");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
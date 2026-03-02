(function() {

    function updateTopics(thematicSelect) {

        const thematicId = thematicSelect.value;
        if (!thematicId) return;

        const row = thematicSelect.closest("tr");
        const topicSelect = row.querySelector("select[name*='topicname']");

        if (!topicSelect) return;

        const url = `/admin/mentorship/mentorshipvisit/get-topics/${thematicId}/`;

        fetch(url)
            .then(response => response.json())
            .then(data => {

                topicSelect.innerHTML = "";

                const emptyOption = document.createElement("option");
                emptyOption.value = "";
                emptyOption.textContent = "---------";
                topicSelect.appendChild(emptyOption);

                data.forEach(topic => {
                    const option = document.createElement("option");
                    option.value = topic.id;
                    option.textContent = topic.name;
                    topicSelect.appendChild(option);
                });
            })
            .catch(err => console.error("Topic fetch error:", err));
    }

    document.addEventListener("change", function(event) {
        if (event.target.matches("select[name*='thematicname']")) {
            updateTopics(event.target);
        }
    });

})();
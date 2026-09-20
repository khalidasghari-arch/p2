(function () {
    "use strict";

    function setupComplications() {
        const boxes = Array.from(
            document.querySelectorAll(
                'input[type="checkbox"][name="complications"]'
            )
        );

        if (!boxes.length) return;

        const noComplicationId =
            boxes[0].dataset.noComplicationId;

        const noneBox = boxes.find(
            box => box.value === noComplicationId
        );

        if (!noneBox) return;

        const otherBoxes = boxes.filter(
            box => box !== noneBox
        );

        function updateState() {
            const conflict =
                noneBox.checked &&
                otherBoxes.some(box => box.checked);

            // Existing contradictory selections need review.
            // Do not silently change them when opening a record.
            noneBox.setCustomValidity(
                conflict
                    ? "Choose No Complication alone, or uncheck it."
                    : ""
            );

            otherBoxes.forEach(box => {
                box.disabled = noneBox.checked && !conflict;

                const label = box.closest("label");
                if (label) {
                    label.style.opacity = box.disabled ? "0.5" : "";
                }
            });
        }

        noneBox.addEventListener("change", function () {
            if (noneBox.checked) {
                otherBoxes.forEach(box => {
                    box.checked = false;
                });
            }

            updateState();
        });

        otherBoxes.forEach(box => {
            box.addEventListener("change", updateState);
        });

        updateState();
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            setupComplications
        );
    } else {
        setupComplications();
    }
})();
document.addEventListener("DOMContentLoaded", function () {
    const dangerSign = document.getElementById("id_dangersign");
    const dangerTypeRow = document.querySelector(".form-row.field-typeofdangersign");

    if (dangerTypeRow) {
        dangerTypeRow.style.display = "";   // always keep textbox visible
    }

    function highlightDangerType() {
        if (!dangerSign || !dangerTypeRow) return;

        if (dangerSign.checked) {
            dangerTypeRow.classList.add("boolean-field-warning");
        } else {
            dangerTypeRow.classList.remove("boolean-field-warning");
        }
    }

    highlightDangerType();

    if (dangerSign) {
        dangerSign.addEventListener("change", highlightDangerType);
    }

    const attendance = document.getElementById("id_attendance");
    const presentGaRow = document.querySelector(".form-row.field-presentga");

    function highlightPresentGA() {
        if (!attendance || !presentGaRow) return;

        if (attendance.value === "ABSENT") {
            presentGaRow.style.backgroundColor = "#fff7ed";
        } else {
            presentGaRow.style.backgroundColor = "";
        }
    }

    highlightPresentGA();

    if (attendance) {
        attendance.addEventListener("change", highlightPresentGA);
    }
});
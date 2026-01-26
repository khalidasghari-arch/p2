document.addEventListener("DOMContentLoaded", function () {
  // Find the inline table
  const inlineGroup = document.querySelector(".inline-group");
  if (!inlineGroup) return;

  const table = inlineGroup.querySelector("table");
  if (!table) return;

  const tbody = table.querySelector("tbody");
  if (!tbody) return;

  const rows = Array.from(tbody.querySelectorAll("tr.form-row"));
  if (!rows.length) return;

  // Helpers to extract text from readonly columns created by admin
  function cellText(row, cls) {
    const cell = row.querySelector(`td.field-${cls}`);
    if (!cell) return "";
    return (cell.innerText || "").trim();
  }

  // Create a clickable header row
  function makeHeaderRow(label, level) {
    const tr = document.createElement("tr");
    tr.className = `hqip-group hqip-${level}`;
    const td = document.createElement("td");
    td.colSpan = 5; // match your inline columns count
    td.innerHTML = `<strong>${label}</strong> <span class="hqip-toggle">(collapse)</span>`;
    tr.appendChild(td);
    tr.style.cursor = "pointer";
    return tr;
  }

  let currentSection = null;
  let currentStandard = null;
  let sectionHeader = null;
  let standardHeader = null;
  let sectionRows = [];
  let standardRows = [];

  function attachToggle(headerRow, rowsToToggle) {
    let open = true;
    headerRow.addEventListener("click", () => {
      open = !open;
      rowsToToggle.forEach(r => r.style.display = open ? "" : "none");
      const toggle = headerRow.querySelector(".hqip-toggle");
      if (toggle) toggle.textContent = open ? "(collapse)" : "(expand)";
    });
  }

  // Rebuild tbody with grouping headers
  const newFrag = document.createDocumentFragment();

  rows.forEach((row) => {
    const sec = cellText(row, "get_section") || "No section";
    const std = cellText(row, "get_standard") || "No standard";

    // New section
    if (sec !== currentSection) {
      // finalize previous standard toggle
      if (standardHeader && standardRows.length) attachToggle(standardHeader, standardRows);
      // finalize previous section toggle (includes all rows in section)
      if (sectionHeader && sectionRows.length) attachToggle(sectionHeader, sectionRows);

      currentSection = sec;
      currentStandard = null;
      sectionRows = [];

      sectionHeader = makeHeaderRow(`Section: ${sec}`, "section");
      newFrag.appendChild(sectionHeader);
    }

    // New standard within section
    if (std !== currentStandard) {
      if (standardHeader && standardRows.length) attachToggle(standardHeader, standardRows);

      currentStandard = std;
      standardRows = [];

      standardHeader = makeHeaderRow(`Standard: ${std}`, "standard");
      newFrag.appendChild(standardHeader);
    }

    // Move the data row
    newFrag.appendChild(row);
    sectionRows.push(row);
    standardRows.push(row);
  });

  // finalize last group
  if (standardHeader && standardRows.length) attachToggle(standardHeader, standardRows);
  if (sectionHeader && sectionRows.length) attachToggle(sectionHeader, sectionRows);

  // Replace tbody content
  tbody.innerHTML = "";
  tbody.appendChild(newFrag);
});

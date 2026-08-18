document.addEventListener("DOMContentLoaded", function () {

    const links = document.querySelectorAll("a");

    links.forEach(function (link) {

        const href = link.getAttribute("href");

        if (
            href &&
            href.includes("/ganc-dashboard/")
        ) {
            link.target = "_blank";
            link.rel = "noopener noreferrer";
        }

    });

});
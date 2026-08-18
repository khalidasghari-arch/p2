document.addEventListener("DOMContentLoaded", function () {

    const dashboardLinks = document.querySelectorAll(
        'a[href*="/ganc-dashboard/"]'
    );

    dashboardLinks.forEach(function (link) {
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "noopener noreferrer");
    });

});
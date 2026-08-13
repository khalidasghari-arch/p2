document.addEventListener(
    "DOMContentLoaded",
    function () {

        function readJson(id) {

            const element =
                document.getElementById(id);

            if (!element) {
                return [];
            }

            try {
                return JSON.parse(
                    element.textContent
                );
            } catch (error) {

                console.error(
                    "Unable to parse dashboard data:",
                    id,
                    error
                );

                return [];
            }
        }


        function drawBarChart(
            svgId,
            labels,
            values,
            isPercent
        ) {

            const chart =
                document.getElementById(
                    svgId
                );

            if (
                !chart ||
                !values.length
            ) {
                return;
            }

            const width =
                chart.clientWidth ||
                1000;

            const height =
                chart.clientHeight ||
                340;

            const margin = {
                top: 30,
                right: 20,
                bottom: 70,
                left: 55
            };

            const innerWidth =
                width -
                margin.left -
                margin.right;

            const innerHeight =
                height -
                margin.top -
                margin.bottom;

            const maxValue =
                isPercent
                    ? 100
                    : Math.max(
                        ...values,
                        1
                    );

            const barSpace =
                innerWidth /
                values.length;

            const barWidth =
                Math.max(
                    barSpace * 0.60,
                    20
                );

            const svgNS =
                "http://www.w3.org/2000/svg";

            chart.setAttribute(
                "viewBox",
                `0 0 ${width} ${height}`
            );

            chart.innerHTML = "";


            function createSvg(
                tag,
                attributes = {}
            ) {

                const element =
                    document.createElementNS(
                        svgNS,
                        tag
                    );

                Object.entries(
                    attributes
                ).forEach(
                    ([key, value]) => {

                        element.setAttribute(
                            key,
                            value
                        );

                    }
                );

                return element;
            }


            const axis = createSvg(
                "line",
                {
                    x1:
                        margin.left,

                    y1:
                        margin.top +
                        innerHeight,

                    x2:
                        margin.left +
                        innerWidth,

                    y2:
                        margin.top +
                        innerHeight,

                    stroke:
                        "#9ca3af",

                    "stroke-width":
                        "1"
                }
            );

            chart.appendChild(
                axis
            );


            values.forEach(
                (value, index) => {

                    const numericValue =
                        Number(value) || 0;

                    const barHeight =
                        (
                            numericValue /
                            maxValue
                        ) *
                        innerHeight;

                    const x =
                        margin.left +
                        (
                            index *
                            barSpace
                        ) +
                        (
                            (
                                barSpace -
                                barWidth
                            ) /
                            2
                        );

                    const y =
                        margin.top +
                        innerHeight -
                        barHeight;


                    const rect =
                        createSvg(
                            "rect",
                            {
                                x: x,
                                y: y,
                                width:
                                    barWidth,
                                height:
                                    barHeight,
                                rx: 4,
                                fill:
                                    "#0f766e"
                            }
                        );

                    chart.appendChild(
                        rect
                    );


                    const valueText =
                        createSvg(
                            "text",
                            {
                                x:
                                    x +
                                    (
                                        barWidth /
                                        2
                                    ),

                                y:
                                    Math.max(
                                        y - 7,
                                        15
                                    ),

                                "text-anchor":
                                    "middle",

                                "font-size":
                                    "12",

                                "font-weight":
                                    "600",

                                fill:
                                    "#374151"
                            }
                        );

                    valueText.textContent =
                        isPercent
                            ? `${numericValue}%`
                            : numericValue;

                    chart.appendChild(
                        valueText
                    );


                    const labelText =
                        createSvg(
                            "text",
                            {
                                x:
                                    x +
                                    (
                                        barWidth /
                                        2
                                    ),

                                y:
                                    margin.top +
                                    innerHeight +
                                    25,

                                "text-anchor":
                                    "middle",

                                "font-size":
                                    "11",

                                fill:
                                    "#4b5563"
                            }
                        );

                    labelText.textContent =
                        labels[index] || "";

                    chart.appendChild(
                        labelText
                    );

                }
            );
        }


        const continuumLabels =
            readJson(
                "continuum-labels"
            );

        const continuumCounts =
            readJson(
                "continuum-counts"
            );

        drawBarChart(
            "gancContinuumChart",
            continuumLabels,
            continuumCounts,
            false
        );


        const breastfeedingLabels =
            readJson(
                "breastfeeding-labels"
            );

        const breastfeedingValues =
            readJson(
                "breastfeeding-values"
            );

        drawBarChart(
            "gancBreastfeedingChart",
            breastfeedingLabels,
            breastfeedingValues,
            true
        );

    }
);
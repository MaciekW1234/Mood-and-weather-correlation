const API_BASE = "http://localhost:8000";

const countrySelect = document.getElementById("country-select");
const statsContainer = document.getElementById("stats");
const statusBox = document.getElementById("status");
const tableBody = document.getElementById("table-body");

let mainChart = null;
let cloudChart = null;
let scatterChart = null;
let barChart = null;
let allCountriesList = [];

async function fetchJSON(path) {
    const url = `${API_BASE}${path}`;
    const res = await fetch(url);
    if (!res.ok) {
        throw new Error(`${res.status} ${res.statusText} (${url})`);
    }
    return res.json();
}

function setStatus(msg, isError = false) {
    statusBox.textContent = msg;
    statusBox.className = isError ? "status error" : "status";
}

function classifyCorr(value) {
    if (value === null || value === undefined) return "neutral";
    if (value > 0.05) return "positive";
    if (value < -0.05) return "negative";
    return "neutral";
}

function renderStats(correlation) {
    const { country, days, corr_temp_polarity, corr_cloud_polarity } = correlation;
    statsContainer.innerHTML = `
        <div class="stat-card">
            <div class="label">Kraj</div>
            <div class="value neutral">${country}</div>
        </div>
        <div class="stat-card">
            <div class="label">Liczba dni</div>
            <div class="value neutral">${days}</div>
        </div>
        <div class="stat-card">
            <div class="label">Temperatura ↔ nastrój</div>
            <div class="value ${classifyCorr(corr_temp_polarity)}">
                ${corr_temp_polarity !== null ? corr_temp_polarity.toFixed(3) : "—"}
            </div>
        </div>
        <div class="stat-card">
            <div class="label">Zachmurzenie ↔ nastrój</div>
            <div class="value ${classifyCorr(corr_cloud_polarity)}">
                ${corr_cloud_polarity !== null ? corr_cloud_polarity.toFixed(3) : "—"}
            </div>
        </div>
    `;
}

function renderMainChart(points) {
    if (mainChart) mainChart.destroy();
    const ctx = document.getElementById("main-chart");

    mainChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: points.map(p => p.date),
            datasets: [
                {
                    label: "Temperatura (°C)",
                    data: points.map(p => p.temp_mean),
                    borderColor: "#e67e22",
                    backgroundColor: "rgba(230, 126, 34, 0.1)",
                    yAxisID: "y-temp",
                    tension: 0.3,
                },
                {
                    label: "Nastrój",
                    data: points.map(p => p.avg_polarity),
                    borderColor: "#2980b9",
                    backgroundColor: "rgba(41, 128, 185, 0.1)",
                    yAxisID: "y-mood",
                    tension: 0.3,
                },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                "y-temp": { type: "linear", position: "left" },
                "y-mood": { type: "linear", position: "right", grid: { drawOnChartArea: false } },
            },
        },
    });
}

function renderCloudChart(points) {
    if (cloudChart) cloudChart.destroy();
    const ctx = document.getElementById("cloud-chart");

    cloudChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: points.map(p => p.date),
            datasets: [
                {
                    label: "Zachmurzenie (%)",
                    data: points.map(p => p.cloudcover),
                    borderColor: "#7f8c8d",
                    backgroundColor: "rgba(127, 140, 141, 0.1)",
                    yAxisID: "y-cloud",
                    tension: 0.3,
                    fill: true
                },
                {
                    label: "Nastrój",
                    data: points.map(p => p.avg_polarity),
                    borderColor: "#2980b9",
                    backgroundColor: "rgba(41, 128, 185, 0.1)",
                    yAxisID: "y-mood",
                    tension: 0.3,
                },
            ],
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                "y-cloud": { type: "linear", position: "left", max: 100, min: 0 },
                "y-mood": { type: "linear", position: "right", grid: { drawOnChartArea: false } },
            },
        },
    });
}

function renderScatterChart(points) {
    if (scatterChart) scatterChart.destroy();
    const ctx = document.getElementById("scatter-chart");

    scatterChart = new Chart(ctx, {
        type: "scatter",
        data: {
            datasets: [{
                label: "Dni",
                data: points.map(p => ({ x: p.temp_mean, y: p.avg_polarity })),
                backgroundColor: "#8e44ad",
                pointRadius: 5,
                pointHoverRadius: 8
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            scales: {
                x: { title: { display: true, text: "Temperatura (°C)" } },
                y: { title: { display: true, text: "Nastrój" } }
            }
        }
    });
}

function renderBarChart(labels, data) {
    if (barChart) barChart.destroy();
    const ctx = document.getElementById("bar-chart");

    barChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Średnia polaryzacja",
                data: data,
                backgroundColor: data.map(v => v > 0 ? "#27ae60" : "#e74c3c"), // Zielony dla pozytywnych, czerwony dla negatywnych
                borderRadius: 4
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { title: { display: true, text: "Nastrój (Polaryzacja)" } }
            }
        }
    });
}

function renderTable(points) {
    tableBody.innerHTML = points.map(p => `
        <tr>
            <td>${p.date}</td>
            <td>${p.temp_mean !== null ? p.temp_mean.toFixed(1) : "—"}</td>
            <td>${p.cloudcover !== undefined ? p.cloudcover : "—"}</td>
            <td>${p.precipitation !== undefined ? p.precipitation : "—"}</td>
            <td>${p.avg_polarity !== null ? p.avg_polarity.toFixed(4) : "—"}</td>
        </tr>
    `).join("");
}

// Funkcja wyliczająca dane dla wszystkich krajów na potrzeby wykresu słupkowego
async function loadGlobalBarChartData(countries) {
    try {
        const promises = countries.map(c => fetchJSON(`/correlation/${encodeURIComponent(c)}`));
        const results = await Promise.all(promises);

        const labels = [];
        const avgData = [];

        results.forEach(res => {
            labels.push(res.country);
            // Wyliczanie średniego nastroju dla danego kraju na podstawie dni
            const validDays = res.data.filter(d => d.avg_polarity !== null);
            const sum = validDays.reduce((acc, val) => acc + val.avg_polarity, 0);
            avgData.push(validDays.length ? sum / validDays.length : 0);
        });

        renderBarChart(labels, avgData);
    } catch (e) {
        console.error("Błąd przy ładowaniu danych do Bar Charta:", e);
    }
}

async function loadCountryData(country) {
    setStatus("Ładowanie...");
    try {
        const data = await fetchJSON(`/correlation/${encodeURIComponent(country)}`);
        renderStats(data);
        renderMainChart(data.data);
        renderCloudChart(data.data);
        renderScatterChart(data.data);
        renderTable(data.data);

        setStatus(`Załadowano pomyślnie.`);
    } catch (e) {
        setStatus(`Błąd: ${e.message}`, true);
    }
}

(async function init() {
    setStatus("Pobieranie konfiguracji...");
    try {
        const data = await fetchJSON("/countries");
        allCountriesList = data.countries;

        countrySelect.innerHTML = allCountriesList
            .map(c => `<option value="${c}">${c}</option>`)
            .join("");

        // Renderuj kraje do Bar Charta od razu
        await loadGlobalBarChartData(allCountriesList);

        if (allCountriesList.length > 0) {
            await loadCountryData(allCountriesList[0]);
        }
    } catch (e) {
        setStatus("Błąd krytyczny inicjalizacji.", true);
    }

    countrySelect.addEventListener("change", (e) => {
        loadCountryData(e.target.value);
    });
})();
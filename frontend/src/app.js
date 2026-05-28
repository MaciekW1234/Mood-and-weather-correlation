const API_BASE = "http://localhost:8000";

const countrySelect = document.getElementById("country-select");
const statsContainer = document.getElementById("stats");
const statusBox = document.getElementById("status");
const chartCanvas = document.getElementById("main-chart");

let chart = null;


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


function renderChart(points) {
    if (chart) chart.destroy();

    const labels = points.map(p => p.date);
    const temps  = points.map(p => p.temp_mean);
    const moods  = points.map(p => p.avg_polarity);

    chart = new Chart(chartCanvas, {
        type: "line",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Temperatura (°C)",
                    data: temps,
                    borderColor: "#e67e22",
                    backgroundColor: "rgba(230, 126, 34, 0.1)",
                    yAxisID: "y-temp",
                    tension: 0.3,
                },
                {
                    label: "Nastrój (polaryzacja)",
                    data: moods,
                    borderColor: "#2980b9",
                    backgroundColor: "rgba(41, 128, 185, 0.1)",
                    yAxisID: "y-mood",
                    tension: 0.3,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            scales: {
                "y-temp": {
                    type: "linear",
                    position: "left",
                    title: { display: true, text: "Temperatura (°C)" },
                },
                "y-mood": {
                    type: "linear",
                    position: "right",
                    title: { display: true, text: "Nastrój" },
                    grid: { drawOnChartArea: false },
                },
            },
        },
    });
}


async function loadCountries() {
    setStatus("Ładowanie listy krajów...");
    try {
        const data = await fetchJSON("/countries");
        countrySelect.innerHTML = data.countries
            .map(c => `<option value="${c}">${c}</option>`)
            .join("");
        setStatus("");
        return data.countries[0];
    } catch (e) {
        setStatus(`Nie udało się pobrać krajów: ${e.message}`, true);
        throw e;
    }
}

async function loadCountryData(country) {
    setStatus(`Ładowanie danych dla: ${country}...`);
    try {
        const data = await fetchJSON(`/correlation/${encodeURIComponent(country)}`);
        renderStats(data);
        renderChart(data.data);
        setStatus(`Załadowano ${data.days} dni dla ${country}.`);
    } catch (e) {
        setStatus(`Błąd ładowania danych: ${e.message}`, true);
    }
}


(async function init() {
    const first = await loadCountries();
    if (first) await loadCountryData(first);

    countrySelect.addEventListener("change", (e) => {
        loadCountryData(e.target.value);
    });
})();
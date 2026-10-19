let breakdownChart = null;
const form = document.getElementById("carbonForm");
const formMessage = document.getElementById("formMessage");
const chartEmpty = document.getElementById("chartEmpty");

function setText(id, value) {
  document.getElementById(id).textContent = value;
}
function makeChart(result) {
  const canvas = document.getElementById("breakdownChart");
  chartEmpty.style.display = "none";
  if (breakdownChart) breakdownChart.destroy();
  breakdownChart = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: ["Transport", "Home energy", "Food"],
      datasets: [{
        data: [result.transport_emissions, result.electricity_emissions, result.food_emissions],
        backgroundColor: ["#287653", "#8dc7a0", "#b8a6e7"],
        borderWidth: 0,
        hoverOffset: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "70%",
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => ` ${ctx.label}: ${ctx.raw} kg CO₂e` } }
      }
    }
  });
}
function renderTips(tips) {
  const container = document.getElementById("tipsContainer");
  container.innerHTML = "";
  const icons = ["↗", "☼", "✿", "✧"];
  tips.forEach((tip, index) => {
    const card = document.createElement("article");
    card.className = "tip-card";
    const icon = document.createElement("div");
    icon.className = "tip-icon";
    icon.textContent = icons[index % icons.length];
    const content = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = tip.title;
    const detail = document.createElement("p");
    detail.textContent = tip.detail;
    const tag = document.createElement("span");
    tag.className = "tip-tag";
    tag.textContent = tip.impact;
    content.append(title, detail, tag);
    card.append(icon, content);
    container.appendChild(card);
  });
}
function renderResult(result) {
  setText("totalMetric", result.total_kg.toFixed(1));
  setText("savedMetric", result.saved_kg.toFixed(1));
  setText("percentMetric", result.reduction_percent.toFixed(1));
  setText("scenarioSaved", `${result.saved_kg.toFixed(1)} kg CO₂e`);
  setText("currentScenario", result.total_kg.toFixed(1));
  setText("futureScenario", result.scenario_kg.toFixed(1));
  setText("scenarioPercent", `${result.reduction_percent.toFixed(1)}%`);
  document.getElementById("progressBar").style.width = `${Math.min(100, result.reduction_percent)}%`;
  makeChart(result);
  renderTips(result.tips);
}
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formMessage.textContent = "";
  const button = form.querySelector("button");
  button.disabled = true;
  button.innerHTML = "Calculating…";
  const data = {
    transport: document.getElementById("transport").value,
    travel_km: document.getElementById("travel_km").value,
    electricity_kwh: document.getElementById("electricity_kwh").value,
    meat_meals: document.getElementById("meat_meals").value
  };
  try {
    const response = await fetch("/api/calculate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(data)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Unable to calculate.");
    renderResult(result);
    formMessage.style.color = "#287653";
    formMessage.textContent = result.disclaimer;
  } catch (error) {
    formMessage.style.color = "#b45151";
    formMessage.textContent = error.message || "Could not connect to the server.";
  } finally {
    button.disabled = false;
    button.innerHTML = '<span>✧</span> Calculate my footprint <span class="btn-arrow">→</span>';
  }
});

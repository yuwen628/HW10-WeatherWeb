let forecastChart = null;

function renderForecastChart(forecast) {
  const context = document.getElementById("forecastChart");
  const labels = forecast.map((item) => item.time.slice(5, 16));
  const temperatures = forecast.map((item) => item.temperature);
  const rain = forecast.map((item) => item.rain_probability);

  if (forecastChart) {
    forecastChart.destroy();
  }

  forecastChart = new Chart(context, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "氣溫 °C",
          data: temperatures,
          borderColor: "#d7542f",
          backgroundColor: "rgba(215, 84, 47, 0.12)",
          tension: 0.35,
          yAxisID: "y",
        },
        {
          label: "降雨機率 %",
          data: rain,
          borderColor: "#1976d2",
          backgroundColor: "rgba(25, 118, 210, 0.12)",
          tension: 0.35,
          yAxisID: "y1",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false,
      },
      scales: {
        y: {
          type: "linear",
          position: "left",
        },
        y1: {
          type: "linear",
          position: "right",
          min: 0,
          max: 100,
          grid: {
            drawOnChartArea: false,
          },
        },
      },
    },
  });
}

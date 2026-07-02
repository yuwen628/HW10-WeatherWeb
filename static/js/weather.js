const WeatherApi = {
  async request(url) {
    const response = await fetch(url);
    const payload = await response.json();

    if (!response.ok || payload.success === false) {
      throw new Error(payload.message || "資料讀取失敗");
    }

    return payload.data ?? payload;
  },

  getLocations() {
    return this.request("/api/locations");
  },

  getWeather(location) {
    return this.request(`/api/weather?location=${encodeURIComponent(location)}`);
  },

  getNearby(lat, lon) {
    return this.request(`/api/weather/nearby?lat=${lat}&lon=${lon}`);
  },

  getCountyTemperatures() {
    return this.request("/api/weather/county-temperatures");
  },

  getSummary(location) {
    return this.request(`/api/weather/summary?location=${encodeURIComponent(location)}`);
  },
};

function formatMetric(value, unit) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "--";
  }
  return `${value}${unit}`;
}

function renderWeather(weather, summary) {
  document.getElementById("locationName").textContent = weather.location;
  renderLocationBadges(weather);
  document.getElementById("updatedAt").textContent = weather.updated_at || "--";
  document.getElementById("temperature").textContent = formatMetric(weather.current.temperature, "°C");
  document.getElementById("humidity").textContent = formatMetric(weather.current.humidity, "%");
  document.getElementById("rainProbability").textContent = formatMetric(weather.current.rain_probability, "%");
  document.getElementById("windSpeed").textContent = formatMetric(weather.current.wind_speed, " m/s");
  document.getElementById("weatherText").textContent = weather.current.weather || "無天氣描述";
  document.getElementById("summaryText").textContent = summary || "目前沒有摘要。";
  renderForecastList(weather.forecast || []);
  renderForecastChart(weather.forecast || []);
}

function renderLocationBadges(weather) {
  const badges = document.getElementById("locationBadges");
  badges.innerHTML = "";

  [
    { label: weather.county, className: "text-bg-primary" },
    { label: weather.town, className: "text-bg-warning" },
  ].filter((item) => item.label).forEach((item) => {
    const badge = document.createElement("span");
    badge.className = `badge rounded-pill ${item.className} location-badge`;
    badge.textContent = item.label;
    badges.appendChild(badge);
  });
}

function renderForecastList(forecast) {
  const list = document.getElementById("forecastList");
  list.innerHTML = "";

  forecast.forEach((item) => {
    const row = document.createElement("div");
    row.className = "forecast-item";
    row.innerHTML = `
      <div>
        <strong>${item.weather || "天氣資料"}</strong>
        <span>${item.time}</span>
      </div>
      <div class="text-end">
        <strong>${formatMetric(item.temperature, "°C")}</strong>
        <span>${formatMetric(item.rain_probability, "%")} 降雨</span>
      </div>
    `;
    list.appendChild(row);
  });
}

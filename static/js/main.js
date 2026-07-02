const message = document.getElementById("message");
const input = document.getElementById("locationInput");
const countySelect = document.getElementById("countySelect");
const searchBtn = document.getElementById("searchBtn");
const locateBtn = document.getElementById("locateBtn");

let allLocations = [];
let messageTimer = null;

function showMessage(text, type = "info") {
  window.clearTimeout(messageTimer);
  message.className = `floating-message alert alert-${type} show`;
  message.textContent = text;

  messageTimer = window.setTimeout(() => {
    message.classList.remove("show");
  }, 3000);
}

function populateCountySelect(locations) {
  const counties = [...new Set(locations.map((item) => item.county).filter(Boolean))].sort();

  counties.forEach((county) => {
    const option = document.createElement("option");
    option.value = county;
    option.textContent = county;
    countySelect.appendChild(option);
  });
}

function getFilteredLocations() {
  const county = countySelect.value;
  if (!county) {
    return allLocations;
  }
  return allLocations.filter((location) => location.county === county);
}

function applyCountyFilter() {
  const filtered = getFilteredLocations();
  renderMarkers(filtered, selectLocation);
  fitLocations(filtered);

  const county = countySelect.value || "全部縣市";
  showMessage(`${county}：顯示 ${filtered.length} 個觀測站`, "success");
}

async function selectLocation(location) {
  try {
    showMessage("正在讀取天氣資料...");
    const weather = await WeatherApi.getWeather(location);
    const summary = await WeatherApi.getSummary(location);
    renderWeather(weather, summary.summary);
    focusLocation(weather);
    highlightSelectedMarker(weather.station_id);
    showMessage("資料已更新", "success");
  } catch (error) {
    showMessage(error.message, "danger");
  }
}

async function selectNearby(lat, lon) {
  try {
    showMessage("正在搜尋附近觀測站...");
    const weather = await WeatherApi.getNearby(lat, lon);
    const summary = await WeatherApi.getSummary(weather.station_id);
    renderWeather(weather, `${summary.summary} 距離約 ${weather.distance_km} 公里。`);
    focusLocation(weather);
    highlightSelectedMarker(weather.station_id);
    showMessage("已找到最近觀測站", "success");
  } catch (error) {
    showMessage(error.message, "danger");
  }
}

countySelect.addEventListener("change", applyCountyFilter);

searchBtn.addEventListener("click", () => {
  const location = input.value.trim();
  if (!location) {
    showMessage("請輸入測站、縣市或鄉鎮", "warning");
    return;
  }
  selectLocation(location);
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    searchBtn.click();
  }
});

locateBtn.addEventListener("click", () => {
  if (!navigator.geolocation) {
    showMessage("瀏覽器不支援定位", "warning");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => selectNearby(position.coords.latitude, position.coords.longitude),
    () => showMessage("無法取得定位，請改用地圖點選或搜尋", "warning"),
    { enableHighAccuracy: true, timeout: 8000 }
  );
});

async function bootstrap() {
  try {
    initMap();
    allLocations = await WeatherApi.getLocations();
    populateCountySelect(allLocations);
    renderMarkers(allLocations, selectLocation);
    showMessage(`已載入 ${allLocations.length} 個觀測站`, "success");

    if (allLocations.length > 0) {
      await selectLocation(allLocations[0].id);
    }
  } catch (error) {
    showMessage(error.message, "danger");
  }
}

bootstrap();

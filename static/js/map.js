let weatherMap = null;
let markers = [];
let markerByLocationId = new Map();
let previewByLocationId = new Map();
let temperatureLayer = null;
let countyTemperatureByName = new Map();
let temperatureLegend = null;

const stationIcon = createStationIcon("station-marker-default");
const nearbyStationIcon = createStationIcon("station-marker-nearby");
const COUNTY_GEOJSON_URL = "https://raw.githubusercontent.com/g0v/twgeojson/master/json/twCounty2010.geo.json";

function createStationIcon(className) {
  return L.divIcon({
    className: "station-marker-shell",
    html: `<span class="station-marker ${className}"></span>`,
    iconSize: [24, 34],
    iconAnchor: [12, 34],
    popupAnchor: [0, -30],
  });
}

function initMap() {
  weatherMap = L.map("map").setView([23.8, 121.0], 7);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(weatherMap);

  weatherMap.on("click", async (event) => {
    await selectNearby(event.latlng.lat, event.latlng.lng);
  });

  initTemperatureControl();
}

function renderMarkers(locations, onSelect) {
  markers.forEach((marker) => marker.remove());
  markers = [];
  markerByLocationId = new Map();
  previewByLocationId = new Map();

  locations.forEach((location) => {
    const marker = L.marker([location.lat, location.lon], { icon: stationIcon }).addTo(weatherMap);
    const townName = location.town || "N/A";

    marker.bindPopup(renderPreviewPopup(location, null, "loading"));
    marker.on("mouseover", () => {
      marker.openPopup();
      loadMarkerPreview(marker, location);
    });
    marker.on("mouseout", () => marker.closePopup());
    marker.on("click", (event) => {
      L.DomEvent.stopPropagation(event.originalEvent);
      onSelect(location.id);
    });
    markers.push(marker);
    markerByLocationId.set(location.id, marker);
  });
}

async function loadMarkerPreview(marker, location) {
  const cachedPreview = previewByLocationId.get(location.id);
  if (cachedPreview) {
    marker.setPopupContent(renderPreviewPopup(location, cachedPreview));
    return;
  }

  marker.setPopupContent(renderPreviewPopup(location, null, "loading"));

  try {
    const weather = await WeatherApi.getWeather(location.id);
    previewByLocationId.set(location.id, weather.current);
    marker.setPopupContent(renderPreviewPopup(location, weather.current));
  } catch (error) {
    marker.setPopupContent(renderPreviewPopup(location, null, "error"));
  }
}

function renderPreviewPopup(location, current, state = "ready") {
  const townName = location.town || "N/A";
  const countyName = location.county || "";
  const stationName = location.name || "";

  if (state === "loading") {
    return `
      <div class="popup-title">${townName}</div>
      <div class="popup-meta">${countyName} ${stationName}</div>
      <div class="popup-loading">讀取氣象預覽...</div>
    `;
  }

  if (state === "error") {
    return `
      <div class="popup-title">${townName}</div>
      <div class="popup-meta">${countyName} ${stationName}</div>
      <div class="popup-loading text-danger">預覽資料讀取失敗</div>
    `;
  }

  return `
    <div class="popup-title">${townName}</div>
    <div class="popup-meta">${countyName} ${stationName}</div>
    <div class="popup-preview-grid">
      <div>
        <span>濕度</span>
        <strong>${formatMetric(current.humidity, "%")}</strong>
      </div>
      <div>
        <span>降雨</span>
        <strong>${formatMetric(current.rain_probability, "%")}</strong>
      </div>
      <div>
        <span>風速</span>
        <strong>${formatMetric(current.wind_speed, " m/s")}</strong>
      </div>
    </div>
  `;
}

function highlightSelectedMarker(locationId) {
  markers.forEach((marker) => marker.setIcon(stationIcon));

  const marker = markerByLocationId.get(locationId);
  if (marker) {
    marker.setIcon(nearbyStationIcon);
    marker.openPopup();
  }
}

function focusLocation(weather) {
  if (weather.lat && weather.lon) {
    weatherMap.setView([weather.lat, weather.lon], 11);
  }
}

function fitLocations(locations) {
  if (!locations.length) {
    return;
  }

  const bounds = L.latLngBounds(locations.map((location) => [location.lat, location.lon]));
  weatherMap.fitBounds(bounds, {
    maxZoom: 11,
    padding: [28, 28],
  });
}

function initTemperatureControl() {
  const control = L.control({ position: "topright" });

  control.onAdd = () => {
    const container = L.DomUtil.create("div", "map-layer-control");
    container.innerHTML = `
      <label>
        <input id="temperatureLayerToggle" type="checkbox">
        <span>縣市溫度</span>
      </label>
    `;
    L.DomEvent.disableClickPropagation(container);
    L.DomEvent.disableScrollPropagation(container);

    const toggle = container.querySelector("#temperatureLayerToggle");
    toggle.addEventListener("change", async () => {
      if (toggle.checked) {
        await showTemperatureLayer();
        return;
      }
      hideTemperatureLayer();
    });

    return container;
  };

  control.addTo(weatherMap);
}

async function showTemperatureLayer() {
  try {
    if (!temperatureLayer) {
      await loadTemperatureLayer();
    }
  } catch (error) {
    const toggle = document.getElementById("temperatureLayerToggle");
    if (toggle) {
      toggle.checked = false;
    }
    showMessage("縣市溫度圖層載入失敗", "danger");
    return;
  }

  if (temperatureLayer && !weatherMap.hasLayer(temperatureLayer)) {
    temperatureLayer.addTo(weatherMap);
  }

  if (temperatureLegend) {
    temperatureLegend.addTo(weatherMap);
  }
}

function hideTemperatureLayer() {
  if (temperatureLayer) {
    temperatureLayer.remove();
  }

  if (temperatureLegend) {
    temperatureLegend.remove();
  }
}

async function loadTemperatureLayer() {
  const [temperatures, geoJson] = await Promise.all([
    WeatherApi.getCountyTemperatures(),
    fetch(COUNTY_GEOJSON_URL).then((response) => response.json()),
  ]);

  countyTemperatureByName = new Map(
    temperatures.map((item) => [normalizeCountyName(item.county), item])
  );

  temperatureLayer = L.geoJSON(geoJson, {
    style: (feature) => {
      const data = getFeatureTemperature(feature);
      return {
        color: "#ffffff",
        fillColor: getTemperatureColor(data?.temperature),
        fillOpacity: data ? 0.58 : 0.12,
        opacity: 0.9,
        weight: 1,
      };
    },
    onEachFeature: (feature, layer) => {
      const countyName = getFeatureCountyName(feature);
      const data = getFeatureTemperature(feature);
      layer.bindTooltip(renderTemperatureTooltip(countyName, data), {
        direction: "center",
        sticky: true,
      });
    },
  });

  temperatureLegend = createTemperatureLegend();
}

function getFeatureTemperature(feature) {
  return countyTemperatureByName.get(normalizeCountyName(getFeatureCountyName(feature)));
}

function getFeatureCountyName(feature) {
  const properties = feature.properties || {};
  return (
    properties.COUNTYNAME ||
    properties.COUNTY_NAME ||
    properties.COUNTY ||
    properties.NAME ||
    properties.name ||
    properties.county ||
    ""
  );
}

function normalizeCountyName(name) {
  const normalizedName = (name || "").replaceAll("臺", "台").trim();
  const legacyCountyNames = {
    桃園縣: "桃園市",
    台北縣: "新北市",
    台中縣: "台中市",
    台南縣: "台南市",
    高雄縣: "高雄市",
  };

  return legacyCountyNames[normalizedName] || normalizedName;
}

function getTemperatureColor(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "#94a3b8";
  }
  if (value >= 34) return "#b91c1c";
  if (value >= 31) return "#ef4444";
  if (value >= 28) return "#f97316";
  if (value >= 25) return "#facc15";
  if (value >= 22) return "#86efac";
  return "#60a5fa";
}

function renderTemperatureTooltip(countyName, data) {
  if (!data) {
    return `<strong>${countyName || "未知縣市"}</strong><br>沒有氣溫資料`;
  }

  return `
    <strong>${data.county || countyName}</strong><br>
    平均氣溫 ${formatMetric(data.temperature, "°C")}<br>
    測站 ${data.station_count} 個
  `;
}

function createTemperatureLegend() {
  const legend = L.control({ position: "bottomleft" });
  const grades = [
    { label: "< 22°C", color: "#60a5fa" },
    { label: "22-25°C", color: "#86efac" },
    { label: "25-28°C", color: "#facc15" },
    { label: "28-31°C", color: "#f97316" },
    { label: "31-34°C", color: "#ef4444" },
    { label: ">= 34°C", color: "#b91c1c" },
  ];

  legend.onAdd = () => {
    const container = L.DomUtil.create("div", "temperature-legend");
    container.innerHTML = `
      <strong>縣市平均氣溫</strong>
      ${grades
        .map((item) => `<span><i style="background:${item.color}"></i>${item.label}</span>`)
        .join("")}
    `;
    L.DomEvent.disableClickPropagation(container);
    return container;
  };

  return legend;
}

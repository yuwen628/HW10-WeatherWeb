# HW10-WeatherWeb

使用 Flask、CWA 開放資料、SQLite、Leaflet.js 與 Chart.js 製作的天氣地圖網站。

## 專案結構

```text
HW10-WeatherWeb/
|-- app.py
|-- config.py
|-- cwa_to_sqlite.py
|-- data/weather.db
|-- routes/
|-- services/
|-- static/
|-- templates/
`-- scripts/
```

## 安裝與啟動

```bash
pip install -r requirements.txt
python app.py
```

開啟瀏覽器：

```text
http://localhost:8000
```

## 環境設定

複製 `.env.example` 為 `.env`，並設定 `CWA_API_KEY`。

```text
FLASK_ENV=production
DATABASE_PATH=data/weather.db
PORT=8000
SECRET_KEY=change-me
CWA_API_KEY=your-cwa-api-key
CWA_DATA_ID=O-A0001-001
CWA_DOWNLOAD_TYPE=WEB
CWA_FORMAT=JSON
CWA_SQLITE_DB=data/weather.db
```

Flask app 實際讀取的資料庫是 `data/weather.db`。專案根目錄的 `cwa_observations.sqlite3` 不是目前網站使用的資料庫。

## 資料更新規則

開啟或刷新網頁時，程式會檢查 `data/weather.db` 中最新的 `obs_time`。

- 如果資料庫沒有資料，會呼叫 CWA API 匯入資料。
- 如果現在時間比最新 `obs_time` 超過 3 小時，會呼叫 CWA API 更新資料。
- 如果未超過 3 小時，會略過 CWA API 呼叫。
- 每次檢查更新時，也會清除距離最新 `obs_time` 超過 1 天的舊資料。

也可以手動匯入資料：

```bash
python cwa_to_sqlite.py
```

## 資料庫工具

```bash
python scripts/inspect_db.py
python scripts/init_check.py
```

## API

```http
GET /api/health
GET /api/schema
GET /api/locations
GET /api/weather?location=C2H950
GET /api/weather/nearby?lat=24.1477&lon=120.6736
GET /api/weather/county-temperatures
GET /api/weather/summary?location=C2H950
```

成功回應格式：

```json
{
  "success": true,
  "message": "ok",
  "data": {}
}
```

錯誤回應格式：

```json
{
  "success": false,
  "message": "error message",
  "data": null
}
```

## Docker

```bash
docker build -t weather-forecast-site .
docker run -p 8000:8000 weather-forecast-site
```

或使用 Docker Compose：

```bash
docker compose up -d
```

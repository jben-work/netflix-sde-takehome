# Weather Data Collector

A containerized weather data collection system that fetches weather information from wttr.in API and stores it in InfluxDB.

## Features

- 🌍 Fetches weather data for 10 predefined cities every 30 seconds
- 📊 Stores data in InfluxDB time-series database
- � Automatic dashboard creation on startup with weather table visualization
- �🐳 Fully containerized with Docker Compose
- 🔄 Automatic retry logic with exponential backoff
- � Automated token extraction and management

## Cities Monitored

- Nashville, TN
- Los Gatos, CA
- San Francisco, CA
- London, UK
- Tokyo, JP
- Rome, IT
- Dublin, IE
- New York City, NY
- Seattle, WA
- Paris, FR

## Quick Start

1. **Start all services:**
   ```bash
   docker-compose up --build
   ```

   That's it! The system will automatically:
   - Set up InfluxDB with admin credentials
   - Extract and save the authentication token
   - Create a weather dashboard
   - Start collecting weather data

2. **Run in background (optional):**
   ```bash
   docker-compose up --build -d
   ```

3. **Access the Weather Dashboard:**
   - Open http://localhost:8086 in your browser
   - Login with:
     - Username: `admin`
     - Password: `admin123!`
   - Navigate to **Dashboards** → **Weather Dashboard**
   - View real-time weather data in a table format with cities and weather metrics

4. **View logs (if running in background):**
   ```bash
   docker-compose logs -f get_weather
   ```

## Data Schema

Weather data is stored with the following structure:

**Measurement**: `weather`

**Tags**:
- `a_location`: City name (prefixed with 'a_' for alphabetical sorting in dashboard)
- `country`: Country name  
- `query_location`: Original query string

**Fields**:
- `temperature_celsius`, `temperature_fahrenheit`, `temperature_kelvin`
- `humidity`, `pressure`, `cloudcover`
- `wind_speed_kmph`, `visibility_km`
- `feels_like_celsius`, `feels_like_fahrenheit`
- `latitude`, `longitude`

## Architecture

The system consists of three Docker services:

1. **influxdb2**: 
   - Time-series database for storing weather data
   - Custom entrypoint script that automatically creates the dashboard on startup
   - Exposes web UI on port 8086

2. **token_extractor**: 
   - Lightweight Alpine container that extracts the auto-generated InfluxDB token
   - Saves token to a file for use by the weather collector
   - Runs once and exits

3. **get_weather**: 
   - Python service that polls wttr.in API every 30 seconds
   - Writes weather data to InfluxDB using the extracted token
   - Monitors 10 cities worldwide

## Configuration

All configuration is managed in `docker-compose.yml`:

**InfluxDB Setup:**
- Username: `admin`
- Password: `admin123!`
- Organization: `nflx`
- Bucket: `default`

**Weather Collector:**
- Polling interval: 30 seconds 
- Data retention: Managed by InfluxDB (default: infinite)
- Debug mode: Set `DEBUG=true` environment variable to enable detailed logging

To enable debug mode, add to the `get_weather` service in `docker-compose.yml`:
```yaml
environment:
  - INFLUXDB_URL=http://influxdb2:8086
  - INFLUXDB_ORG=nflx
  - INFLUXDB_BUCKET=default
  - DEBUG=true  # Enable detailed debug logging
```

## Dashboard

The Weather Dashboard is automatically created and includes:
- **Table visualization** showing all cities and their current weather
- **Columns**: City name, temperature, humidity, pressure, cloud cover, wind speed, visibility, and more
- **Real-time updates** as new data arrives every 30 seconds
- **Sortable columns** for easy data analysis

## Troubleshooting

**Port already in use:**
- Ensure port 8086 is not already in use
- Stop any existing InfluxDB instances: `docker stop influxdb2`

**Permission errors:**
- The system will automatically create `influxdb2_data` and `influxdb2_config` directories
- If you encounter permission issues, ensure Docker has access to the current directory
- If you are re-running this locally, `rm -rf influxdb2_data influxdb2_config`

**Dashboard not appearing:**
- Wait 10-20 seconds after startup for the dashboard to be created
- Check InfluxDB logs: `docker-compose logs influxdb2`
- Verify the dashboard exists: Navigate to Dashboards in the InfluxDB UI

**No data in dashboard:**
- Check weather collector logs: `docker-compose logs get_weather`
- Verify token extraction succeeded: `docker-compose logs token_extractor`
- Ensure the wttr.in API is accessible from your network
- Enable debug mode by setting `DEBUG=true` in the `get_weather` service environment variables for more detailed logging

**"Is a directory" error for extracted_token:**
- This happens when the `extracted_token` file was created as a directory
- Run the clean restart commands below to fix it

**Container name already in use:**
- Run `docker-compose down` to remove old containers
- If that doesn't work, run `docker rm -f influxdb2 token_extractor get_weather`

**Clean restart:**
```bash
docker-compose down
rm -rf influxdb2_data influxdb2_config extracted_token
docker-compose up --build
```
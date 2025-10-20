# Weather Data Collector

A containerized weather data collection system that fetches weather information from wttr.in API and stores it in InfluxDB.

(mermaid chart)[https://github.com/jben-work/netflix-sde-takehome/blob/main/files/mermaid_chart.png]

## Features

- 🌍 Fetches weather data for 10 predefined cities every 30 seconds
- 📊 Stores data in InfluxDB time-series database
- Automatic dashboard creation on startup with weather table visualization
- 🐳 Fully containerized with Docker Compose
- 🔄 Automatic retry logic with exponential backoff
- Automated token extraction and management

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

3. **Verify system is working:**
   ```bash
   chmod +x test_system.sh
   ./test_system.sh
   ```

   This test script will verify:
   - ✓ InfluxDB is healthy and responding
   - ✓ All containers are running
   - ✓ Weather data is being written to the database
   - ✓ Multiple locations are being tracked
   - ✓ Dashboard has been created
   - ✓ Data is fresh (< 2 minutes old)
   - ✓ No errors in application logs

4. **Access the Weather Dashboard:**
   - Open http://localhost:8086 in your browser
   - Login with:
     - Username: `admin`
     - Password: `admin123!`
   - Navigate to **Dashboards** → **Weather Dashboard**
   - View real-time weather data in a table format with cities and weather metrics

5. **View logs (if running in background):**
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

## Testing

The project includes an automated integration test script that verifies the entire system:

```bash
./test_system.sh
```

**What it tests:**
1. InfluxDB health endpoint
2. Container status (influxdb2 and get_weather)
3. Data is being written to InfluxDB
4. Multiple locations are tracked (expects 10 cities)
5. Weather Dashboard exists
6. Data freshness (< 2 minutes old)
7. No errors in application logs

The test waits up to 60 seconds for data to appear, making it safe to run immediately after starting the containers.

## Troubleshooting

**Container name conflicts:**
- If you see "container name is already in use" errors:
  ```bash
  docker-compose down
  docker rm -f influxdb2 token_extractor get_weather
  docker-compose up --build
  ```

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
- Run the test script to verify: `./test_system.sh`

**No data in dashboard:**
- Check weather collector logs: `docker-compose logs get_weather`
- Verify token extraction succeeded: `docker-compose logs token_extractor`
- Ensure the wttr.in API is accessible from your network
- Enable debug mode by setting `DEBUG=true` in the `get_weather` service environment variables for more detailed logging
- Run the test script to diagnose: `./test_system.sh`

**Test script fails:**
- Ensure all containers are running: `docker ps`
- Check that InfluxDB is healthy: `curl http://localhost:8086/health`
- Wait 30-60 seconds after startup for data to be collected
- Review individual service logs for errors

## Productionalization
### Scaling
In order to scale this tool, we could begin by deploying multiple instances of this for each city (i.e., one deployment for Nashville, one for Los Gatos, etc.). In addition, we could also implement some sort of queueing mechanism (RabbitMQ/Kafka) to enqueue tasks for each city. We could then scale up workers depending upon demand.

### Reliability and Failover
Looking at this from an SRE perspective makes me want to think about alternatives to wttr.in (What if wttr.n is down?). As of this writing, AWS is having a massive outage, and despite their marketing materials, it doesn't seem like they actually have automated failover :). Given that wttr.in simply returns weather data, I think we should implement a failover weather service. We could build in some monitoring to verify that the endpoint is working, and if not, then failover to another data provider (a quick Google shows weather.gov and openweathermap.org as alternatives). This may mean we need to write some additional code to ensure that the other providers' data is in the format we expect, though.

### Data Persistence 
Currently, this implementation simply writes data on disk. As such, if the host/instance falls over, we would have data loss. A better way to architect this would be to write the data to a persistent DB instance hosted elsewhere.

### High Availability
We also have a single point of failure, given that this instance only runs on one host. Adding in a load balancer and multiple instances would help alleviate any such issues.

### Performance
Thinking about performance...I am sure we could optimize some of the code to have parallel API calls. Similarly, instead of individual writes to the DB, we could batch all of our writes into one request. This likely would be a large improvement in DB throughput. Another point here would be to think about caching: it seems that the wttr.in API has some rate-limiting, so depending on any SLAs we have with customers, we could implement some caching (Redis?) to keep recent results. This would likely also improve startup times.

### Georgraphic distribution
Further, given the recent AWS outage, distributing the per-city-instances across multiple AZs would likely be a good idea. We could also have disaster recovery cold nodes that we could spin up/failover to, in the even that our monitoring detecting any outage(s).

### Observability
As far as telemetry is concerned, since we already have InfluxDB, a logical next step would be to wire up the time-series data to Grafana. We could then use tools like PagerDuty to setup on-call rotations and Slack for coordination.

### Security
The use of `privileged:true` in Docker is not the correct way to productionalize this application. Given the starter docker-compose file's use of bind mounts and how each container needs to read from the other, this was a tradeoff for local development/this interview exercise. In a production environment, we could resolve this by using a Docker managed volume, or something like a k8s persistent volume claim that all pods in the namespace to read/write from. Further, we should remove the hardcoded credentials from the compose file.



**Clean restart:**
```bash
docker-compose down
rm -rf influxdb2_data influxdb2_config extracted_token
docker-compose up --build
```

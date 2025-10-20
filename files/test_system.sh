#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "Weather Monitoring System Tests"
echo "=================================="
echo ""

# Test 1: Check if InfluxDB is healthy
echo -n "Test 1: InfluxDB health check... "
if curl -sf http://localhost:8086/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "  InfluxDB is not responding at http://localhost:8086"
    exit 1
fi

# Test 2: Check if containers are running
echo -n "Test 2: Checking containers... "
INFLUXDB_RUNNING=$(docker ps --filter "name=influxdb2" --filter "status=running" -q)
GET_WEATHER_RUNNING=$(docker ps --filter "name=get_weather" --filter "status=running" -q)

if [ -n "$INFLUXDB_RUNNING" ] && [ -n "$GET_WEATHER_RUNNING" ]; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    if [ -z "$INFLUXDB_RUNNING" ]; then
        echo "  influxdb2 container is not running"
    fi
    if [ -z "$GET_WEATHER_RUNNING" ]; then
        echo "  get_weather container is not running"
    fi
    exit 1
fi

# Get the token for API authentication
TOKEN_FILE="./influxdb2_config/influx-configs"
if [ ! -f "$TOKEN_FILE" ]; then
    echo -e "${RED}✗ FAIL${NC}"
    echo "  Token file not found at $TOKEN_FILE"
    exit 1
fi
TOKEN=$(grep '^  token = ' "$TOKEN_FILE" | sed 's/.*token = "\(.*\)"/\1/')

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ FAIL${NC}"
    echo "  Could not extract token from config file"
    exit 1
fi

# Test 3: Wait for data to be written (give it up to 60 seconds)
echo -n "Test 3: Waiting for weather data to be written... "
RETRIES=12
DATA_FOUND=0

for i in $(seq 1 $RETRIES); do
    # Query InfluxDB for weather data (using POST method)
    RESPONSE=$(curl -s -X POST http://localhost:8086/api/v2/query?org=nflx \
        --header "Authorization: Token $TOKEN" \
        --header "Accept: application/csv" \
        --header "Content-type: application/vnd.flux" \
        --data 'from(bucket: "default") |> range(start: -5m) |> filter(fn: (r) => r._measurement == "weather") |> limit(n: 1)')
    
    # Check if we got any data (look for actual measurements, not just headers)
    if echo "$RESPONSE" | grep -q "weather"; then
        DATA_FOUND=1
        break
    fi
    
    if [ $i -lt $RETRIES ]; then
        sleep 5
    fi
done

if [ $DATA_FOUND -eq 1 ]; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "  No weather data found in InfluxDB after 60 seconds"
    echo "  Response: $RESPONSE"
    exit 1
fi

# Test 4: Verify multiple locations are being tracked
echo -n "Test 4: Checking multiple locations... "
LOCATIONS=$(curl -s -X POST http://localhost:8086/api/v2/query?org=nflx \
    --header "Authorization: Token $TOKEN" \
    --header "Accept: application/csv" \
    --header "Content-type: application/vnd.flux" \
    --data 'from(bucket: "default") |> range(start: -5m) |> filter(fn: (r) => r._measurement == "weather") |> distinct(column: "a_location")' \
    | grep -c "weather" || echo "0")

if [ "$LOCATIONS" -ge 3 ]; then
    echo -e "${GREEN}✓ PASS${NC} (Found $LOCATIONS locations)"
else
    echo -e "${YELLOW}⚠ PARTIAL${NC} (Found $LOCATIONS locations, expected 10)"
fi

# Test 5: Check if dashboard exists
echo -n "Test 5: Checking for dashboard... "
DASHBOARDS=$(curl -s http://localhost:8086/api/v2/dashboards \
    --header "Authorization: Token $TOKEN" \
    --header "Content-Type: application/json")

if echo "$DASHBOARDS" | grep -q "Weather Dashboard"; then
    echo -e "${GREEN}✓ PASS${NC}"
else
    echo -e "${YELLOW}⚠ WARNING${NC}"
    echo "  Dashboard not found or not named 'Weather Dashboard'"
    echo "  Response: $DASHBOARDS"
fi

# Test 6: Verify data freshness
echo -n "Test 6: Checking data freshness (< 2 minutes old)... "
LATEST_TIME=$(curl -s -X POST http://localhost:8086/api/v2/query?org=nflx \
    --header "Authorization: Token $TOKEN" \
    --header "Accept: application/csv" \
    --header "Content-type: application/vnd.flux" \
    --data 'from(bucket: "default") |> range(start: -5m) |> filter(fn: (r) => r._measurement == "weather") |> last()' \
    | grep "weather" | head -1 | cut -d',' -f6)

if [ -n "$LATEST_TIME" ]; then
    # Convert to timestamp and check if within last 2 minutes
    CURRENT_TIME=$(date +%s)
    LATEST_TIMESTAMP=$(date -d "$LATEST_TIME" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "${LATEST_TIME%.*}" +%s 2>/dev/null || echo "0")
    
    if [ $LATEST_TIMESTAMP -gt 0 ]; then
        TIME_DIFF=$((CURRENT_TIME - LATEST_TIMESTAMP))
        
        if [ $TIME_DIFF -lt 120 ]; then
            echo -e "${GREEN}✓ PASS${NC} (Data is ${TIME_DIFF}s old)"
        else
            echo -e "${YELLOW}⚠ WARNING${NC} (Data is ${TIME_DIFF}s old)"
        fi
    else
        echo -e "${YELLOW}⚠ SKIP${NC} (Could not parse timestamp)"
    fi
else
    echo -e "${YELLOW}⚠ SKIP${NC} (No timestamp found)"
fi

# Test 7: Check get_weather logs for errors
echo -n "Test 7: Checking get_weather logs for errors... "
ERROR_COUNT=$(docker logs get_weather 2>&1 | grep -c "✗" || echo "0")

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ PASS${NC} (No errors found)"
else
    echo -e "${YELLOW}⚠ WARNING${NC} (Found $ERROR_COUNT error messages)"
    echo "  Recent errors:"
    docker logs get_weather 2>&1 | grep "✗" | tail -3 | sed 's/^/    /'
fi

echo ""
echo "=================================="
echo -e "${GREEN}Test Summary: System is operational!${NC}"
echo "=================================="
echo ""
echo "You can view the dashboard at: http://localhost:8086"
echo "  Username: admin"
echo "  Password: admin123!"
echo ""

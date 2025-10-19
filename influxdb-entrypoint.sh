#!/bin/bash
set -e

# Start InfluxDB in the background
/entrypoint.sh influxd &
INFLUXD_PID=$!

# Wait for InfluxDB to be ready
echo "Waiting for InfluxDB to be ready..."
until curl -sf http://localhost:8086/health > /dev/null 2>&1; do
    sleep 2
done
echo "✓ InfluxDB is ready"

# Wait a bit more for setup to complete
sleep 10

# Apply the dashboard template
echo "Setting up InfluxDB Weather Dashboard..."
echo "Getting organization ID..."
ORG_ID=$(influx org list --host http://localhost:8086 | grep nflx | awk '{print $1}')

if [ -z "$ORG_ID" ]; then
    echo "✗ Could not get organization ID"
    influx org list --host http://localhost:8086
else
    echo "✓ Found organization ID: $ORG_ID"
    echo "Applying dashboard template..."
    
    # Show what we're about to apply
    echo "Dashboard template content (first 500 chars):"
    head -c 500 /tmp/dashboard.yml
    echo ""
    echo "..."
    echo ""
    
    if influx apply -f /tmp/dashboard.yml --org-id $ORG_ID --host http://localhost:8086 --force true; then
        echo "✓ Dashboard template applied successfully!"
        echo "✓ Weather Dashboard is now available at http://localhost:8086"
        
        # Verify dashboard was created
        echo "Listing dashboards:"
        influx dashboards --host http://localhost:8086 --org-id $ORG_ID
    else
        echo "✗ Failed to apply dashboard template"
    fi
fi

# Wait for InfluxDB process to finish
wait $INFLUXD_PID

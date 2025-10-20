#!/usr/bin/env python3
"""
Weather fetcher using wttr.in JSON API
Uses only built-in Python libraries for portability
"""

import urllib.request
import urllib.parse
import json
import sys
import time
import os
from typing import Dict, Any

# Force unbuffered output for Docker logs
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Debug mode - controlled by environment variable
# Allows more detailed logging when enabled
DEBUG = os.getenv('DEBUG', '').lower() in ('true', '1', 'yes')

def debug_print(message: str):
    """Print debug message only if DEBUG mode is enabled"""
    if DEBUG:
        print(f"DEBUG: {message}")


def get_weather(location: str = "", format_type: str = "j1", max_retries: int = 3) -> Dict[str, Any]:
    """
    Fetch weather data from wttr.in JSON API with retry logic
    
    Args:
        location: Location to get weather for (empty string for auto-detection)
        format_type: Format type (j1 for current weather, j2 for forecast)
        max_retries: Maximum number of retry attempts
    
    Returns:
        Dictionary containing weather data
    """
    # Encode location for URL
    encoded_location = urllib.parse.quote(location)
    
    # Build the API URL
    base_url = "https://wttr.in"
    if encoded_location:
        url = f"{base_url}/{encoded_location}?format={format_type}"
    else:
        url = f"{base_url}?format={format_type}"
    
    for attempt in range(max_retries):
        try:
            # Make the request
            with urllib.request.urlopen(url, timeout=10) as response:
                data = response.read().decode('utf-8')
                return json.loads(data)
        
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"Attempt {attempt + 1} failed: {e}")
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Error fetching weather data after {max_retries} attempts: {e}")
                return {}
        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Attempt {attempt + 1} failed - JSON decode error: {e}")
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Error parsing JSON response after {max_retries} attempts: {e}")
                return {}
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Attempt {attempt + 1} failed - unexpected error: {e}")
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"Unexpected error after {max_retries} attempts: {e}")
                return {}
    
    return {}


def format_current_weather(weather_data: Dict[str, Any]) -> str:
    """
    Format current weather data for display
    
    Args:
        weather_data: Weather data from API
    
    Returns:
        Formatted weather string
    """
    if not weather_data or 'current_condition' not in weather_data:
        return "No weather data available"
    
    current = weather_data['current_condition'][0]
    nearest_area = weather_data.get('nearest_area', [{}])[0]
    
    # Location data
    location = nearest_area.get('areaName', [{'value': 'Unknown'}])[0]['value']
    country = nearest_area.get('country', [{'value': 'Unknown'}])[0]['value']
    latitude = nearest_area.get('latitude', 'N/A')
    longitude = nearest_area.get('longitude', 'N/A')
    
    # Temperature data
    temp_c = current.get('temp_C', 'N/A')
    temp_f = current.get('temp_F', 'N/A')
    
    # Calculate Kelvin temperature if Celsius is available
    temp_k = 'N/A'
    if temp_c != 'N/A':
        try:
            temp_k = str(float(temp_c) + 273.15)
        except (ValueError, TypeError):
            temp_k = 'N/A'
    
    # Weather conditions
    humidity = current.get('humidity', 'N/A')
    pressure = current.get('pressure', 'N/A')
    cloudcover = current.get('cloudcover', 'N/A')
    description = current.get('weatherDesc', [{'value': 'N/A'}])[0]['value']
    feels_like_c = current.get('FeelsLikeC', 'N/A')
    feels_like_f = current.get('FeelsLikeF', 'N/A')
    wind_speed = current.get('windspeedKmph', 'N/A')
    wind_dir = current.get('winddir16Point', 'N/A')
    visibility = current.get('visibility', 'N/A')
    
    weather_info = f"""
Location: {location}, {country}
Latitude: {latitude}
Longitude: {longitude}
Temperature (Celsius): {temp_c}°C
Temperature (Fahrenheit): {temp_f}°F
Temperature (Kelvin): {temp_k}K
Feels like: {feels_like_c}°C ({feels_like_f}°F)
Humidity: {humidity}%
Pressure: {pressure} hPa
Cloudcover: {cloudcover}%
Condition: {description}
Wind: {wind_speed} km/h {wind_dir}
Visibility: {visibility} km
"""
    
    return weather_info.strip()


def get_influxdb_token() -> str:
    """
    Get InfluxDB token from mounted env file
    
    Returns:
        InfluxDB token string, or empty string if not found
    """
    
    debug_print("Attempting to get InfluxDB token...")
    
    # First try environment variable (in case it's set directly)
    token = os.getenv('INFLUXDB_TOKEN', '')
    
    if token:
        print(f"✓ Found token in environment: {token[:10]}...{token[-4:] if len(token) > 14 else token}")
        return token
    
    # Try to read from the mounted env file (shared via Docker volume)
    token_file_path = "/tmp/extracted_token"
    
    debug_print(f"Looking for token file at: {token_file_path}")
    if DEBUG:
        print("DEBUG: Contents of /tmp/:")
        try:
            for item in os.listdir('/tmp/'):
                print(f"  - {item}")
        except Exception as e:
            print(f"  Error listing /tmp/: {e}")
    
    try:
        if os.path.exists(token_file_path):
            with open(token_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('INFLUXDB_TOKEN='):
                        token = line.split('=', 1)[1]
                        if token:
                            print(f"✓ Found token in env file: {token[:10]}...{token[-4:] if len(token) > 14 else token}")
                            return token
                        break
            print("✗ INFLUXDB_TOKEN not found in env file")
        else:
            print(f"✗ Token env file not found at {token_file_path}")
    except Exception as e:
        print(f"✗ Error reading token env file: {e}")
    
    return ""


def write_to_influxdb(weather_data: Dict[str, Any], location: str) -> bool:
    """
    Write weather data to InfluxDB using built-in libraries
    
    Args:
        weather_data: Weather data from API
        location: Location name for the measurement
    
    Returns:
        True if successful, False otherwise
    """
    # Get InfluxDB configuration from environment variables
    influxdb_url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
    influxdb_org = os.getenv('INFLUXDB_ORG', 'nflx')
    influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'default')
    
    # Get token dynamically with retry logic
    influxdb_token = ""
    max_token_retries = 5
    
    for attempt in range(max_token_retries):
        debug_print(f"Token retrieval attempt {attempt + 1}/{max_token_retries}")
        influxdb_token = get_influxdb_token()
        if influxdb_token:
            break
        else:
            if attempt < max_token_retries - 1:
                wait_time = 5 * (attempt + 1)  # 5s, 10s, 15s, 20s
                debug_print(f"Token retrieval failed, retrying in {wait_time} seconds...")
                time.sleep(wait_time)
    
    if not influxdb_token:
        print("✗ Could not authenticate with InfluxDB after multiple attempts, skipping write to database")
        return False
    
    if not weather_data or 'current_condition' not in weather_data:
        print("Warning: No weather data to write to InfluxDB")
        return False
    
    try:
        current = weather_data['current_condition'][0]
        nearest_area = weather_data.get('nearest_area', [{}])[0]
        
        # Extract data for InfluxDB
        location_name = nearest_area.get('areaName', [{'value': 'Unknown'}])[0]['value']
        country = nearest_area.get('country', [{'value': 'Unknown'}])[0]['value']
        latitude = nearest_area.get('latitude', '0')
        longitude = nearest_area.get('longitude', '0')
        
        # Convert and validate lat/lon
        try:
            lat_float = float(latitude) if latitude else 0.0
            lon_float = float(longitude) if longitude else 0.0
        except (ValueError, TypeError):
            print(f"✗ Invalid latitude/longitude values for {location}: lat={latitude}, lon={longitude}")
            lat_float = 0.0
            lon_float = 0.0
        
        # Convert ALL values to floats to avoid InfluxDB schema collisions
        if DEBUG:
            print(f"DEBUG: Raw weather data for {location}:")
            print(f"  temp_C: {current.get('temp_C', 'N/A')}")
            print(f"  humidity: {current.get('humidity', 'N/A')}")
            print(f"  pressure: {current.get('pressure', 'N/A')}")
        
        # Convert with better error handling
        try:
            temp_c = float(current.get('temp_C', 0)) if current.get('temp_C') else 0.0
            temp_f = float(current.get('temp_F', 0)) if current.get('temp_F') else 0.0
            temp_k = temp_c + 273.15 if temp_c != 0 else 273.15
            humidity = float(current.get('humidity', 0)) if current.get('humidity') else 0.0
            pressure = float(current.get('pressure', 0)) if current.get('pressure') else 0.0
            cloudcover = float(current.get('cloudcover', 0)) if current.get('cloudcover') else 0.0
            wind_speed = float(current.get('windspeedKmph', 0)) if current.get('windspeedKmph') else 0.0
            visibility = float(current.get('visibility', 0)) if current.get('visibility') else 0.0
            feels_like_c = float(current.get('FeelsLikeC', 0)) if current.get('FeelsLikeC') else 0.0
            feels_like_f = float(current.get('FeelsLikeF', 0)) if current.get('FeelsLikeF') else 0.0
            
            # Validate that we don't have any NaN or infinite values
            for name, value in [('temp_c', temp_c), ('temp_f', temp_f), ('temp_k', temp_k), 
                              ('humidity', humidity), ('pressure', pressure), ('cloudcover', cloudcover),
                              ('wind_speed', wind_speed), ('visibility', visibility), 
                              ('feels_like_c', feels_like_c), ('feels_like_f', feels_like_f)]:
                if not isinstance(value, (int, float)) or str(value).lower() in ['nan', 'inf', '-inf']:
                    print(f"✗ Invalid numeric value for {name}: {value}")
                    return False
                    
        except (ValueError, TypeError) as e:
            print(f"✗ Error converting weather values to float for {location}: {e}")
            return False
        
        # Get current timestamp in nanoseconds
        timestamp = int(time.time() * 1_000_000_000)
        
        # Escape strings for InfluxDB line protocol (can't use backslashes in f-strings)
        # More comprehensive escaping for InfluxDB line protocol
        def escape_tag_value(value):
            if not value or value == 'Unknown':
                return 'Unknown'
            return str(value).replace(' ', '\\ ').replace(',', '\\,').replace('=', '\\=').replace('"', '\\"')
        
        escaped_location = escape_tag_value(location_name)
        escaped_country = escape_tag_value(country)
        escaped_query = escape_tag_value(location)
        
        # Create InfluxDB line protocol format - ALL values as floats (no 'i' suffix)
        line_protocol = f"weather,a_location={escaped_location},country={escaped_country},query_location={escaped_query} temperature_celsius={temp_c},temperature_fahrenheit={temp_f},temperature_kelvin={temp_k},humidity={humidity},pressure={pressure},cloudcover={cloudcover},wind_speed_kmph={wind_speed},visibility_km={visibility},feels_like_celsius={feels_like_c},feels_like_fahrenheit={feels_like_f},latitude={lat_float},longitude={lon_float} {timestamp}"
        
        if DEBUG:
            print(f"DEBUG: Line protocol for {location}:")
            print(f"  {line_protocol[:200]}{'...' if len(line_protocol) > 200 else ''}")
        
        # Prepare the HTTP request to InfluxDB
        write_url = f"{influxdb_url}/api/v2/write?org={influxdb_org}&bucket={influxdb_bucket}&precision=ns"
        
        # Create the request
        req = urllib.request.Request(
            write_url,
            data=line_protocol.encode('utf-8'),
            headers={
                'Authorization': f'Token {influxdb_token}',
                'Content-Type': 'text/plain; charset=utf-8'
            },
            method='POST'
        )
        
        # Send the request
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 204:
                print(f"✓ Successfully wrote weather data for {location} to InfluxDB")
                return True
            else:
                print(f"✗ Failed to write to InfluxDB: HTTP {response.status}")
                return False
                
    except ValueError as e:
        print(f"✗ Data conversion error for {location}: {e}")
        return False
    except urllib.error.HTTPError as e:
        # Read the error response body for more details
        error_body = e.read().decode('utf-8') if hasattr(e, 'read') else 'No error details'
        print(f"✗ InfluxDB HTTP error for {location}: {e.code} {e.reason}")
        print(f"✗ Error details: {error_body}")
        print(f"✗ Line protocol being sent: {line_protocol}")
        return False
    except urllib.error.URLError as e:
        print(f"✗ InfluxDB connection error for {location}: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error writing to InfluxDB for {location}: {e}")
        return False


def main():
    """Main function to run the weather fetcher"""
    print("Weather Fetcher using wttr.in API")
    print("=" * 40)
    
    # Display InfluxDB configuration
    influxdb_url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
    influxdb_org = os.getenv('INFLUXDB_ORG', 'nflx')
    influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'default')
    influxdb_username = os.getenv('INFLUXDB_USERNAME', '')
    influxdb_password = os.getenv('INFLUXDB_PASSWORD', '')
    
    print(f"InfluxDB URL: {influxdb_url}")
    print(f"InfluxDB Org: {influxdb_org}")
    print(f"InfluxDB Bucket: {influxdb_bucket}")
    print(f"InfluxDB Auth: {'✓ Username/Password configured' if influxdb_username and influxdb_password else '✗ Missing credentials'}")
    print("=" * 40)
    
    # Default cities list
    default_cities = [
        "Nashville, TN",
        "Los Gatos, CA", 
        "San Francisco, CA",
        "London, UK",
        "Tokyo, JP",
        "Rome, IT",
        "Dublin, IE",
        "New York City, NY",
        "Seattle, WA",
        "Paris, FR"
    ]
    
    # Always use the hardcoded default cities
    locations_to_fetch = default_cities
    
    # Continuous polling loop
    poll_count = 1
    
    try:
        while True:
            print(f"\n{'#'*80}")
            print(f"WEATHER UPDATE #{poll_count}")
            print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'#'*80}")
            
            # Fetch and display weather for each location
            for i, location in enumerate(locations_to_fetch):
                if len(locations_to_fetch) > 1:
                    print(f"\n{'='*60}")
                    print(f"Location {i+1} of {len(locations_to_fetch)}")
                
                print(f"\nFetching weather for: {location}")
                print("Loading...")
                
                # Fetch weather data
                weather_data = get_weather(location)
                
                if weather_data:
                    print("\n" + format_current_weather(weather_data))
                    
                    # Write to InfluxDB
                    write_success = write_to_influxdb(weather_data, location)
                    if not write_success:
                        print(f"Note: Weather data display successful but database write failed for {location}")
                else:
                    print(f"Failed to fetch weather data for {location}")
                
                # Add a small delay between requests to be respectful to the API
                if i < len(locations_to_fetch) - 1:
                    time.sleep(1)
            
            poll_count += 1
            print(f"\n{'='*80}")
            print("Waiting 30 seconds before next update...")
            print(f"{'='*80}")
            
            # Wait 30 seconds before next poll
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\nShutting down weather fetcher...")
        print("Goodbye!")


if __name__ == "__main__":
    main()
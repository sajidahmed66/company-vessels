#!/bin/bash

# MagicPort Fleet Data Scraper with Anti-Detection
# Usage: ./magicport_scraper.sh [company-url]

# Configuration
BASE_URL="https://magicport.ai"
COMPANY_URL="${1:-https://magicport.ai/owners-managers/malaysia/sin-soon-hock-sdn-bhd}"
COOKIES_FILE="magicport_cookies.txt"
USER_AGENT="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}MagicPort Fleet Data Scraper${NC}"
echo "=================================="

# Step 0: Visit homepage first to establish session
echo "Step 0: Establishing session..."
curl -s -c "$COOKIES_FILE" -b "$COOKIES_FILE" \
  "https://magicport.ai/" \
  -H "User-Agent: $USER_AGENT" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8" \
  -H "Accept-Language: en-US,en;q=0.9" \
  -H "Cache-Control: max-age=0" \
  -H "Sec-Fetch-Dest: document" \
  -H "Sec-Fetch-Mode: navigate" \
  -H "Sec-Fetch-Site: none" \
  -H "Sec-Fetch-User: ?1" \
  -H "Upgrade-Insecure-Requests: 1" \
  --compressed > /dev/null

sleep 2

# Step 1: Get the company page
echo "Step 1: Fetching company page..."

RESPONSE=$(curl -s -c "$COOKIES_FILE" -b "$COOKIES_FILE" \
  "$COMPANY_URL" \
  -H "User-Agent: $USER_AGENT" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8" \
  -H "Accept-Language: en-US,en;q=0.9" \
  -H "Cache-Control: max-age=0" \
  -H "Referer: https://magicport.ai/" \
  -H "Sec-Fetch-Dest: document" \
  -H "Sec-Fetch-Mode: navigate" \
  -H "Sec-Fetch-Site: same-origin" \
  -H "Sec-Fetch-User: ?1" \
  -H "Upgrade-Insecure-Requests: 1" \
  --compressed)

# Extract CSRF token
CSRF_TOKEN=$(echo "$RESPONSE" | grep -o 'name="csrf-token" content="[^"]*"' | head -1 | sed 's/.*content="//;s/"//')

if [ -z "$CSRF_TOKEN" ]; then
    echo -e "${RED}Error: Could not extract CSRF token${NC}"
    exit 1
fi

echo -e "${GREEN}CSRF Token extracted: ${CSRF_TOKEN:0:20}...${NC}"

# Extract fleet route
FLEET_ROUTE=$(echo "$RESPONSE" | grep -o 'data-route="[^"]*fleets"' | sed 's/data-route="//;s/"//')

if [ -z "$FLEET_ROUTE" ]; then
    echo -e "${RED}Error: Could not find fleet data route${NC}"
    exit 1
fi

echo -e "${GREEN}Fleet route: $FLEET_ROUTE${NC}"

# Step 2: Wait and simulate human behavior
sleep 3

# Step 3: Make more realistic AJAX call
echo "Step 2: Fetching fleet data with enhanced headers..."

FLEET_RESPONSE=$(curl -s -X POST "$FLEET_ROUTE" \
  -H "Accept: application/json, text/javascript, */*; q=0.01" \
  -H "Accept-Language: en-US,en;q=0.9" \
  -H "Content-Type: application/x-www-form-urlencoded; charset=UTF-8" \
  -H "Origin: $BASE_URL" \
  -H "Referer: $COMPANY_URL" \
  -H "User-Agent: $USER_AGENT" \
  -H "X-CSRF-TOKEN: $CSRF_TOKEN" \
  -H "X-Requested-With: XMLHttpRequest" \
  -H "Sec-Fetch-Dest: empty" \
  -H "Sec-Fetch-Mode: cors" \
  -H "Sec-Fetch-Site: same-origin" \
  -H "DNT: 1" \
  -H "Sec-GPC: 1" \
  -c "$COOKIES_FILE" -b "$COOKIES_FILE" \
  --data-raw "draw=1&columns%5B0%5D%5Bdata%5D=0&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&start=0&length=25&search%5Bvalue%5D=&search%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=asc" \
  --compressed)

# Check response
if echo "$FLEET_RESPONSE" | jq . >/dev/null 2>&1; then
    ERROR_CHECK=$(echo "$FLEET_RESPONSE" | jq -r '.error // empty')

    if [ "$ERROR_CHECK" = "Attack !" ]; then
        echo -e "${RED}Anti-bot protection triggered. Trying alternative approach...${NC}"

        # Try with minimal parameters
        sleep 5
        FLEET_RESPONSE=$(curl -s -X POST "$FLEET_ROUTE" \
          -H "Accept: application/json" \
          -H "Content-Type: application/x-www-form-urlencoded" \
          -H "Referer: $COMPANY_URL" \
          -H "User-Agent: $USER_AGENT" \
          -H "X-CSRF-TOKEN: $CSRF_TOKEN" \
          -H "X-Requested-With: XMLHttpRequest" \
          -c "$COOKIES_FILE" -b "$COOKIES_FILE" \
          --data "draw=1&start=0&length=10")

        ERROR_CHECK=$(echo "$FLEET_RESPONSE" | jq -r '.error // empty' 2>/dev/null)
    fi

    if [ "$ERROR_CHECK" = "Attack !" ]; then
        echo -e "${RED}Still being blocked. This endpoint likely requires subscription access.${NC}"
        echo "Response: $FLEET_RESPONSE"
    else
        echo -e "${GREEN}Success! Fleet data retrieved${NC}"
        echo "$FLEET_RESPONSE" | jq .

        FILENAME="fleet_data_$(date +%Y%m%d_%H%M%S).json"
        echo "$FLEET_RESPONSE" | jq . > "$FILENAME"
        echo -e "${GREEN}Data saved to $FILENAME${NC}"
    fi
else
    echo -e "${RED}Invalid JSON response${NC}"
    echo "Response: $FLEET_RESPONSE"
fi

# Cleanup
rm -f "$COOKIES_FILE"
echo "Script completed."

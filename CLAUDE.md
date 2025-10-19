# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Magiport-SC is a maritime data scraping system that collects shipping company and vessel information from multiple sources. The system primarily scrapes data from MagicPort.ai and VesselFinder.com, storing it in a MySQL database. It's built with Python 3.13+ using Playwright for browser automation and BeautifulSoup for HTML parsing.

## Database Architecture

The system uses MySQL with the following key databases:
- `magic_port_updated` - Main production database for scraped company data
- `magic_port_final` - Database for vessel validation and processing

Key tables:
- `companies_directory2` - Company directory with URLs and metadata
- `vessel_companies` - Detailed company information
- `company_fleet_vessels` - Fleet data linked to companies
- `vessels` - Individual vessel records
- `vessel_validation_tracking` - Validation processing logs

## Core Modules

### Company Scraping (`company/`)
- **`action.py`** - Main company processing script with batch processing loop
- **`singel_company.py`** - Enhanced scraper for individual companies with full fleet data
- **`company_validate.py`** - Vessel validation and company relationship correction

### Vessel Scraping (`vessel/`)
- **`vessel_scrap.py`** - VesselFinder scraper for detailed vessel information

### Utilities
- **`company_dict/main.py`** - Batch company directory scraper by country
- **`ports/all_ports.py`** - Port information scraper from VesselFinder
- **`expected_arrivals/eta.py`** - ETA/navigation data scraper

## Common Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Activate virtual environment (if using)
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
```

### Running Scrapers

**Single Company Processing:**
```bash
python company/action.py
```

**Company Directory Batch Processing:**
```bash
python company_dict/main.py
```

**Vessel Data Scraping:**
```bash
python vessel/vessel_scrap.py
```

**Vessel Validation:**
```bash
python company/company_validate.py
```

**Port Data Scraping:**
```bash
python ports/vessel_finder_port.py
```

**ETA Data Extraction:**
```bash
python expected_arrivals/eta.py
```

### Database Operations

The scrapers automatically connect to MySQL using credentials in the scripts. Default configuration:
- Host: localhost
- User: root
- Password: rootpassword
- Database: magic_port_updated (for company data)

## Architecture Notes

### Anti-Detection Measures
- Playwright browser automation with stealth measures
- Realistic user agents and viewport settings
- Session establishment on homepage before target pages
- Rate limiting and human-like behavior simulation
- CSRF token extraction for AJAX requests

### Error Handling & Logging
- Failed companies are logged to `logs/failed_companies_YYYYMMDD.log`
- Validation logs saved as JSON timestamps
- Automatic status updates to prevent infinite retry loops
- Graceful handling of redirects and 404 errors

### Data Processing Flow
1. **Company Discovery**: Scrape company directories by country
2. **Company Detail Extraction**: Process individual companies for fleet data
3. **Vessel Validation**: Correct company relationships and missing data
4. **Data Enrichment**: Add port information, ETA data, etc.

### Key Design Patterns
- **DatabaseManager class**: Centralized DB operations with connection pooling
- **Async/Await**: All scrapers use async patterns for performance
- **Batch Processing**: Scripts process data in configurable batches
- **JSON Backup**: All scraped data saved as timestamped JSON files
- **Tracking Tables**: Validation and processing status tracked in database

## Testing Data

The system includes several SQL files for testing:
- `companies_directory2.sql` - Company directory test data
- `vessel_companies.sql` - Vessel company test data
- `vessels.sql` - Individual vessel test records

## Configuration Notes

- Browser headless mode enabled by default (use `--visible` flag for debugging)
- Batch sizes configurable in individual scripts
- Database credentials hardcoded in scripts (consider environment variables for production)
- Logging automatically creates `logs/` directory as needed
- Fleet data saved to `fleet_data/` directory as JSON backup

## Development Workflow

1. **Database Setup**: Ensure MySQL is running and databases are created
2. **Initial Data Load**: Import provided SQL files for test data
3. **Run Directory Scraper**: Populate company directory with `company_dict/main.py`
4. **Process Companies**: Run `company/action.py` for detailed scraping
5. **Validate Data**: Execute `company/company_validate.py` to correct relationships
6. **Monitor Logs**: Check `logs/` directory for failed companies and validation results
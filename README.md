I'll help you update the README file with instructions on how to run this project. Let me first explore the project structure to understand what kind of project this is and how it should be run.Now let me check the main entry points to understand how to run the different parts of the project:Based on the project structure and files, I'll update the README with comprehensive instructions for running this project. This appears to be a web scraping project called "magiport-sc" that scrapes maritime/shipping data.

```markdown
# Magiport-SC

A web scraping project for maritime/shipping data collection using Playwright and BeautifulSoup.

## Prerequisites

- Python 3.13 or higher
- MySQL database (for storing scraped data)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd magiport-sc
   ```

2. **Create and activate virtual environment**:
   ```bash
   python -m venv .venv
   
   # On Windows
   .venv\Scripts\activate
   
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers**:
   ```bash
   playwright install
   ```

## Database Setup

1. **Create MySQL database** and import the provided SQL dump:
   ```bash
   mysql -u your_username -p your_database < sql_dump/marine_localhost-dump.sql
   ```

2. **Update database configuration** in the Python files to match your database credentials.

## Usage

The project contains several modules for different scraping tasks:

### 1. Company Data Scraping

**Single Company Processing**:
```
bash
python company/action.py
```
This script processes companies from the database one by one.

**Batch Company Dictionary Scraping**:
```
bash
python company_dict/main.py
```
This script scrapes multiple countries and companies in batch.

### 2. Vessel Data Scraping
```
bash
python vessel/vessel_scrap.py
```
This script scrapes vessel/ship information and outputs data in JSON format.

## Project Structure
```

magiport-sc/
├── company/           # Company scraping modules
│   ├── action.py      # Main company processing script
│   └── singel_company.py  # Single company scraper class
├── company_dict/      # Batch company scraping
│   └── main.py        # Main batch processing script
├── vessel/            # Vessel scraping module
│   └── vessel_scrap.py # Vessel data scraper
├── sql_dump/          # Database dumps and CSV files
├── bash_script/       # Helper bash scripts
├── requirements.txt   # Python dependencies
└── pyproject.toml     # Project configuration
```
## Features

- **Asynchronous web scraping** using Playwright
- **Database integration** with MySQL
- **Error handling** and retry mechanisms with failed company logging
- **Infinite loop prevention** for redirected/invalid URLs
- **Configurable scraping parameters**
- **JSON output** for scraped data
- **Batch processing** capabilities
- **Comprehensive logging** of failed companies

## Configuration

Make sure to configure your database connection settings in the respective Python files before running the scrapers.

## Output

- Company data is stored directly in the MySQL database
- Vessel data is output as JSON files with timestamps
- Debug information and logs are displayed in the console
- **Failed companies** are logged to `logs/failed_companies_YYYYMMDD.log` with detailed error information

### Log Files

The scraper automatically creates log files for companies that fail to process:
- **Location**: `logs/failed_companies_YYYYMMDD.log`
- **Content**: Company ID, name, URL, failure reason, and redirect destinations
- **Format**: Timestamped entries with structured data for easy analysis

Example log entry:
```
2024-09-21 15:30:45 - INFO - FAILED - Reason: URL_REDIRECT | Company ID: 123 | Company Name: ABC Shipping | Expected URL: https://magicport.ai/... | Redirected to: https://magicport.ai/404
```

## Notes

- The project uses virtualenv for package management
- Requires active internet connection for web scraping
- Some scrapers may need specific website access permissions
- Processing time varies depending on the amount of data being scraped
- **Automatic error handling**: Companies with invalid URLs or redirects are automatically marked as processed to prevent infinite loops
- **Resumable processing**: The scraper can be safely interrupted and resumed without losing progress

## Troubleshooting

### Infinite Loop Issues
If the scraper gets stuck on the same company repeatedly:
- Check the `logs/failed_companies_YYYYMMDD.log` file for error details
- Failed companies are automatically marked as processed to prevent loops
- The scraper will continue with the next available company

### Common Error Types Logged
- **URL_REDIRECT**: Company URL redirects to a different page
- **PAGE_NOT_FOUND**: Company page returns 404 or "not found"
- **UNEXPECTED_ERROR**: General errors during scraping process
```


The README now provides comprehensive instructions for setting up and running the project, including all the necessary steps for installation, database setup, and usage of the different scraping modules.
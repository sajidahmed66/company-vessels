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
- **Error handling** and retry mechanisms
- **Configurable scraping parameters**
- **JSON output** for scraped data
- **Batch processing** capabilities

## Configuration

Make sure to configure your database connection settings in the respective Python files before running the scrapers.

## Output

- Company data is stored directly in the MySQL database
- Vessel data is output as JSON files with timestamps
- Debug information and logs are displayed in the console

## Notes

- The project uses virtualenv for package management
- Requires active internet connection for web scraping
- Some scrapers may need specific website access permissions
- Processing time varies depending on the amount of data being scraped
```


The README now provides comprehensive instructions for setting up and running the project, including all the necessary steps for installation, database setup, and usage of the different scraping modules.
from bs4 import BeautifulSoup
import requests
import re
import time
from urllib.parse import urljoin, urlparse


def scrape_multiple_countries(countries):
    base_url = "https://magicport.ai/owners-managers"
    all_results = {}

    for country_code in countries:
        print(f"\n=== Scraping {country_code} ===")

        first_page_url = f"{base_url}?country[]={country_code}"

        total_pages = get_total_pages(first_page_url)
        print(f"Found {total_pages} total pages for {country_code}")

        country_hrefs = set()

        # Scrape all pages for this country
        for page in range(1, total_pages + 1):
            if page == 1:
                current_url = first_page_url
            else:
                current_url = f"{first_page_url}&page={page}"

            print(f"Scraping {country_code} page {page}/{total_pages}...")

            page_hrefs = get_data_from_page(current_url)
            country_hrefs.update(page_hrefs)

            time.sleep(1)

        all_results[country_code] = list(country_hrefs)
        print(f"Found {len(country_hrefs)} companies for {country_code}")

        # Save results for this country
        filename = f"magicport_links_{country_code.replace('%', '').replace('C3%A5', 'aland')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for href in country_hrefs:
                f.write(href + '\n')
        print(f"Saved to {filename}")

    return all_results


def main():
    print("Starting Magicport scraper...")

    # Option 1: Scrape single country
    # all_hrefs = get_all_data()

    # Save to file
    # with open('magicport_links.txt', 'w', encoding='utf-8') as f:
    #     for href in all_hrefs:
    #         f.write(href + '\n')
    #
    # print(f"Found {len(all_hrefs)} matching links")
    # print("Links saved to magicport_links.txt")

    # Option 2: Uncomment to scrape multiple countries
    countries = [
        "%C3%A5land-islands",  # Åland Islands
        "albania",
        "algeria",
        "argentina"
    ]
    all_results = scrape_multiple_countries(countries)


def get_all_data():
    """Scrape all pages and collect matching hrefs"""
    base_url = "https://magicport.ai/owners-managers"
    all_matching_hrefs = set()  # Use set to avoid duplicates

    # Start with the first page
    current_url = f"{base_url}?country[]=%C3%A5land-islands"
    page = 1

    while current_url:
        print(f"Scraping page {page}...")

        # Get hrefs from current page
        page_hrefs = get_data_from_page(current_url)
        all_matching_hrefs.update(page_hrefs)

        current_url = get_next_page_url(current_url, page)
        page += 1

        # Add delay to be respectful
        time.sleep(1)

    return list(all_matching_hrefs)


def get_total_pages(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        response.raise_for_status()
        print(response.raise_for_status())

        soup = BeautifulSoup(response.text, "html.parser")

        # Find the pagination container
        pagination_container = soup.find('ul', class_='pagination')

        if not pagination_container:
            return 1  # Only one page if no pagination

        # Find all pagination links
        pagination_items = pagination_container.find_all('li', class_='pagination__item')

        max_page = 1
        for item in pagination_items:

            link = item.find('a', class_='pagination__item-link')
            if link and link.get('href'):
                page_match = re.search(r'page=(\d+)', link['href'])
                if page_match:
                    page_num = int(page_match.group(1))
                    max_page = max(max_page, page_num)

            span = item.find('span', class_='pagination__item-link--active')
            if span and span.text.strip().isdigit():
                page_num = int(span.text.strip())
                max_page = max(max_page, page_num)

        return max_page

    except requests.RequestException as e:
        print(f"Error getting total pages: {e}")
        return 1


def get_data_from_page(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Find all 'a' tags
        items = soup.find_all('a', href=True)

        matching_hrefs = []
        pattern = r'^https://magicport\.ai/owners-managers/[^/]+/[^/]+/?$'

        for item in items:
            href = item.get('href')
            if href:
                absolute_url = urljoin(url, href)

                if re.match(pattern, absolute_url):
                    matching_hrefs.append(absolute_url)
                    print(f"Found: {absolute_url}")

        print(f"Found {len(matching_hrefs)} matching links on this page")
        return matching_hrefs

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []

def get_next_page_url(current_url, current_page):
    """
    Try to find the next page URL
    This function handles different pagination patterns
    """
    try:
        response = requests.get(current_url, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Method 1: Look for a "Next" button/link
        next_button = soup.find('a', {'class': re.compile(r'next', re.I)})
        if next_button and next_button.get('href'):
            return urljoin(current_url, next_button['href'])

        # Method 2: Look for pagination links
        pagination_links = soup.find_all('a', href=re.compile(r'page=\d+'))
        if pagination_links:
            # Find the highest page number
            max_page = 0
            for link in pagination_links:
                href = link.get('href', '')
                page_match = re.search(r'page=(\d+)', href)
                if page_match:
                    page_num = int(page_match.group(1))
                    max_page = max(max_page, page_num)

            # If current page is less than max page, go to next
            if current_page < max_page:
                next_page = current_page + 1
                if 'page=' in current_url:
                    return re.sub(r'page=\d+', f'page={next_page}', current_url)
                else:
                    separator = '&' if '?' in current_url else '?'
                    return f"{current_url}{separator}page={next_page}"

        # Method 3: Try incrementing page parameter directly
        if current_page == 1:  # First attempt
            separator = '&' if '?' in current_url else '?'
            test_url = f"{current_url}{separator}page=2"

            # Test if page 2 exists
            test_response = requests.get(test_url, timeout=10)
            if test_response.status_code == 200:
                test_soup = BeautifulSoup(test_response.text, "html.parser")
                # Check if page has content (adjust selector based on site structure)
                content = test_soup.find_all('a', href=True)
                if content:
                    return test_url

        return None  # No more pages

    except requests.RequestException:
        return None


def check_pattern_examples():
    """Test the regex pattern with examples"""
    pattern = r'^https://magicport\.ai/owners-managers/[^/]+/[^/]+/?$'

    test_urls = [
        "https://magicport.ai/owners-managers/%C3%A5land-islands/lundqvist-rederierna-ab",
        "https://magicport.ai/owners-managers/country/company",
        "https://magicport.ai/owners-managers/",
        "https://magicport.ai/owners-managers/only-one-part",
        "https://magicport.ai/other-section/country/company"
    ]

    print("Pattern testing:")
    for url in test_urls:
        matches = bool(re.match(pattern, url))
        print(f"{url} -> {matches}")


if __name__ == "__main__":
    # Uncomment to test pattern
    # check_pattern_examples()

    main()

import requests
from bs4 import BeautifulSoup
import json


def extract_table_data(html_content):
    """
    Parses HTML content to extract specific table data into a dictionary.
    This function is reused from the previous solution.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    result = {}

    # Helper function to find a table by its caption text
    def find_table_by_caption(caption_text):
        caption = soup.find('caption', string=lambda text: text and caption_text in text)
        return caption.find_parent('table') if caption else None

    # 1. Extract Port Information table
    port_info_table = find_table_by_caption('Port Information')
    if port_info_table:
        port_info = {}
        for row in port_info_table.find_all('tr'):
            header = row.find('th')
            if header:
                key = header.text.strip()
                cell = row.find('td')

                # Special handling for the 'Port Usage' progress bar
                if key == 'Port Usage':
                    progress_bars = cell.find_all('span', class_='progress-bar__track')
                    port_usage = {}
                    for bar in progress_bars:
                        # Extract class name (e.g., 'progress-bar__track--cargo')
                        usage_type = bar.get('class', [])[1].replace('progress-bar__track--', '')
                        # Extract width percentage from style attribute
                        width = bar.get('style', '').replace('width: ', '').replace(';', '')
                        port_usage[usage_type] = width
                    port_info[key] = port_usage
                else:
                    value = cell.text.strip()
                    port_info[key] = value
        result['Port Information'] = port_info

    # 2. Extract Depths table
    depths_table = find_table_by_caption('Depths')
    if depths_table:
        depths = {}
        for row in depths_table.find_all('tr'):
            header = row.find('th')
            if header:
                key = header.text.strip()
                value = row.find('td').text.strip()
                depths[key] = value
        result['Depths'] = depths

    # 3. Extract Nearby Ports table
    nearby_ports_table = find_table_by_caption('Nearby Ports')
    if nearby_ports_table:
        nearby_ports = []
        tbody = nearby_ports_table.find('tbody')
        if tbody:
            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    port_link = cells[0].find('a')
                    if port_link:
                        port_data = {
                            'code': port_link.text.strip(),
                            'name': port_link.get('title', '').strip(),
                            'coordinates': cells[1].text.strip()
                        }
                        nearby_ports.append(port_data)
        result['Nearby Ports'] = nearby_ports

    # 4. Extract Port Characteristics table
    port_char_table = find_table_by_caption('Port Characteristics')
    if port_char_table:
        port_characteristics = {}
        for row in port_char_table.find_all('tr'):
            header = row.find('th')
            if header:
                key = header.text.strip()
                value = row.find('td').text.strip()
                port_characteristics[key] = value
        result['Port Characteristics'] = port_characteristics

    return result


def extract_table_data_from_url(url):
    """
    Fetches HTML from a URL and extracts table data.
    """
    try:
        # Set headers to mimic a browser visit
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # Make the HTTP request with a timeout
        response = requests.get(url, headers=headers, timeout=15)

        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        print("Successfully fetched HTML content.")

        # Parse the fetched HTML
        return extract_table_data(response.text)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None


# --- Main execution ---
if __name__ == "__main__":
    # The URL provided in the request
    target_url = "https://magicport.ai/ports/jordan/%27aqaba-port-joaqb"

    print(f"Attempting to fetch data from: {target_url}\n")

    # Extract data from the live URL
    extracted_data = extract_table_data_from_url(target_url)

    if extracted_data:
        print("Data extraction successful. Converting to JSON...")

        # Convert the dictionary to a JSON formatted string
        json_data = json.dumps(extracted_data, indent=2, ensure_ascii=False)

        # Print the JSON to the console
        print("\n--- Extracted JSON Data ---")
        print(json_data)

        # Save the JSON data to a file
        output_filename = 'port_data_from_url.json'
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(json_data)
            print(f"\nData successfully saved to '{output_filename}'")
        except IOError as e:
            print(f"\nError: Could not write to file '{output_filename}'. Reason: {e}")

    else:
        print("Failed to extract data. The script will now exit.")

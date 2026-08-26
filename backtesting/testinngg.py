import requests
from bs4 import BeautifulSoup


def decode_secret_message(url):
    # Download the published Google Doc
    response = requests.get(url)
    response.raise_for_status()

    # Parse the HTML
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the table containing the character coordinates
    table = soup.find("table")

    if table is None:
        raise ValueError("Could not find the data table in the Google Doc.")

    points = []

    # Read the rows
    for row in table.find_all("tr")[1:]:
        cells = row.find_all(["td", "th"])

        if len(cells) >= 3:
            x = int(cells[0].get_text(strip=True))
            character = cells[1].get_text(strip=True)
            y = int(cells[2].get_text(strip=True))

            points.append((x, y, character))

    if not points:
        raise ValueError("No coordinate data found.")

    # Find the dimensions of the grid
    max_x = max(x for x, y, character in points)
    max_y = max(y for x, y, character in points)

    # Create the grid and fill it with spaces
    grid = [
        [" " for _ in range(max_x + 1)]
        for _ in range(max_y + 1)
    ]

    # Place each character at its coordinate
    for x, y, character in points:
        grid[max_y - y][x] = character

    # Print the completed grid
    for row in grid:
        print("".join(row).rstrip())


# YOUR VERIFICATION DOCUMENT
url = "https://docs.google.com/document/d/e/2PACX-1vSvM5gDlNvt7npYHhp_XfsJvuntUhq184By5xO_pA4b_gCWeXb6dM6ZxwN8rE6S4ghUsCj2VKR21oEP/pub"

# Run the decoder
decode_secret_message(url)
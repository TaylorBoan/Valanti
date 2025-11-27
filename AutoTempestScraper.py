import asyncio
import os
import time
from pickle import LIST

import pandas as pd
from playwright.async_api import async_playwright

CAR_MODELS_CSV = "./Car Models/cars.csv"
LISTING_URL_CSV = "./Car Models/listing_urls.csv"
MAX_PAGES_PER_MODEL = 1000


async def main():
    # Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100,
        )
        page = await browser.new_page()

        # Load seen IDs from existing CSV if it exists
        seen_ids = set()
        if os.path.exists(LISTING_URL_CSV):
            try:
                existing_df = pd.read_csv(LISTING_URL_CSV)
                if "id" in existing_df.columns:
                    seen_ids = set(existing_df["id"].dropna().tolist())
                else:
                    print("No 'id' column found in CSV")

                # Printing the number of found ids
                print(f"Loaded {len(seen_ids)} seen IDs from {LISTING_URL_CSV}")
                print(f"Found {len(seen_ids)} seen IDs from {LISTING_URL_CSV}")

            except Exception as e:
                print(f"Error loading {LISTING_URL_CSV}: {e}")

        # For each car model we will scrape price trends data
        # Getting each car model from the CSV file
        # Each row has a "Make" and "Model" feature
        df = pd.read_csv(CAR_MODELS_CSV)

        # Creating a list of car models
        car_models = df["Model"].tolist()

        # Creating a list of car makes
        car_makes = df["Make"].tolist()

        # Creating a list of car models and makes
        car_models_makes = list(zip(car_makes, car_models))

        for car in car_models_makes:
            print(f"\n=== Starting scraping for {car[0]} {car[1]} ===")
            # ---------------- Navigate to a car listings for each make and model ----------------
            await page.goto("https://www.autotempest.com/")
            await page.wait_for_timeout(500)

            # Selecting the "Price Trends Option"
            await page.locator('li[data-id="price-trends-main"]').click()
            await page.wait_for_timeout(300)

            # Now we will input the car model and make
            await page.locator("#trends-make-input").fill(car[0])
            await page.locator("#trends-make-input").press("Enter")
            await page.wait_for_timeout(300)
            await page.locator("#trends-model-input").fill(car[1])
            await page.locator("#trends-model-input").press("Enter")
            await page.wait_for_timeout(300)

            # Clicking the Search button
            await page.get_by_role("button", name="Search").first.click()
            await page.wait_for_timeout(1000)

            print("Search button pressed")

            # Wait for the page to load
            await page.wait_for_timeout(2000)

            # Switching from sample data to all data
            # The button has text "Sampled Data"
            await page.locator("text=Sampled Data").click()
            await page.wait_for_timeout(500)

            # Set the slider to 100%
            slider = page.locator('span[role="slider"]')
            await slider.focus()
            await slider.press("End")
            await page.wait_for_timeout(500)

            num_more_results = 0
            while num_more_results < MAX_PAGES_PER_MODEL:
                local_results = []
                # ---------------- Getting a list of all listings ----------------
                # Getting a list of car items
                # Wait for results to update (instead of just sleep)
                try:
                    await page.wait_for_selector(
                        ".ResultItem_cardWrap__tA63Q", timeout=10000
                    )  # 10s wait for at least one result
                except:
                    print(f"Initial results failed to load for {car[0]} {car[1]}")
                    continue  # Skip this model
                car_elements = page.locator(".ResultItem_cardWrap__tA63Q")
                cars = await car_elements.all()

                # ---------------- Extract the URL from each listing ----------------
                for car_elem in cars:
                    # Getting the URL for each listing to be saved and then visited later:
                    link_elem = car_elem.locator("h3 a")  # Find <a> inside <h3>
                    href = await link_elem.get_attribute("href")
                    listing_url = f"https://www.autotempest.com{href}" if href else None
                    listing_id = await car_elem.locator("..").get_attribute("id")

                    if (
                        listing_id in seen_ids
                        or len(local_results) >= MAX_PAGES_PER_MODEL
                    ):
                        # print(f"Skipping already seen ID: {listing_id}")
                        continue

                    # parent_html = await car_elem.locator("..").inner_html()
                    # print(
                    #     f"Parent HTML snippet: {parent_html[:500]}..."
                    # )  # First 500 chars to see the id and structure

                    print(f"Listing ID: {listing_id}")
                    print(f"Listing URL: {listing_url}")
                    print("\n")

                    local_results.append({"id": listing_id, "url": listing_url})
                    seen_ids.add(listing_id)

                # Writing the data to a file
                if local_results:
                    header = not os.path.exists(LISTING_URL_CSV)
                    pd.DataFrame(local_results).to_csv(
                        LISTING_URL_CSV, mode="a", header=header, index=False
                    )
                    print(
                        f"Saved {len(local_results)} new listings to {LISTING_URL_CSV}"
                    )

                # Now that we have gotten the listings on this page we will get the listings on the next page
                # by clicking the "More Results" button
                # Check for "More Results" button
                more_button = page.get_by_role("button", name="More Results").first
                if (
                    not await more_button.is_visible()
                    or not await more_button.is_enabled()
                ):
                    print("More Results button not visible/enabled. Stopping.")
                    break  # Exit if button is hidden or missing

                # Click the button and robustly wait for more results to load
                prev_count = await page.locator(".ResultItem_cardWrap__tA63Q").count()
                await more_button.click()
                await page.wait_for_timeout(1000)  # Short pause for human-like behavior
                try:
                    await page.wait_for_function(
                        "(arg) => document.querySelectorAll(arg.sel).length > arg.prev",
                        {"sel": ".ResultItem_cardWrap__tA63Q", "prev": prev_count},
                        timeout=10000,
                    )
                except Exception as e:
                    print(f"No new results detected after clicking More Results: {e}")
                    break
                num_more_results += 1
            # Wait for the page to load
            await page.wait_for_timeout(5000)

    # Close browser
    await browser.close()


# Run the async function
asyncio.run(main())

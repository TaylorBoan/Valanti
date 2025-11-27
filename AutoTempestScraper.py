import asyncio
import os
import random

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
            await page.wait_for_timeout(random.randint(700, 1400))

            # Selecting the "Price Trends Option"
            await page.locator('li[data-id="price-trends-main"]').click()
            await page.wait_for_timeout(random.randint(500, 1000))

            # Now we will input the car model and make
            await page.locator("#trends-make-input").fill(car[0])
            await page.locator("#trends-make-input").press("Enter")
            await page.wait_for_timeout(random.randint(400, 900))
            await page.locator("#trends-model-input").fill(car[1])
            await page.locator("#trends-model-input").press("Enter")
            await page.wait_for_timeout(random.randint(400, 900))

            # Clicking the Search button
            await page.get_by_role("button", name="Search").first.click()
            await page.wait_for_timeout(random.randint(1200, 2000))

            print("Search button pressed")

            # Wait for the page to load
            await page.wait_for_timeout(random.randint(2500, 4000))

            # Switching from sample data to all data (if present)
            # The button has text "Sampled Data"
            sampled_btn = page.locator("text=Sampled Data")
            if await sampled_btn.is_visible():
                await sampled_btn.click()
                await page.wait_for_timeout(random.randint(600, 1200))
            else:
                print("Sampled Data toggle not visible; continuing with defaults.")

            # Set the slider to 100%
            slider = page.locator('span[role="slider"]')
            await slider.focus()
            await slider.press("End")
            await page.wait_for_timeout(random.randint(600, 1200))

            # Per-model tracking counters
            num_more_results = 0
            processed_count = 0
            saved_this_model = 0
            skipped_no_id = 0
            skipped_no_href = 0
            skipped_duplicates = 0
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
                    break  # Stop pagination for this model
                car_elements = page.locator(".ResultItem_cardWrap__tA63Q")
                cars = await car_elements.all()

                # ---------------- Extract the URL from each listing ----------------
                for car_elem in cars:
                    # Getting the URL for each listing to be saved and then visited later:
                    link_elem = car_elem.locator("h3 a")  # Find <a> inside <h3>
                    href = await link_elem.get_attribute("href")
                    listing_url = f"https://www.autotempest.com{href}" if href else None
                    listing_id = await car_elem.locator("..").get_attribute("id")

                    processed_count += 1

                    # Guard: missing ID
                    if not listing_id:
                        skipped_no_id += 1
                        print("Skipping listing: missing id")
                        continue

                    # Guard: missing href/url
                    if not href:
                        skipped_no_href += 1
                        print(f"Skipping listing {listing_id}: missing href")
                        continue

                    # Duplicate check
                    if listing_id in seen_ids:
                        skipped_duplicates += 1
                        print(f"Skipping duplicate listing id={listing_id}")
                        continue

                    # parent_html = await car_elem.locator("..").inner_html()
                    # print(
                    #     f"Parent HTML snippet: {parent_html[:500]}..."
                    # )  # First 500 chars to see the id and structure

                    print(f"Listing ID: {listing_id}")
                    print(f"Listing URL: {listing_url}")
                    print("\n")

                    local_results.append(
                        {
                            "make": car[0],
                            "model": car[1],
                            "id": listing_id,
                            "url": listing_url,
                        }
                    )
                    seen_ids.add(listing_id)

                # Writing the data to a file
                if local_results:
                    # Ensure output directory exists
                    os.makedirs(os.path.dirname(LISTING_URL_CSV), exist_ok=True)
                    header = not os.path.exists(LISTING_URL_CSV)
                    pd.DataFrame(local_results).to_csv(
                        LISTING_URL_CSV, mode="a", header=header, index=False
                    )
                    saved_this_model += len(local_results)
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
                await page.wait_for_timeout(
                    random.randint(1200, 2500)
                )  # Short pause for human-like behavior
                try:
                    await page.wait_for_function(
                        "(arg) => document.querySelectorAll(arg.sel).length > arg.prev",
                        arg={"sel": ".ResultItem_cardWrap__tA63Q", "prev": prev_count},
                        timeout=10000,
                    )
                except Exception as e:
                    print(f"No new results detected after clicking More Results: {e}")
                    break
                num_more_results += 1
            # Per-model summary logging
            print(
                f"Summary for {car[0]} {car[1]} -> processed: {processed_count}, saved: {saved_this_model}, skipped_no_id: {skipped_no_id}, skipped_no_href: {skipped_no_href}, skipped_duplicates: {skipped_duplicates}, more_results_clicks: {num_more_results}"
            )
            await page.wait_for_timeout(random.randint(6000, 9000))

    # Close browser
    await browser.close()


# Run the async function
asyncio.run(main())

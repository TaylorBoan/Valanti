import asyncio
import os
import random
import time

import pandas as pd
from playwright.async_api import async_playwright

CAR_MODELS_CSV = "./Car Models/cars.csv"
LISTING_URL_CSV = "./Car Models/listing_urls.csv"
MAX_PAGES_PER_MODEL = 1000
MAX_HARVEST_BUFFER = 15000  # cap for in-memory id buffer
# SAFE_OVERLAP removed; DOM processing is now target-id driven via network responses


async def main():
    # Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100,
        )
        page = await browser.new_page()
        page.set_default_timeout(15000)

        # Session-level metrics
        session_start = time.time()
        session_seen_count = 0

        # Load seen URLs from existing CSV if it exists
        seen_urls = set()
        if os.path.exists(LISTING_URL_CSV):
            try:
                existing_df = pd.read_csv(LISTING_URL_CSV)
                if "url" in existing_df.columns:
                    seen_urls = set(existing_df["url"].dropna().tolist())
                else:
                    print("No 'url' column found in CSV")

                # Printing the number of found urls
                print(f"Loaded {len(seen_urls)} seen URLs from {LISTING_URL_CSV}")

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
        total_models = len(car_models_makes)

        for model_index, car in enumerate(car_models_makes, start=1):
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


                print(
                    f"[Session] Elapsed: {elapsed:.2f}s | Listings seen: {session_seen_count} | Time/listing: {time_per_listing:.2f}s"
                )
            # Per-model summary logging
            print(
                f"Summary for {car[0]} {car[1]} -> processed: {processed_count}, saved: {saved_this_model}, skipped_no_id: {skipped_no_id}, skipped_no_href: {skipped_no_href}, skipped_duplicates: {skipped_duplicates}, more_results_clicks: {num_more_results}"
            )
            # Progress bar for models
            bar_width = 30
            filled = int(bar_width * model_index / total_models) if total_models else 0
            bar = "#" * filled + "-" * (bar_width - filled)
            print(f"[Progress] [{bar}] {model_index}/{total_models} models completed")
            await page.wait_for_timeout(random.randint(6000, 9000))

    # Close browser
    await browser.close()


# Run the async function
asyncio.run(main())

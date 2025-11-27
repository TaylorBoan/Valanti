import asyncio
import time

import pandas as pd
from playwright.async_api import async_playwright


async def main():
    # Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=100,
        )
        page = await browser.new_page()

        # For each car model we will scrape price trends data
        # Getting each car model from the CSV file
        # Each row has a "Make" and "Model" feature
        df = pd.read_csv("./Car Models/cars.csv")

        # Creating a list of car models
        car_models = df["Model"].tolist()

        # Creating a list of car makes
        car_makes = df["Make"].tolist()

        # Creating a list of car models and makes
        car_models_makes = [(make, model) for make in car_makes for model in car_models]

        for car in car_models_makes:
            # Navigate to a car listings site (example: cars.com)
            await page.goto("https://www.autotempest.com/")

            # Selecting the "Price Trends Option"
            await page.locator('li[data-id="price-trends-main"]').click()

            # Now we will input the car model and make
            await page.locator("#trends-make-input").fill(car[0])
            await page.locator("#trends-make-input").press("Enter")
            await page.locator("#trends-model-input").fill(car[1])
            await page.locator("#trends-model-input").press("Enter")

            # Clicking the Search button
            await page.get_by_role("button", name="Search").first.click()

            print("Search button pressed")

            # Wait for the page to load
            time.sleep(2)

            # Switching from sample data to all data
            # The button has text "Sampled Data"
            await page.locator("text=Sampled Data").click()

            # Set the slider to 100%
            slider = page.locator('span[role="slider"]')
            await slider.focus()
            await slider.press("End")

            # Wait for the page to load
            time.sleep(5)
            await browser.close()

        # Close browser
        await browser.close()


# Run the async function
asyncio.run(main())

import asyncio
from playwright.async_api import async_playwright

async def main():
    # Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Navigate to a car listings site (example: cars.com)
        await page.goto("https://www.cars.com/shopping/")

        # Wait for content to load
        await page.wait_for_selector(".vehicle-card")

        # Extract car listings (example selectors, may need adjustment based on site)
        listings = await page.query_selector_all(".vehicle-card")
        for listing in listings:
            title = await listing.query_selector(".vehicle-header-make-model")
            price = await listing.query_selector(".primary-price")
            mileage = await listing.query_selector(".listing-mileage")

            if title:
                title_text = await title.inner_text()
                price_text = await price.inner_text() if price else "N/A"
                mileage_text = await mileage.inner_text() if mileage else "N/A"

                print(f"Title: {title_text}, Price: {price_text}, Mileage: {mileage_text}")

        # Close browser
        await browser.close()

# Run the async function
asyncio.run(main())

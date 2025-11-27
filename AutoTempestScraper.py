import asyncio

from playwright.async_api import async_playwright


async def main():
    # Launch browser
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Navigate to a car listings site (example: cars.com)
        await page.goto("https://www.cars.com/shopping/")

        #

        # Close browser
        await browser.close()


# Run the async function
asyncio.run(main())

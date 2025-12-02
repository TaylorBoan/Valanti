import marimo

__generated_with = "0.17.6"
app = marimo.App(width="medium")


@app.cell
def _():
    import pandas as pd
    return (pd,)


@app.cell
def _(pd):
    # Opening the listing_urls.csv with pandas
    listing_urls = pd.read_csv('Car Models/listing_urls.csv', low_memory=False)
    return (listing_urls,)


@app.cell
def _(listing_urls):
    # Priting the total number of rows in the CSV file
    print(listing_urls.shape[0])
    return


@app.cell
def _(listing_urls):
    # Viewing the number of rows for each Model
    listing_urls['model'].value_counts()
    return


@app.cell
def _(listing_urls):
    # Printing all of the columns in the csv file
    print(listing_urls.columns)
    return


@app.cell
def _(listing_urls):
    # Printing all of the unique values in the "model" column
    print(listing_urls.model.unique())
    return


@app.cell
def _(listing_urls):
    listing_urls.head()
    return


@app.cell
def _(listing_urls):
    # Printing all of the rows where the vin is equal to a particular value
    listing_urls[listing_urls['vin'] == "ZHWCT3ZD5HLA06070"]
    return


@app.cell
def _(listing_urls_vin):
    listing_urls_vin["ctime"].value_counts()
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()

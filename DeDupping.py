import pandas as pd
import os

# CONFIGURABLE PATH VARIABLE
CSV_FILE_PATH = 'data.csv'  # Replace with your actual CSV file path

def remove_duplicates(file_path):
    """
    Loads a CSV file, removes duplicate rows, and saves the cleaned data back to the file.
    """
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    try:
        print(f"Loading data from {file_path}...")
        df = pd.read_csv(file_path)
        
        original_count = len(df)
        print(f"Original row count: {original_count}")

        # Remove duplicates
        df_cleaned = df.drop_duplicates()
        
        cleaned_count = len(df_cleaned)
        duplicates_removed = original_count - cleaned_count
        
        print(f"Cleaned row count: {cleaned_count}")
        print(f"Duplicates removed: {duplicates_removed}")

        if duplicates_removed > 0:
            print(f"Saving cleaned data to {file_path}...")
            df_cleaned.to_csv(file_path, index=False)
            print("Done.")
        else:
            print("No duplicates found. File not modified.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    remove_duplicates(CSV_FILE_PATH)

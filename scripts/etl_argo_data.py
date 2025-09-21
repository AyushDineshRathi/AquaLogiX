import os
import xarray as xr
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pandas as pd

# --- 1. CONFIGURATION & DATABASE CONNECTION ---
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file.")
engine = create_engine(DATABASE_URL)

# --- 2. DATA EXTRACTION & TRANSFORMATION ---
def process_argo_file(file_path):
    """
    Extracts, transforms, and loads data from a single ARGO .nc file
    into the PostgreSQL database.
    """
    try:
        with xr.open_dataset(file_path) as ds:
            # --- Extract Float Metadata ---
            wmo_id = int(ds['PLATFORM_NUMBER'].values[0])
            project_name = ds.attrs.get('project_name', 'N/A')
            launch_date = pd.to_datetime(ds['JULD'].values[0])
            print(f"Processing float WMO ID: {wmo_id}")

            with engine.connect() as connection:
                # --- Insert Float Metadata ---
                insert_float_query = text("""
                    INSERT INTO argo_floats (wmo_id, launch_date, project_name)
                    VALUES (:wmo_id, :launch_date, :project_name)
                    ON CONFLICT (wmo_id) DO NOTHING;
                """)
                connection.execute(insert_float_query, {
                    "wmo_id": wmo_id, "launch_date": launch_date, "project_name": project_name
                })
                
                get_float_id_query = text("SELECT id FROM argo_floats WHERE wmo_id = :wmo_id;")
                result = connection.execute(get_float_id_query, {"wmo_id": wmo_id}).fetchone()
                if result is None:
                    print(f"Error: Could not retrieve float ID for WMO {wmo_id}")
                    return
                float_id = result[0]
                
                # --- FIX: Check which variables are available before extracting ---
                available_vars = list(ds.data_vars)
                vars_to_extract = ['JULD', 'LATITUDE', 'LONGITUDE', 'PRES']
                
                # Conditionally add optional measurement variables if they exist
                if 'TEMP' in available_vars:
                    vars_to_extract.append('TEMP')
                if 'PSAL' in available_vars:
                    vars_to_extract.append('PSAL')

                # --- Extract Measurement Data ---
                measurements_df = ds[vars_to_extract].to_dataframe().reset_index()
                
                # Rename columns to match our database schema
                rename_map = {
                    'PRES': 'pressure', 'TEMP': 'temperature', 'PSAL': 'salinity',
                    'JULD': 'timestamp', 'LATITUDE': 'latitude', 'LONGITUDE': 'longitude'
                }
                measurements_df.rename(columns=rename_map, inplace=True)
                
                measurements_df['float_id'] = float_id
                measurements_df['timestamp'] = pd.to_datetime(measurements_df['timestamp'], errors='coerce')
                
                # Ensure our essential columns exist before dropping NAs
                required_cols = ['timestamp', 'pressure']
                measurements_df.dropna(subset=required_cols, inplace=True)
                
                # --- Load Measurement Data into Database ---
                if not measurements_df.empty:
                    # Select only the columns that exist in our database table
                    db_cols = [col for col in ['float_id', 'timestamp', 'latitude', 'longitude', 'pressure', 'temperature', 'salinity'] if col in measurements_df.columns]
                    
                    measurements_df[db_cols].to_sql(
                        'measurements', con=connection, if_exists='append', index=False
                    )
                    print(f"Successfully loaded {len(measurements_df)} measurements for float {wmo_id}")
                else:
                    print(f"No valid measurement data found for float {wmo_id}")

                connection.commit()

    except Exception as e:
        print(f"An error occurred while processing {file_path}: {e}")

# --- 3. MAIN EXECUTION ---
if __name__ == "__main__":
    raw_data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
    for filename in os.listdir(raw_data_dir):
        if filename.endswith('.nc'):
            file_path = os.path.join(raw_data_dir, filename)
            process_argo_file(file_path)
    print("\nETL process completed.")
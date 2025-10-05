import os
import xarray as xr
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file.")
engine = create_engine(DATABASE_URL)

def process_argo_file(file_path):
    """
    Reads a .nc file, transforms the data, and loads it into the PostgreSQL database.
    """
    try:
        with xr.open_dataset(file_path) as ds:
            # --- 2. Transform: Convert to DataFrame and standardize ---
            df = ds.to_dataframe().reset_index()
            df.columns = [col.lower() for col in df.columns]

            # --- 3. Extract Float-level Metadata ---
            wmo_id = int(df['platform_number'].iloc[0])
            print(f"Processing float WMO ID: {wmo_id}")
            
            project_name = df['project_name'].iloc[0].decode('utf-8').strip() if 'project_name' in df else 'N/A'
            pi_name = df['pi_name'].iloc[0].decode('utf-8').strip() if 'pi_name' in df else 'N/A'
            launch_date = pd.to_datetime(df['juld'].iloc[0])

            with engine.connect() as connection:
                # --- 4. Load Float Metadata ---
                insert_float_query = text("""
                    INSERT INTO argo_floats (wmo_id, project_name, pi_name, launch_date)
                    VALUES (:wmo_id, :project_name, :pi_name, :launch_date)
                    ON CONFLICT (wmo_id) DO UPDATE SET
                        project_name = EXCLUDED.project_name,
                        pi_name = EXCLUDED.pi_name;
                """)
                connection.execute(insert_float_query, {
                    "wmo_id": wmo_id, "project_name": project_name,
                    "pi_name": pi_name, "launch_date": launch_date
                })

                get_float_id_query = text("SELECT id FROM argo_floats WHERE wmo_id = :wmo_id;")
                float_id = connection.execute(get_float_id_query, {"wmo_id": wmo_id}).scalar_one()

                # --- 5. Extract and Clean Measurement Data ---
                source_cols = ['juld', 'latitude', 'longitude', 'pres_adjusted', 'temp_adjusted', 'psal_adjusted']
                target_cols = ['timestamp', 'latitude', 'longitude', 'pressure', 'temperature', 'salinity']

                # Check if all required adjusted columns exist
                if not all(col in df.columns for col in source_cols):
                    print(f"  -> Skipping: File is missing one or more adjusted data columns.")
                    return

                measurements_df = df[source_cols].copy()
                measurements_df.columns = target_cols # Rename columns
                measurements_df['float_id'] = float_id
                
                # Convert timestamp and clean data
                measurements_df['timestamp'] = pd.to_datetime(measurements_df['timestamp'])
                measurements_df.dropna(subset=['pressure', 'temperature', 'salinity'], inplace=True)

                # --- 6. Load Measurements into Database ---
                if not measurements_df.empty:
                    measurements_df.to_sql('measurements', con=connection, if_exists='append', index=False)
                    print(f"  -> Successfully loaded {len(measurements_df)} measurements.")
                
                connection.commit()

    except Exception as e:
        print(f"An error occurred while processing {file_path}: {e}")

# --- Main Execution Block ---
if __name__ == "__main__":
    raw_data_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
    print("Starting ETL process...")
    for filename in os.listdir(raw_data_dir):
        if filename.endswith('.nc'):
            file_path = os.path.join(raw_data_dir, filename)
            process_argo_file(file_path)
    print("\nETL process completed.")
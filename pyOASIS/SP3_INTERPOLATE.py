import sys
import re
from datetime import datetime
import pandas as pd
import os

def SP3intp(year,doy,input_folder,output_folder):

    # Regular expressions for data analysis
    pattern_datetime = r"\*\s+(\d{4})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2}\.\d{8})"
    pattern_data = r"([A-Z]{2}\d{2})\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)"
    
    # Constructing the full path to the data folder
    path_ = input_folder
    
    # Final list for all the data (without interpolation)
    satellite_data = []
    
    # Defining the key date in dd-mm-yyyy format
    key_date = datetime.strptime(f"{doy}/{year}", "%j/%Y").strftime("%d-%m-%Y")
    
    # Check directory existence and process files if it exists.
    # Filter the candidate file list to entries that match the requested
    # (year, doy) by filename — typical names embed the date as either
    # `<YYYY><DOY>` (e.g. `GBM0MGXRAP_20230790000_01D_05M_ORB.SP3`) or as
    # GPS week+day-of-week (`gbmWWWWD.sp3`). Avoids a quadratic blow-up
    # when the orbit dir accumulates many days' worth of SP3 files: instead
    # of parsing every file and discarding non-matching dates, we open
    # only the file we actually need.
    year_doy = f"{int(year)}{int(doy):03d}"
    if os.path.exists(path_):
        candidates = [f for f in os.listdir(path_) if f.endswith(".SP3")]
        targeted = [f for f in candidates if year_doy in f]
        # Fall back to scanning all files only if no name matched — keeps
        # backward-compat with archives that use unconventional naming.
        files_to_scan = targeted if targeted else candidates
        for file in files_to_scan:
            if file.endswith(".SP3"):
                file_path = os.path.join(path_, file)
                print()
                print(f"Processing file: {file_path}")
    
                # Opens the file and reads its lines
                with open(file_path, "r") as file:
                    for line in file:
                        # Extracts date and time if the line matches the pattern
                        if re.match(pattern_datetime, line):
                            match = re.match(pattern_datetime, line)
                            file_year, month, day, hour, minute = (int(match.group(i)) for i in range(1, 6))
                            second = float(match.group(6))
                            last_date_time = datetime(file_year, month, day, hour, minute, int(second))
    
                            # Skips the line if the date is greater than the key date
                            if last_date_time.date() > datetime.strptime(key_date, "%d-%m-%Y").date():
                                continue
    
                        # Checks if the line has satellite data
                        elif re.match(pattern_data, line):
                            match = re.match(pattern_data, line)
                            satellite_name, x, y, z = match.groups()
    
                            # Adds the current record to the satellite data (without interpolation)
                            satellite_data.append({
                                'Date': last_date_time.strftime("%d-%m-%Y"),
                                'Time': last_date_time.strftime("%H:%M:%S"),
                                'Satellite': satellite_name,
                                'X': x,
                                'Y': y,
                                'Z': z
                            })
    
        # Creating a DataFrame with the original data (without interpolation)
        df_satellite = pd.DataFrame(satellite_data)
        df_satellite = df_satellite.sort_values(by=['Satellite', 'Date', 'Time'])
    
        # Removes rows with dates different from the key date
        df_satellite = df_satellite[df_satellite['Date'] == key_date]
    
        # Saves the data to the file. Write to a sibling temp path then
        # atomically rename so a kill mid-write leaves no half-baked
        # orbit table that the resume logic would mistake for "done".
        output_file_name = os.path.join(output_folder, f'ORBITS_{year}_{doy}.SP3')
        tmp_path = output_file_name + '.tmp'
        df_satellite.to_csv(tmp_path, sep='\t', index=False)
        os.replace(tmp_path, output_file_name)
        print()
        print(f"Processed tabular data saved to: {output_file_name}")

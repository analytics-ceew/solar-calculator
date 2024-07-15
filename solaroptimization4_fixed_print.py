#import required python library
import logging
import calendar
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
from io import BytesIO
from PIL import Image
import base64
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import plotly.graph_objects as go

# Helper function to convert time in "HH:MM A.M./P.M." format to slot-based format
def time_to_slot(time_str, n):
    time_parts = time_str.strip().split()
    hh_mm = time_parts[0].split(':')
    period = time_parts[1] if len(time_parts) > 1 else 'A.M.'  # Default to 'A.M.' if period is missing

    hour = int(hh_mm[0])
    minute = int(hh_mm[1])

    if period == 'P.M.' and hour != 12:
        hour += 12
    elif period == 'A.M.' and hour == 12:
        hour = 0

    total_minutes = hour * 60 + minute

    # Adjust minutes to align with the nearest slot boundary
    adjusted_minutes = total_minutes // (60 // n) * (60 // n)

    slot = adjusted_minutes // (60 // n)

    return slot

# Validate outage time blocks
def validate_time_blocks(time_blocks, n):
    try:
        max_slots = 24 * n
        for block in time_blocks:
            start, end = block.split('-')
            start_slot = time_to_slot(start, n)
            end_slot = time_to_slot(end, n)
            
            # Handle crossing midnight scenario
            if start_slot >= max_slots or end_slot >= max_slots or start_slot < 0 or end_slot < 0:
                return False
    except Exception as e:
        print(e)
        return False
    return True

# Function to generate time options based on interval
def generate_time_options(n):
    times = []
    if n == 1:  # Hourly slots
        times = [f"{hour:02d}:00 A.M." if hour < 12 else (f"{hour-12:02d}:00 P.M." if hour != 12 else "12:00 P.M.") for hour in range(24)]
    elif n == 2:  # 30 min slots
        times = [f"{hour:02d}:{minute:02d} A.M." if hour < 12 else (f"{hour-12:02d}:{minute:02d} P.M." if hour != 12 else f"12:{minute:02d} P.M.") for hour in range(24) for minute in [0, 30]]
    elif n == 4:  # 15 min slots
        times = [f"{hour:02d}:{minute:02d} A.M." if hour < 12 else (f"{hour-12:02d}:{minute:02d} P.M." if hour != 12 else f"12:{minute:02d} P.M.") for hour in range(24) for minute in [0, 15, 30, 45]]
    return times

# Function to get outage schedule
def get_outage_schedule(n):
    outage_schedule = {}
    months = ['January', 'February', 'March', 'April', 'May', 'June', 
              'July', 'August', 'September', 'October', 'November', 'December']

    frequency_choices = [
        "No outage", "Daily", "Weekly two days", "Weekly three days",
        "Once in a month", "Twice a month", "Thrice a month"
    ]

    # Get common outage frequency and time blocks
    st.write("Select common outage frequency:")
    common_frequency = st.selectbox("Outage frequency", frequency_choices)

    time_options = generate_time_options(n)
    
    common_time_blocks = []
    if common_frequency != "No outage":
        st.write("Select outage time block:")
        start_time = st.selectbox(f"Start time block ", time_options, key=f"common_start")
        end_time = st.selectbox(f"End time block", time_options, key=f"common_end")
        if start_time and end_time:
            common_time_blocks = [f"{start_time}-{end_time}"]

    # Collecting data from user for each month with default settings
    for month in months:
        outage_frequency = common_frequency
        outage_time_blocks = common_time_blocks

        if outage_frequency == "No outage":
            outage_days = []
        elif outage_frequency == "Daily":
            outage_days = list(range(1, calendar.monthrange(2023, months.index(month) + 1)[1] + 1))
        elif outage_frequency == "Weekly two days":
            outage_days = [3, 5, 10, 12, 15, 17, 22, 24]
        elif outage_frequency == "Weekly three days":
            outage_days = [1, 3, 5, 8, 10, 13, 15, 17, 19, 23, 25, 27]
        elif outage_frequency == "Once in a month":
            outage_days = [15]
        elif outage_frequency == "Twice a month":
            outage_days = [14, 27]
        elif outage_frequency == "Thrice a month":
            outage_days = [8, 17, 24]

        outage_schedule[month] = {
            'frequency': outage_frequency,
            'days': outage_days,
            'time_blocks': outage_time_blocks
        }

    # Optional Overrides for each month
    use_optional_timeblocks = st.checkbox("Use Optional Inputs? (yes/no)", key='optionaltime')
    with st.expander("Optional Inputs:"):
        for month in months:
            st.write(f"\nEnter outage details for {month}:")
            frequency_choice = st.selectbox(f"Outage frequency for {month}", frequency_choices, key=month)
            month_time_blocks = []
            if frequency_choice != "No outage":
                st.write(f"Select outage time blocks for {month}:")
                start_time = st.selectbox(f"Start time block for {month}", time_options, key=f"{month}_start")
                end_time = st.selectbox(f"End time block for {month}", time_options, key=f"{month}_end")
                if start_time and end_time:
                    month_time_blocks = [f"{start_time}-{end_time}"]

            if frequency_choice == 'Daily':
                outage_days = list(range(1, calendar.monthrange(2023, months.index(month) + 1)[1] + 1))
            elif frequency_choice == 'Weekly two days':
                outage_days = [3, 5, 10, 12, 15, 17, 22, 24]
            elif frequency_choice == 'Weekly three days':
                outage_days = [1, 3, 5, 8, 10, 13, 15, 17, 19, 23, 25, 27]
            elif frequency_choice == 'Once in a month':
                outage_days = [15]
            elif frequency_choice == 'Twice a month':
                outage_days = [14, 27]
            elif frequency_choice == 'Thrice a month':
                outage_days = [8, 17, 24]
            else:
                outage_days = []

            if use_optional_timeblocks:
                outage_schedule[month] = {
                    'frequency': frequency_choice,
                    'days': outage_days,
                    'time_blocks': month_time_blocks
                }

    return outage_schedule

## Function to define outage schedule
def generate_outage_status(outage_schedule, months, n):
    # Calculate the number of time slots per hour
    slots_per_hour = n
    total_slots = 24 * slots_per_hour

    # Initialize a list to store outage status for each time slot of the year
    yearly_outage_status = []

    # Iterate over each month in the year
    for month, data in outage_schedule.items():
        # Get outage frequency for the month
        outage_frequency = data['frequency']

        # Get outage days for the month
        outage_days = data.get('days', [])

        # Get outage time blocks for the month
        outage_time_blocks = data['time_blocks']

        # Extend yearly_outage_status with outage status for the month
        for day in range(1, calendar.monthrange(2023, months.index(month) + 1)[1] + 1):
            if day in outage_days:
                for slot in range(total_slots):
                    for block in outage_time_blocks:
                        start, end = block.split('-')
                        start_slot = time_to_slot(start, n)
                        end_slot = time_to_slot(end, n)
                        
                        # Handle crossing midnight scenario and 24-hour outage
                        if start_slot == end_slot or start_slot <= slot < end_slot or (end_slot < start_slot and (slot >= start_slot or slot < end_slot)):
                            yearly_outage_status.append(1)
                            break
                    else:
                        yearly_outage_status.append(0)
            else:
                for _ in range(total_slots):
                    yearly_outage_status.append(0)

    # Ensure that the number of slots is correct for the entire year

    expected_slots_per_year = 365 * total_slots
    yearly_outage_status = yearly_outage_status[:expected_slots_per_year]
    
    return yearly_outage_status

# List of months for iteration
months = ['January', 'February', 'March', 'April', 'May', 'June', 
          'July', 'August', 'September', 'October', 'November', 'December']

# Display the options
st.write("Select an option for data pattern:")
options = ["Hourly time block", "30 min time block", "15 min time block"]

# Create a selectbox for the options
time_block_option = st.selectbox("Choose a time block option:", options)

# Determine the value of 'n' based on the selection
if time_block_option == "Hourly time block":
    n = 1

elif time_block_option == "30 min time block":
    n = 2

elif time_block_option == "15 min time block":
    n = 4

req_length=8760*n


#Define function to calculate the monthly index from hourly data for net-metering

def calculate_month_key(index):
    if 0 <= index <= (743 *n +(n-1)):
        return 1  # January
    elif (743 *n +(n-1)) < index <= (1415 * n +(n-1)):
        return 2  # February
    elif (1415 * n+(n-1)) < index <= (2159 * n+(n-1)):
        return 3  # March
    elif (2159 * n+(n-1)) < index <= (2879 * n+(n-1)):
        return 4  # April
    elif (2879 * n+(n-1)) < index <= (3623 * n+(n-1)):
        return 5  # May
    elif (3623 * n+(n-1)) < index <= (4343 * n+(n-1)):
        return 6  # June
    elif (4343 * n+(n-1)) < index <= (5087 * n+(n-1)):
        return 7  # July
    elif (5087 * n+(n-1)) < index <= (5831 * n+(n-1)):
        return 8  # August
    elif (5831 * n+(n-1)) < index <= (6551 * n+(n-1)):
        return 9  # September
    elif (6551 * n+(n-1)) < index <= (7295 * n+(n-1)):
        return 10  # October
    elif (7295 * n+(n-1)) < index <= (8015 * n+(n-1)):
        return 11  # November
    elif (8015 * n+(n-1)) < index <= (8759 * n+(n-1)):
        return 12  # December

#Define function for net-metering calculation mechanism
def calculate_billing(units):
    banked_units = 0
    billing_units = []

    for month, unit in enumerate(units):
        if unit >= 0:
            if unit <= banked_units:
                banked_units -= unit
                billing_units.append(0)
            else:
                billing_units.append(unit - banked_units)
                banked_units = 0
        else:
            banked_units += abs(unit)
            billing_units.append(0)
        
        #print(f"Month {month+1}: Unit = {unit}, Banked = {banked_units}, Billed = {billing_units[-1]}")

    return billing_units, banked_units

# Define a function to format a number into Indian currency format
def format_indian_currency(amount):
    # Convert the amount to a string with commas for thousands separator
    formatted_amount = "{:,.0f}".format(amount)
    # Add the Indian Rupee symbol before the amount
    formatted_amount = "₹" + formatted_amount
    return formatted_amount

# Define tariff rates for each state and consumer category

tariff_rates = {
    'Andhra Pradesh - Visakhapatnam': {
        'residential': 5.58,  # Tariff rate for residential consumers in Maharashtra
        'industrial': 6.3,   # Tariff rate for industrial consumers in Maharashtra
        'commercial': 7.65,   # Tariff rate for commercial consumers in Maharashtra
        # Add more categories if needed
    },
    'Assam - Guwahati': {
        'residential': 6.66,  # Tariff rate for residential consumers in Gujarat
        'industrial': 7.05,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 7.9,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Bihar - Patna': {
        'residential': 8.59,  # Tariff rate for residential consumers in Gujarat
        'industrial': 7.98,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 7.73,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Chandigarh - Chandigarh': {
        'residential': 3.50,  # Tariff rate for residential consumers in Gujarat
        'industrial': 4.60,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 5.50,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Chhattisgarh - Bilaspur': {
        'residential': 4.30,  # Tariff rate for residential consumers in Gujarat
        'industrial': 7.45,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 8.25,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Chhattisgarh - Raipur': {
        'residential': 4.30,  # Tariff rate for residential consumers in Gujarat
        'industrial': 7.45,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 8.25,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Delhi - Delhi': {
        'residential': 3.50,  # Tariff rate for residential consumers in Gujarat
        'industrial': 7.75,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 8.50,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Goa - Goa': {
        'residential':2.80 ,  # Tariff rate for residential consumers in Gujarat
        'industrial': 5.75,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 5.10,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Gujarat - Ahmedabad': {
        'residential':4.03 ,  # Tariff rate for residential consumers in Gujarat
        'industrial': 4.0,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 4.65,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Gujarat - Rajkot': {
        'residential':4.03 ,  # Tariff rate for residential consumers in Gujarat
        'industrial': 4.0,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 4.65,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Haryana - Faridabad': {
        
       'residential': 4.18 ,  # Tariff rate for residential consumers in Gujarat
        'industrial': 6.95,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.65    # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Himachal Pradesh - Shimla': {
        'residential':4.90 ,  # Tariff rate for residential consumers in Gujarat
        'industrial': 5.76,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.42,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Jammu and Kashmir - Srinagar': {
        'residential':3.20 ,  # Tariff rate for residential consumers in Gujarat
        'industrial': 3.85 ,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 5.45,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Jharkhand - Ranchi': {
        'residential':6.30 ,  # Tariff rate for residential consumers in Gujarat
        'industrial': 5.85 ,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.65,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Karnataka - Bengaluru': {
        'residential':5.9,  # Tariff rate for residential consumers in Gujarat
        'industrial':8.0  ,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 5.45,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Karnataka - Mangalore': {
        'residential':5.9,  # Tariff rate for residential consumers in Gujarat
        'industrial':8.0  ,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 5.45,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Kerala - Kochi': {
        'residential':6.40,  # Tariff rate for residential consumers in Gujarat
        'industrial':6.40  ,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 7.58,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Kerala - Thrissur': {
        'residential':6.40,  # Tariff rate for residential consumers in Gujarat
        'industrial':6.40  ,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 7.58,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Madhya Pradesh - Bhopal': {
        'residential':5.76,  # Tariff rate for residential consumers in Gujarat
        'industrial':6.60  ,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.30,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Madhya Pradesh - Indore': {
        'residential':6.40,  # Tariff rate for residential consumers in Gujarat
        'industrial':6.40  ,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 7.58,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Madhya Pradesh - Jabalpur': {
        'residential':6.40,  # Tariff rate for residential consumers in Gujarat
        'industrial':6.40  ,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 7.58,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Maharashtra - Aurangabad': {
        'residential':7.90,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.36,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 12.23,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Maharashtra - Mumbai': {
        'residential':7.90,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.36,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 12.23,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Maharashtra - Navi Mumbai': {
        'residential':7.90,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.36,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 12.23,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

     'Maharashtra - Pune': {
        'residential':7.90,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.36,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 12.23,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Odisha - Bhubaneswar': {
        'residential':4.83,  # Tariff rate for residential consumers in Gujarat
        'industrial':  7.6,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 9.85,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

     'Odisha - Cuttack': {
        'residential':4.83,  # Tariff rate for residential consumers in Gujarat
        'industrial':  7.6,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 9.85,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

     'Punjab - Amritsar': {
        'residential':6.5,  # Tariff rate for residential consumers in Gujarat
        'industrial':  6.7,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 7.3,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

     'Rajasthan - Bikaner': {
        'residential':6.63,  # Tariff rate for residential consumers in Gujarat
        'industrial':  6.5,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 8.2,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

     'Rajasthan - Jaipur': {
        'residential':6.63,  # Tariff rate for residential consumers in Gujarat
        'industrial':  6.5,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 8.2,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Rajasthan - Jodhpur': {
        'residential':6.63,  # Tariff rate for residential consumers in Gujarat
        'industrial':  6.5,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 8.2,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },
    'Tamil Nadu - Chennai': {
        'residential':5.45,  # Tariff rate for residential consumers in Gujarat
        'industrial':  7.7,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 8.7,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Tamil Nadu - Coimbatore': {
        'residential':5.45,  # Tariff rate for residential consumers in Gujarat
        'industrial':  7.7,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 8.7,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Tamil Nadu - Madurai': {
        'residential':5.45,  # Tariff rate for residential consumers in Gujarat
        'industrial':  7.7,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 8.7,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Telangana - Hyderabad': {
        'residential':5.97,  # Tariff rate for residential consumers in Gujarat
        'industrial':  7.7,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 7,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Uttar Pradesh - Agra': {
        'residential':5.75,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.5,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.5,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Uttar Pradesh - Aligarh': {
        'residential':5.75,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.5,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.5,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Uttar Pradesh - Ghaziabad': {
        'residential':5.75,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.5,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.5,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

     'Uttar Pradesh - Kanpur': {
        'residential':5.75,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.5,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.5,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

     'Uttar Pradesh - Lucknow': {
        'residential':5.75,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.5,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.5,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Uttar Pradesh - Meerut': {
        'residential':5.75,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.5,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.5,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Uttar Pradesh - Moradabad': {
        'residential':5.75,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.5,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.5,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

     'Uttar Pradesh - Varanasi': {
        'residential':5.75,  # Tariff rate for residential consumers in Gujarat
        'industrial':  8.5,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 6.5,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'Uttarakhand - Dehradun': {
        'residential':4.68,  # Tariff rate for residential consumers in Gujarat
        'industrial':  7,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 5.7,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'West Bengal - Asansol': {
        'residential':6.21,  # Tariff rate for residential consumers in Gujarat
        'industrial':  4.37,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 4.31,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    },

    'West Bengal - Kolkata': {
        'residential':6.21,  # Tariff rate for residential consumers in Gujarat
        'industrial':  4.37,   # Tariff rate for industrial consumers in Gujarat
        'commercial': 4.31,   # Tariff rate for commercial consumers in Gujarat
        # Add more categories if needed
    }

}

# Define a function to parse state and city from the predefined dictionary
def get_state_city_options(tariff_rates):
    state_city_dict = {}
    for key in tariff_rates.keys():
        state, city = key.split(" - ")
        if state not in state_city_dict:
            state_city_dict[state] = []
        state_city_dict[state].append(city)
    return state_city_dict

# Function to get tariff rates
def get_tariff_rate(state, city, consumer_category):
    key = f"{state} - {city}"
    return tariff_rates.get(key, {}).get(consumer_category)

# Parse the state and city options from the tariff rates dictionary
state_city_dict = get_state_city_options(tariff_rates)

# Select state
selected_state = st.selectbox("Select your state", list(state_city_dict.keys()))

# Select city if the state has multiple cities
cities = state_city_dict[selected_state]
if len(cities) > 1:
    selected_city = st.selectbox("Select your city", cities)
else:
    selected_city = cities[0]

# Combine state and city
state = f"{selected_state} - {selected_city}"

# Select consumer category
consumer_category = st.selectbox("Select your consumer category", ['residential', 'industrial', 'commercial'])

# Select tariff option (predefined or custom)
tariff_option = st.radio("Select an option for electricity tariff", ("Predefined", "Custom"))

if tariff_option=="Predefined":
    # Check if the state and consumer category are valid
    if state in tariff_rates and consumer_category in tariff_rates[state]:
        # Retrieve the corresponding tariff rate based on user input
        normal_tariff = tariff_rates[state][consumer_category]
    else:
        st.error("Invalid state or consumer category.")
        exit()

else:
    normal_tariff = st.number_input("Enter electricity tariff rate: ", min_value=0.0, step=1.0)

outage_schedule = get_outage_schedule(n)
yearly_outage_status = generate_outage_status(outage_schedule, months, n)

# Repeat the yearly outage status for 25 years
extended_outage_status = yearly_outage_status * 25
#Read the input file

file_path = 'D:/Internship/CEEW/data/input1.xlsx'

if n == 1:
    solar_data_sheet = 'Hourly'
elif n == 2:
    solar_data_sheet = 'Half-Hourly'
elif n == 4:
    solar_data_sheet = 'Quarterly'
else:
    raise ValueError("Invalid value for n. Expected 1, 2, or 4.")


# Attempt to read the Excel file
try:
    df = pd.read_excel(file_path, sheet_name=solar_data_sheet)

except FileNotFoundError:
    st.write(f"File not found: {file_path}")
except ValueError as e:
    st.write(f"ValueError: {e}")
except Exception as e:
    st.write(f"An error occurred: {e}")

st.title("Select an option for solar generation:")
option = st.selectbox(
    "Choose an option:",
    ["Predefined solar generation", "Custom solar generation"]
)
if option == "Predefined solar generation":
    # Select the solar-generation coloumn based on the input state
    
    if state == 'Andhra Pradesh - Visakhapatnam':
        solar_generation = 'Andhra Pradesh - Visakhapatnam'
    elif state == 'Assam - Guwahati':
        solar_generation = 'Assam - Guwahati'
    elif state == 'Bihar - Patna':
        solar_generation = 'Bihar - Patna'
    elif state == 'Chandigarh - Chandigarh':
        solar_generation = 'Chandigarh - Chandigarh'
    elif state == 'Chhattisgarh - Bilaspur':
        solar_generation = 'Chhattisgarh - Bilaspur'
    elif state == 'Chhattisgarh - Raipur':
        solar_generation = 'Chhattisgarh - Raipur'
    elif state == 'Delhi - Delhi':
        solar_generation = 'Delhi - Delhi'
    elif state == 'Goa - Goa':
        solar_generation = 'Goa - Goa'
    elif state == 'Gujarat - Ahmedabad':
        solar_generation = 'Gujarat - Ahmedabad'
    elif state == 'Gujarat - Rajkot':
        solar_generation = 'Gujarat - Rajkot'
    elif state == 'Haryana - Faridabad':
        solar_generation = 'Haryana - Faridabad'
    elif state == 'Himachal Pradesh - Shimla':
        solar_generation = 'Himachal Pradesh - Shimla'
    elif state == 'Jammu and Kashmir - Srinagar':
        solar_generation = 'Jammu and Kashmir - Srinagar'
    elif state == 'Jharkhand - Ranchi':
        solar_generation = 'Jharkhand - Ranchi'
    elif state == 'Karnataka - Bengaluru':
        solar_generation = 'Karnataka - Bengaluru'
    elif state == 'Karnataka - Mangalore':
        solar_generation = 'Karnataka - Mangalore'
    elif state == 'Kerala - Kochi':
        solar_generation = 'Kerala - Kochi'
    elif state == 'Kerala - Thrissur':
        solar_generation = 'Kerala - Thrissur'
    elif state == 'Madhya Pradesh - Bhopal':
        solar_generation = 'Madhya Pradesh - Bhopal'
    elif state == 'Madhya Pradesh - Indore':
        solar_generation = 'Madhya Pradesh - Indore'
    elif state == 'Madhya Pradesh - Jabalpur':
        solar_generation = 'Madhya Pradesh - Jabalpur'
    elif state == 'Maharashtra - Aurangabad':
        solar_generation = 'Maharashtra - Aurangabad'
    elif state == 'Maharashtra - Mumbai':
        solar_generation = 'Maharashtra - Mumbai'
    elif state == 'Maharashtra - Navi Mumbai':
        solar_generation = 'Maharashtra - Navi Mumbai'
    elif state == 'Maharashtra - Pune':
        solar_generation = 'Maharashtra - Pune'
    elif state == 'Odisha - Bhubaneswar':
        solar_generation = 'Odisha - Bhubaneswar'
    elif state == 'Odisha - Cuttack':
        solar_generation = 'Odisha - Cuttack'
    elif state == 'Punjab - Amritsar':
        solar_generation = 'Punjab - Amritsar'
    elif state == 'Rajasthan - Bikaner':
        solar_generation = 'Rajasthan - Bikaner'
    elif state == 'Rajasthan - Jaipur':
        solar_generation = 'Rajasthan - Jaipur'
    elif state == 'Rajasthan - Jodhpur':
        solar_generation = 'Rajasthan - Jodhpur'
    elif state == 'Tamil Nadu - Chennai':
        solar_generation = 'Tamil Nadu - Chennai'
    elif state == 'Tamil Nadu - Coimbatore':
        solar_generation = 'Tamil Nadu - Coimbatore'
    elif state == 'Tamil Nadu - Madurai':
        solar_generation = 'Tamil Nadu - Madurai'
    elif state == 'Telangana - Hyderabad':
        solar_generation = 'Telangana - Hyderabad'
    elif state == 'Uttar Pradesh - Agra':
        solar_generation = 'Uttar Pradesh - Agra'
    elif state == 'Uttar Pradesh - Aligarh':
        solar_generation = 'Uttar Pradesh - Aligarh'
    elif state == 'Uttar Pradesh - Ghaziabad':
        solar_generation = 'Uttar Pradesh - Ghaziabad'
    elif state == 'Uttar Pradesh - Kanpur':
        solar_generation = 'Uttar Pradesh - Kanpur'
    elif state == 'Uttar Pradesh - Lucknow':
        solar_generation = 'Uttar Pradesh - Lucknow'
    elif state == 'Uttar Pradesh - Meerut':
        solar_generation = 'Uttar Pradesh - Meerut'
    elif state == 'Uttar Pradesh - Moradabad':
        solar_generation = 'Uttar Pradesh - Moradabad'
    elif state == 'Uttar Pradesh - Varanasi':
        solar_generation = 'Uttar Pradesh - Varanasi'
    elif state == 'Uttarakhand - Dehradun':
        solar_generation = 'Uttarakhand - Dehradun'
    elif state == 'West Bengal - Asansol':
        solar_generation = 'West Bengal - Asansol'
    elif state == 'West Bengal - Kolkata':
        solar_generation = 'West Bengal - Kolkata'
    
    # Add more conditions for other states if needed
else:  # Custom demand pattern
    st.write("Upload your custom solar generation CSV file:")
    solar_generation='customsolar'
    # Define the path to the sample CSV file
    sample_file_path = "D:/Internship/CEEW/data/samplesolar.csv"

    # Provide a downloadable sample CSV file from the specified path
    try:
        with open(sample_file_path, "rb") as file:
            st.download_button(
                label="Download Sample CSV",
                data=file,
                file_name="samplesolar.csv",
                mime='text/csv'
            )
    except FileNotFoundError:
        st.error(f"The sample file '{sample_file_path}' was not found. Please ensure it is placed in the correct directory.")

    # File uploader for custom demand pattern
    custom_file = st.file_uploader("Choose a CSV file", type="csv", key="loadpatterncsv")


    if custom_file:
        try:
        # Read the uploaded file into a DataFrame without header
            custom_df = pd.read_csv(custom_file, header=None)

            # Check if the uploaded DataFrame has correct rows
            if len(custom_df) == req_length:
            # Rename the column to 'customsolar'
                custom_df.columns = ['customsolar']

                # Replace the existing 'customsolar' column with the uploaded data
                df['customsolar'] = custom_df['customsolar']
            else:
                st.error("The uploaded CSV file does not have the required rows. Please upload a file with correct rows.")
        except pd.errors.EmptyDataError:
            st.error("The uploaded file is empty. Please upload a valid CSV file.")
        except pd.errors.ParserError:
            st.error("The uploaded file is not a valid CSV. Please check the file format and content.")
        except Exception as e:
            st.error(f"An error occurred while processing the file: {e}")





# Demand Pattern Calculation

# Define column names for the load profiles

load_profile_columns = ['Constant load - 7 days a week', 'Constant load - 6 days a week', 'Constant load - 5 days a week', 'Constant load - 6 AM to 10 PM',
 'Constant load - 6 AM to 10 PM - 6 days a week', 'Constant load - 6 AM to 10 PM - 5 days a week', 'Constant load - 9 AM to 5 PM', 'Constant load - 9 AM to 5 PM - 6 days a week', 'Constant load - 9 AM to 5 PM - 5 days a week',
 'Constant load - 6 AM to 6 PM']

st.title("Select an option:")
option = st.selectbox(
    "Choose an option:",
    ["Predefined load profiles", "Custom demand pattern"]
)

hourly_load_demand = []

def calculate_monthly_energy_consumption(monthly_consumption):
    return [monthly_consumption] * 12

if option == "Predefined load profiles":  
    # Function to calculate monthly energy consumption


    # Create a dictionary to map profile to index
    profile_dict = {profile: i for i, profile in enumerate(load_profile_columns, start=1)}
    # Display dropdown with profile names
    st.subheader('Select a Load Profile:')
    profile_name = st.selectbox('Choose a load profile:', load_profile_columns)

    # Get the selected profile index using the profile name
    profile_choice = profile_dict[profile_name]
    st.write(profile_choice)
    # User input for monthly energy consumption
    default_consumption = st.number_input('Enter Monthly Energy Consumption (in kWh):', min_value=0.0, step=1.0)
    use_optional_energy=False

    # Hidden expander for optional detailed input
    with st.expander('Optional: Enter Detailed Monthly Energy Consumption'):
        use_optional_energy = st.checkbox("Use Optional Inputs? (yes/no)", key='optionalenergy')
        detailed_consumption = []
        for month in calendar.month_name[1:]:  # Start from January
            detailed_consumption.append(st.number_input(f'Enter {month} energy consumption (in kWh):', min_value=0.0, step=1.0))

    # Use default or detailed inputs based on user choice
    if use_optional_energy:
        monthly_energy_consumption = detailed_consumption
    else:
        monthly_energy_consumption = calculate_monthly_energy_consumption(default_consumption)
    # Initialize an empty list to store hourly load demand for the entire year
    hourly_load_demand = []

    # Calculate hourly load demand for each month based on selected solar input and energy consumption
    for month_index, month in enumerate(months):
        days_in_month = calendar.monthrange(2023, month_index + 1)[1]
        hours_in_month = days_in_month * 24*n
        total_load_input = df[load_profile_columns[profile_choice]].values[:hours_in_month]
        total_load_input = total_load_input / total_load_input.sum()  # Normalize the solar input
        hourly_load_for_month = total_load_input * monthly_energy_consumption[month_index]*n
        hourly_load_demand.extend(hourly_load_for_month)    
    
else:  # Predefined load profiles
    custom_load_column = 'customload'
    st.write("Upload your custom demand pattern CSV file:")
    
    # Define the path to the sample CSV file
    sample_file_path = "D:/Internship/CEEW/data/sampleload.csv"

    # Provide a downloadable sample CSV file from the specified path
    try:
        with open(sample_file_path, "rb") as file:
            st.download_button(
                label="Download Sample CSV",
                data=file,
                file_name="sampleload.csv",
                mime='text/csv'
            )
    except FileNotFoundError:
        st.error(f"The sample file '{sample_file_path}' was not found. Please ensure it is placed in the correct directory.")

    # File uploader for custom demand pattern
    custom_file = st.file_uploader("Choose a CSV file", type="csv")

    if custom_file:
        try:
            # Read the uploaded file into a DataFrame without header
            custom_df = pd.read_csv(custom_file, header=None)

            # Check if the uploaded DataFrame has correct rows

            if len(custom_df) == req_length:
                # Rename the column to 'customload'
                custom_df.columns = ['customload']
                
                # Replace the existing 'customsolar' column with the uploaded data
                df['customload'] = custom_df['customload']

                # Extract the custom load column for further processing if needed
                hourly_load_demand = df[custom_load_column]

                st.write("Custom load pattern uploaded successfully.")
                st.write(df)
            else:
                st.error("The uploaded CSV file does not have the required rows. Please upload a file with correct rows.")
        except pd.errors.EmptyDataError:
            st.error("The uploaded file is empty. Please upload a valid CSV file.")
        except pd.errors.ParserError:
            st.error("The uploaded file is not a valid CSV. Please check the file format and content.")
        except Exception as e:
            st.error(f"An error occurred while processing the file: {e}")


# User inputs
#b=0 # control optimization and analyze option
# Selecting option 1 or 2
stringoption = st.selectbox("Select an option:", ["Do you want to analyze and compare your system cost with existing battery size", "Do you want to optimize the battery size"])

# Handling user input based on selected option
if stringoption == "Do you want to analyze and compare your system cost with existing battery size":
    bpc_wo = st.number_input("Enter the size of the battery in kW:", min_value=0.0)
    option=1
else:
    option=2
# User input for solar system size
solar_system_size = st.number_input("Enter the size of the solar system in kW:", min_value=0.0)

charge_from_grid=False
discharge_battery=False
# Expander for optional inputs
with st.expander('Optional Inputs'):
    charge_from_grid = st.checkbox("Allow charging the battery from the grid? (yes/no)", key='charge_from_grid')
    discharge_battery = st.checkbox("Discharge battery when solar generation < load demand and no outage during peak hours? (yes/no)", key='discharge_battery')


hos = 4  # hours of storage
eff = 0.95  # efficiency value, assuming an example value
min_charge = 0.2  # minimum charge level to prevent discharge below 20%
demand_charge = 300 #INR/kWh/Month 
increment_on_peak_tariff= 0.2 # 20%
decrement_on_non_peak_tariff=0.2 # 20%
feed_in_tariff = 0   #INR/kWh
vos = 50 # Value of lost load 

if 0 <= solar_system_size < 1:
    initial_solar_module_cost = 46293*1.12  # INR per kW the bench mark cost is with out GST, 12% GST added with that
    
if 1 <= solar_system_size < 2:
    initial_solar_module_cost = 43140*1.12

if 2 <= solar_system_size < 3:
    initial_solar_module_cost = 42020*1.12

if 3 <= solar_system_size < 10:
    initial_solar_module_cost = 40991*1.12

if 10 <= solar_system_size <= 100:
    initial_solar_module_cost = 38236*1.12

if  solar_system_size > 100:
    initial_solar_module_cost = 35886*1.12

initial_battery_cost = 25000  # INR per kWh
dg_cost = 30  # Diesel Generator cost INR/kWh

#Select metering regime
# User input for selecting the metering regime
st.markdown("## Select the metering regime:")
string_metering_option = st.selectbox("Net Metering", ["Net Metering", "Net Billing"])

if string_metering_option == "Net Metering":
    st.write("You selected Net Metering.")
    metering_option=1
else:
    st.write("You selected Net Billing.")
    metering_option=2

if metering_option == 1:
    metering_regime = 'net metering'
else:
    metering_regime = 'net billing'
# Yearly degradation and escalation rates
grid_carbon_factor=0.716
dg_carbon_factor=0.76
carbon_cost=0
solar_degradation_rate_yearly = 0.01  # 0.5% per year
battery_degradation_rate_yearly = 0.03  # 1% per year
demand_escalation_rate_yearly = 0.00  # 2% per year
om_cost_escalation_rate = 0.03  # 3% per year
tariff_escalation_rate_yearly = 0.01  # 2% per year
demand_charge_escalation_rate_yearly = 0.01  # 2% per year
dg_escalation_rate_yearly = 0.04  # 2% per year
vos_escalation_rate_yearly = 0.0  # 2% per year
discount_factor=0.08 #8% per year

#storage & Initialization of used arrays

num_years = 25  # Number of years
num_hours_in_year=n*8760 # Number of hours in a year
# Initialize the charge list
charge = [1] * (num_hours_in_year * num_years + 1)

# List to store calculated values for all years
calculated_values = []
max_values_per_year = []
yearly_om_costs_sg = []
yearly_total_demands=[]
yearly_total_demands_nd=[]
yearly_unmet_demand_costs_sg=[]
yearly_electricity_costs_sg=[]
yearly_electricity_costs_sg_nm=[]
yearly_electricity_costs_sdg=[]
yearly_electricity_costs_sdg_nm=[]
yearly_dg_costs_sdg=[]
yearly_sdg_grid_emis=[]
yearly_sdg_dg_emis=[]
yearly_sg_grid_emis=[]
overall_max_load = 0


# Battery replacement schedule and cost
battery_replacement_schedule = [10, 20]  # Battery is replaced at year 10 and year 20
battery_costs = {0: initial_battery_cost, 10: initial_battery_cost / 2, 20: initial_battery_cost / 4}  # Cost halves every 10 years

# #Calculation of power flow for solar+Grid+DG scenario
 # #Calculation of power flow for solar+Grid+DG scenario
max_values_per_year = []
max_gd_sdg1=0
for year in range(num_years):
    
# initialization of variables 
    
    yearly_demand=0
    yearly_dg_cost_sdg=0
    yearly_cost_sdg=0  
    yearly_cos_sdg_nm=0
    max_load=0
    yearly_sdg_grid_emi=0
    yearly_sdg_dg_emi=0
    # Adjust tariff rates for the current year
    
    peak_tariff = float(normal_tariff) + (float(normal_tariff) * float(increment_on_peak_tariff))
    non_peak_tariff = float(normal_tariff) - (float(normal_tariff) * float(decrement_on_non_peak_tariff))
    current_normal_tariff = float(normal_tariff) * ((1 + float(tariff_escalation_rate_yearly)) ** year)
    current_peak_tariff = peak_tariff * ((1 + float(tariff_escalation_rate_yearly)) ** year)
    current_non_peak_tariff = non_peak_tariff * ((1 + float(tariff_escalation_rate_yearly)) ** year)
    current_feed_in_tariff = float(feed_in_tariff) * ((1 + float(tariff_escalation_rate_yearly)) ** year)
    current_vos = float(vos) * ((1 + float(vos_escalation_rate_yearly)) ** year)
    current_dg_cost = float(dg_cost) * ((1 + float(dg_escalation_rate_yearly)) ** year)

    monthly_ngd_peak = [0]*13
    monthly_ngd_off_peak = [0]*13
    monthly_ngd_normal = [0]*13
  
    # Iterate over each hour in the year
    for index in range(num_hours_in_year):
        
        
        # Calculate the current hour in the overall simulation
        current_hour = year * num_hours_in_year + index    
        hour_of_day = index % (24*n)
       

        # Get the current hour's data from the original DataFrame for the first year or from calculated values for subsequent years
    
        if year == 0:
            s = df.at[index, solar_generation] * solar_system_size    #solar generation
            l = hourly_load_demand[index]
        else:
            prev_index = (year - 1) * num_hours_in_year + index
            s = calculated_values[prev_index]['solar_generation'] * (1 - solar_degradation_rate_yearly) 
            l = calculated_values[prev_index]['load_demand'] * (1 + demand_escalation_rate_yearly)
            

        # Set outage status based on extended outage status list
        o = extended_outage_status[current_hour]
        
        # Add your further calculations and logic here...
        demand=l/n        
        yearly_demand+=demand
        
        # Multiply 'load' and 'outage' for each hour and accumulate it
        l_o = l * o
        # Determine the tariff for the current hour
        if n==1:
            if 16 <= hour_of_day < 22:  # Peak hours from 5:00 PM to 11:00 PM
                hourly_tariff = current_peak_tariff
            elif 22 <= hour_of_day or hour_of_day < 4:  # Non-peak hours from 11:00 PM to 5:00 AM
                hourly_tariff = current_non_peak_tariff
            else:  # Normal hours for the remaining time
                hourly_tariff = current_normal_tariff

        if n==2:
            if 32 <= hour_of_day < 44:  # Peak hours from 5:00 PM to 11:00 PM
                hourly_tariff = current_peak_tariff
            elif 44 <= hour_of_day or hour_of_day < 8:  # Non-peak hours from 11:00 PM to 5:00 AM
                hourly_tariff = current_non_peak_tariff
            else:  # Normal hours for the remaining time
                hourly_tariff = current_normal_tariff
        if n==4:
            if 64 <= hour_of_day < 88:  # Peak hours from 5:00 PM to 11:00 PM
                hourly_tariff = current_peak_tariff
            elif 88 <= hour_of_day or hour_of_day < 16:  # Non-peak hours from 11:00 PM to 5:00 AM
                hourly_tariff = current_non_peak_tariff
            else:  # Normal hours for the remaining time
                hourly_tariff = current_normal_tariff
        


        # Initialize the variables

        sl_sdg=d_sdg=dg_unmet=gl_sdg=sg_sdg=gd_sdg=gf_sdg=ngd_sdg=sc_sdg=lc_sdg=0
          
        #Calculation of maximum load 

        max_load=max(max_load,l)
        
        sl_sdg=min(s,l)
        #sl_sdglist += sl_sdg
        #dg_unmet = 0
        if s>l and o==1:
            d_sdg=(s-l)
        if s>l and o==0:
            sg_sdg=(s-l)
        if s<l and o==1:
            dg_unmet= (l-s)                                #umnet load suppiled by DG
        if s<l and o==0:
            gl_sdg= (l-s)

        gd_sdg = gl_sdg  # Grid drawn
        gf_sdg = sg_sdg  # Grid feed-in
        ngd_sdg = gd_sdg - gf_sdg  # Net grid draw
        sc_sdg = sl_sdg + sg_sdg - s  # Solar check
        lc_sdg = sl_sdg + gl_sdg - l  # Load check

        sdg_grid_emi=ngd_sdg*(grid_carbon_factor)/n
        sdg_dg_emi=dg_unmet*(dg_carbon_factor)/n

        yearly_sdg_grid_emi+=sdg_grid_emi
        yearly_sdg_dg_emi+=sdg_dg_emi
        
        if metering_option == 1:
            # Example usage to populate monthly_ngd_peak based on some data
            month_key = calculate_month_key(index)
            if n==1:
                if 16 <= hour_of_day < 22:
                    monthly_ngd_peak[month_key] += ngd_sdg
                    
                elif 22 <= hour_of_day or hour_of_day < 4:
                    monthly_ngd_off_peak[month_key] += ngd_sdg              
                else:
                    monthly_ngd_normal[month_key] += ngd_sdg 
            if n==2:
                if 32 <= hour_of_day < 44:  # Peak hours from 5:00 PM to 11:00 PM
                    monthly_ngd_peak[month_key] += ngd_sdg
                elif 44 <= hour_of_day or hour_of_day < 8:  # Non-peak hours from 11:00 PM to 5:00 AM
                    monthly_ngd_off_peak[month_key] += ngd_sdg           
                else:  # Normal hours for the remaining time
                    monthly_ngd_normal[month_key] += ngd_sdg 
            if n==4:
                if 64 <= hour_of_day < 88:  # Peak hours from 5:00 PM to 11:00 PM
                     monthly_ngd_peak[month_key] += ngd_sdg
                elif 88 <= hour_of_day or hour_of_day < 16:  # Non-peak hours from 11:00 PM to 5:00 AM
                    monthly_ngd_off_peak[month_key] += ngd_sdg
                else:  # Normal hours for the remaining time
                    monthly_ngd_normal[month_key] += ngd_sdg
        

        if metering_option == 2:
            hourly_electricity_cost_sdg= ((gd_sdg * hourly_tariff) - (sg_sdg *current_feed_in_tariff))/n
            yearly_cost_sdg += hourly_electricity_cost_sdg
        
        # Update maximum values of gd for the current year when there is no outage   
        if o == 0:           
            max_gd_sdg1=max(max_gd_sdg1,gd_sdg)

       
        # Accumulate yearly generator cost solar+Grid+DG

        hourly_dg_cost_sdg = (dg_unmet * (current_dg_cost))/n
        yearly_dg_cost_sdg += hourly_dg_cost_sdg
        

        # Append the calculated values to the list
        calculated_values.append({
            'Year': year + 1,
            'Hour': index + 1,
            'solar_generation': s,
            'load_demand': l,
            'outage': o,
            'hourly_tariff': hourly_tariff,
            'sg_sdg':sg_sdg, 'dg_numet':dg_unmet,
        
        
        })
        
    overall_max_load = max(overall_max_load, max_load)


    #print(monthly_ngd_peak)
    unitspk = monthly_ngd_peak
    billing_unitspk, total_banked_unitspk = calculate_billing(unitspk)
    #print("Billing units in year pk:", sum(billing_unitspk))
    #print("Total Banked Units at the end of the period:", total_banked_unitspk)
    yearly_sdg_peak_cost=(sum(billing_unitspk)*(current_peak_tariff)/n-total_banked_unitspk*(current_feed_in_tariff)/n)

    unitsopk = monthly_ngd_off_peak
    billing_unitsopk, total_banked_unitsopk = calculate_billing(unitsopk)
    #print("Billing units in year: opk", sum(billing_unitsopk))
    #print("Total Banked Units at the end of the period:", total_banked_unitsopk)
    yearly_sdg_off_peak_cost=(sum(billing_unitsopk)*(current_non_peak_tariff)/n-total_banked_unitsopk*(current_feed_in_tariff)/n)

    unitsn = monthly_ngd_normal
    billing_unitsn, total_banked_unitsn = calculate_billing(unitsn)
    #print("Billing units in year: n", sum(billing_unitsn))
    #print("Total Banked Units at the end of the period:", total_banked_unitsn)
    yearly_sdg_nor_cost=(sum(billing_unitsn)*(current_normal_tariff)/n-total_banked_unitsn*(current_feed_in_tariff)/n)

    yearly_cost_sdg_nm=yearly_sdg_peak_cost+yearly_sdg_off_peak_cost+yearly_sdg_nor_cost
    #print(yearly_cost_sdg)
    
    # Append yearly maximum values and costs
    max_values_per_year.append({
        'Year': year + 1,
        'max_grid_load_sdg1':max_gd_sdg1,
        'max_demand_load':max_load
    })    
    
    yearly_electricity_costs_sdg.append(yearly_cost_sdg*(1/(1+discount_factor)**year)) 
    yearly_electricity_costs_sdg_nm.append(yearly_cost_sdg_nm*(1/(1+discount_factor)**year))   
    yearly_dg_costs_sdg.append(yearly_dg_cost_sdg*(1/(1+discount_factor)**year))
    yearly_total_demands.append(yearly_demand*(1/(1+discount_factor)**year))
    yearly_total_demands_nd.append(yearly_demand) 
    yearly_sdg_grid_emis.append (yearly_sdg_grid_emi)
    yearly_sdg_dg_emis.append (yearly_sdg_dg_emi)

#print(f'The maximum load value over 25 years is: {overall_max_load}')

#print(f'The maximum load value over 25 years is: {overall_max_load}')

#Cost Calculation of solar+Grid+DG


# Calculate the fixed component cost for solar+Grid+DG
fixed_cost_sdg_cost=sum( max_values_per_year[year]['max_grid_load_sdg1'] *12* demand_charge*((1+demand_escalation_rate_yearly)/(1+discount_factor)**year)
    for year in range(num_years))

# Calculate the variable component cost for solar+Grid+DG
if metering_option==1:
    total_electricity_cost_sdg=sum(yearly_electricity_costs_sdg_nm)
if metering_option==2:
    total_electricity_cost_sdg=sum(yearly_electricity_costs_sdg)

# Calculate the diesel cost for solar+Grid+DG
total_yearly_dg_costs_sdg = sum(yearly_dg_costs_sdg)

#solar module cost
solar_module_cost = solar_system_size * initial_solar_module_cost




total_demand=sum(yearly_total_demands)

#Calculate the carbon emission cost Grid+DG system

total_sdg_grid_emi=sum(yearly_sdg_grid_emis)
total_sdg_dg_emi=sum(yearly_sdg_dg_emis)
total_sdg_emi=(total_sdg_grid_emi+total_sdg_dg_emi)
total_sdg_emi_cost=(total_sdg_emi)*carbon_cost


#O&M cost
initial_om_cost_sg=0.01*solar_module_cost
yearly_om_costs_sg=[]
for year in range(num_years):
    if year == 0:
        yearly_om_cost_sg= initial_om_cost_sg
    else:
        yearly_om_cost_sg = initial_om_cost_sg * ((1 + om_cost_escalation_rate) ** year)

    yearly_om_costs_sg.append(yearly_om_cost_sg*(1/(1+discount_factor)**year))

# Accumulate the total O&M cost
total_om_cost_sg =sum(yearly_om_costs_sg)


# Calculate the total cost with solar+Grid+DG
total_cost_solar_grid_dg=fixed_cost_sdg_cost+total_electricity_cost_sdg+total_yearly_dg_costs_sdg+solar_module_cost+total_om_cost_sg+total_sdg_emi_cost


#Calculate the LCOE of solar+Grid+DG system
grid_sol_sdg_lcoe=(total_cost_solar_grid_dg)/(total_demand)

# Defining specific variable names for each cost component and LCOE
fixed_component_cost_solar_grid_dg = fixed_cost_sdg_cost
variable_component_cost_solar_grid_dg = total_electricity_cost_sdg
diesel_cost_solar_grid_dg = total_yearly_dg_costs_sdg
capx_cost_solar_grid_dg = solar_module_cost
om_cost_solar_grid_dg = total_om_cost_sg
total_cost_solar_grid_dg_system = total_cost_solar_grid_dg
lcoe_solar_grid_dg = grid_sol_sdg_lcoe


if st.button("Submit"):
    # Print statements with specific variable names

    #Calculation of power flow for solar+Grid scenario
    max_values_per_year = []
    max_gd_sg1=0
    for year in range(num_years):
        
    # initialization of variables 
        
        
        yearly_unmet_demand_cost_sg=0
        yearly_cost_sg=0
        yearly_cost_sg_nm=0
        max_load=0
        yearly_sg_grid_emi=0
        
        
        # Adjust tariff rates for the current year
        
        peak_tariff=normal_tariff+(normal_tariff*increment_on_peak_tariff)
        non_peak_tariff=normal_tariff-(normal_tariff*decrement_on_non_peak_tariff)
        current_normal_tariff = normal_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
        current_peak_tariff = peak_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
        current_non_peak_tariff = non_peak_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
        current_feed_in_tariff = feed_in_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
        current_vos = vos * ((1 + vos_escalation_rate_yearly) ** year)
        current_dg_cost = dg_cost * ((1 + dg_escalation_rate_yearly) ** year)

        monthly_ngd_peak = [0]*13
        monthly_ngd_off_peak = [0]*13
        monthly_ngd_normal = [0]*13
    
        
        # Iterate over each hour in the year
        for index in range(num_hours_in_year):
            # Calculate the current hour in the overall simulation
            current_hour = year * num_hours_in_year + index      
            hour_of_day = index % (24*n)

            # Get the current hour's data from the original DataFrame for the first year or from calculated values for subsequent years
        
            if year == 0:
                s = df.at[index, solar_generation] * solar_system_size    #solar generation
                l = hourly_load_demand[index]
            else:
                prev_index = (year - 1) * num_hours_in_year + index
                s = calculated_values[prev_index]['solar_generation'] * (1 - solar_degradation_rate_yearly) 
                l = calculated_values[prev_index]['load_demand'] * (1 + demand_escalation_rate_yearly)
                

            # Set outage status based on extended outage status list
            o = extended_outage_status[current_hour]
            
            # Add your further calculations and logic here...
            
            
            # Multiply 'load' and 'outage' for each hour and accumulate it
            l_o = l * o
            # Determine the tariff for the current hour
            if n==1:
                if 16 <= hour_of_day < 22:  # Peak hours from 5:00 PM to 11:00 PM
                    hourly_tariff = current_peak_tariff
                elif 22 <= hour_of_day or hour_of_day < 4:  # Non-peak hours from 11:00 PM to 5:00 AM
                    hourly_tariff = current_non_peak_tariff
                else:  # Normal hours for the remaining time
                    hourly_tariff = current_normal_tariff

            if n==2:
                if 32 <= hour_of_day < 44:  # Peak hours from 5:00 PM to 11:00 PM
                    hourly_tariff = current_peak_tariff
                elif 44 <= hour_of_day or hour_of_day < 8:  # Non-peak hours from 11:00 PM to 5:00 AM
                    hourly_tariff = current_non_peak_tariff
                else:  # Normal hours for the remaining time
                    hourly_tariff = current_normal_tariff
            if n==4:
                if 64 <= hour_of_day < 88:  # Peak hours from 5:00 PM to 11:00 PM
                    hourly_tariff = current_peak_tariff
                elif 88 <= hour_of_day or hour_of_day < 16:  # Non-peak hours from 11:00 PM to 5:00 AM
                    hourly_tariff = current_non_peak_tariff
                else:  # Normal hours for the remaining time
                    hourly_tariff = current_normal_tariff


            # Initialize the variables
            sl_sg=x_sg=sg_sg=gl_sg=gd_sg=gf_sg=ngd_sg=sc_sg=lc_sg=0
            
        
            
            #Calculation of maximum load 

            max_load=max(max_load,l)

            # Calculation for solar+Grid
            sl_sg=min(s,l)                       #sg=solar+Grid
            if  o==1:
                x_sg=l
            if s>l and o==0:
                sg_sg=(s-l)
                
            if s<l and o==0:
                gl_sg=(l-s)

            gd_sg = gl_sg  # Grid drawn
            gf_sg = sg_sg  # Grid feed-in
            ngd_sg = gd_sg - gf_sg  # Net grid draw
            sc_sg = sl_sg + sg_sg - s  # Solar check
            lc_sg = sl_sg + gl_sg - l  # Load check


            sg_emi=(ngd_sg*grid_carbon_factor)/n
            yearly_sg_grid_emi+=sg_emi

            
            if metering_option == 1:
                month_key = calculate_month_key(index)
                if n==1:
                    
                    if 16 <= hour_of_day < 22:
                        monthly_ngd_peak[month_key] += ngd_sg
                        
                    elif 22 <= hour_of_day or hour_of_day < 4:
                        monthly_ngd_off_peak[month_key] += ngd_sg              
                    else:
                        monthly_ngd_normal[month_key] += ngd_sg 
                if n==2:
                    
                    if 32 <= hour_of_day < 44:
                        monthly_ngd_peak[month_key] += ngd_sg
                        
                    elif 44 <= hour_of_day or hour_of_day < 8:
                        monthly_ngd_off_peak[month_key] += ngd_sg              
                    else:
                        monthly_ngd_normal[month_key] += ngd_sg 

                if n==4:     
                    if 64 <= hour_of_day < 88:
                        monthly_ngd_peak[month_key] += ngd_sg
                    elif 88 <= hour_of_day or hour_of_day < 16:
                        
                        monthly_ngd_off_peak[month_key] += ngd_sg              
                    else:
                        monthly_ngd_normal[month_key] += ngd_sg 
        
            
            if metering_option == 2:
                hourly_electricity_cost_sg = ((gd_sg * hourly_tariff) - (sg_sg * current_feed_in_tariff))/n
                yearly_cost_sg += hourly_electricity_cost_sg

            # Update maximum values of gd for the current year when there is no outage
            if o == 0:
                max_gd_sg1 = max(max_gd_sg1, gd_sg)

            # Accumulate the unmet demand cost for solar + Grid
            hourly_unmet_demand_cost_sg = (x_sg * current_vos)/n
            yearly_unmet_demand_cost_sg += hourly_unmet_demand_cost_sg


            # Append the calculated values to the list
            calculated_values.append({
                'Year': year + 1,
                'Hour': index + 1,
                'solar_generation': s,
                'load_demand': l,
                'outage': o,
                'hourly_tariff': hourly_tariff,
                'gd_sg': gd_sg,
                'gf_sg': gf_sg,
                'ngd_sg': ngd_sg,
                'sl_sg': sl_sg
            })

        overall_max_load = max(overall_max_load, max_load)

        
        #print(monthly_ngd_peak)
        unitspk = monthly_ngd_peak
        billing_unitspk, total_banked_unitspk = calculate_billing(unitspk)
        #print("Billing units in year pk:", sum(billing_unitspk))
        #print("Total Banked Units at the end of the period:", total_banked_unitspk)
        yearly_sg_peak_cost=((sum(billing_unitspk)*current_peak_tariff/n)-(total_banked_unitspk*(current_feed_in_tariff/n)))

        unitsopk = monthly_ngd_off_peak
        billing_unitsopk, total_banked_unitsopk = calculate_billing(unitsopk)
        #print("Billing units in year: opk", sum(billing_unitsopk))
        #print("Total Banked Units at the end of the period:", total_banked_unitsopk)
        yearly_sg_off_peak_cost=(sum(billing_unitsopk)*(current_non_peak_tariff/n)-(total_banked_unitsopk*(current_feed_in_tariff/n)))

        unitsn = monthly_ngd_normal
        billing_unitsn, total_banked_unitsn = calculate_billing(unitsn)
        #print("Billing units in year: n", sum(billing_unitsn))
        #print("Total Banked Units at the end of the period:", total_banked_unitsn)
        yearly_sg_nor_cost=(sum(billing_unitsn)*(current_normal_tariff/n)-(total_banked_unitsn*(current_feed_in_tariff/n)))

        yearly_cost_sg_nm=yearly_sg_peak_cost+yearly_sg_off_peak_cost+yearly_sg_nor_cost
        #print(yearly_cost_sg_nm)
        


        # Append yearly maximum values and costs
        max_values_per_year.append({
            'Year': year + 1,
            'max_grid_load_sg1': max_gd_sg1,
            'max_demand_load': max_load
        })
        
        yearly_electricity_costs_sg.append(yearly_cost_sg * (1 / (1 + discount_factor) ** year))
        yearly_electricity_costs_sg_nm.append(yearly_cost_sg_nm * (1 / (1 + discount_factor) ** year))   
        yearly_unmet_demand_costs_sg.append(yearly_unmet_demand_cost_sg * (1 / (1 + discount_factor) ** year))
        yearly_sg_grid_emis.append(yearly_sg_grid_emi)
    # print(f'The maximum load value over 25 years is: {overall_max_load}')

    #Cost Calculation of grid+solar


    #Fixed cost component for solar+Grid
    fixed_cost_dg_cost=sum( max_values_per_year[year]['max_grid_load_sg1'] *12* demand_charge*((1+demand_escalation_rate_yearly)/(1+discount_factor)**year)
        for year in range(num_years))


    # Calculate the total electricity cost over all years

    if metering_option==1:
        total_electricity_cost_sg = sum(yearly_electricity_costs_sg_nm)
    if metering_option==2:
        total_electricity_cost_sg = sum(yearly_electricity_costs_sg)



    # Calculate the cost of unmet demand solar+Grid
    total_unmet_demand_cost_sg = sum(yearly_unmet_demand_costs_sg)

    #Calculate carbon cost
    total_sg_emi=sum(yearly_sg_grid_emis)
    total_sg_emi_cost=total_sg_emi*carbon_cost

    #Total demand Calculation
    total_demand=sum(yearly_total_demands)

    #solar module cost
    solar_module_cost = solar_system_size * initial_solar_module_cost

    #O&M cost
    initial_om_cost_sg=0.01*solar_module_cost
    yearly_om_costs_sg=[]
    for year in range(num_years):
        if year == 0:
            yearly_om_cost_sg= initial_om_cost_sg
        else:
            yearly_om_cost_sg = initial_om_cost_sg * ((1 + om_cost_escalation_rate) ** year)

        yearly_om_costs_sg.append(yearly_om_cost_sg*(1/(1+discount_factor)**year))

    # Accumulate the total O&M cost
    total_om_cost_sg =sum(yearly_om_costs_sg)

    # Calculate the total cost with solar+Grid
    total_cost_solar_grid= fixed_cost_dg_cost + total_electricity_cost_sg+ total_unmet_demand_cost_sg+ solar_module_cost + total_om_cost_sg+total_sg_emi_cost


    #Calculate the LCOE of solar+Grid system
    grid_sg_lcoe=(total_cost_solar_grid)/(total_demand)


    total_fixed_component_cost_solar_grid = fixed_cost_dg_cost
    total_variable_component_cost_solar_grid = total_electricity_cost_sg
    total_unmet_demand_cost_solar_grid = total_unmet_demand_cost_sg
    total_capx_cost_solar_grid = solar_module_cost
    total_om_cost_solar_grid = total_om_cost_sg
    total_cost_solar_grid_system = total_cost_solar_grid
    lcoe_solar_grid = grid_sg_lcoe


    total_fixed_component_cost_solar_grid_bess = 0
    total_variable_component_cost_solar_grid_bess = 0
    total_unmet_demand_cost_solar_grid_bess = 0
    total_capx_cost_solar_grid_bess = 0
    total_om_cost_solar_grid_bess = 0
    total_cost_solar_grid_bess_system = 0
    lcoe_solar_grid_bess = 0

    if option==1:
    #Cost Calculation of BESS+Solar+Grid System 


        initial_bpc=bpc_wo
        yearly_total_demands=[]
        yearly_electricity_costs = []
        yearly_electricity_costs_nm = []
        max_values_per_year = []
        yearly_unmet_demand_costs = []
        yearly_om_costs = []
        yearly_total_sl=[]
        yearly_total_bl=[]
        yearly_total_gl=[]
        yearly_total_sb=[]
        yearly_total_sg=[]
        yearly_total_gb=[]
        yearly_total_d=[]
        yearly_total_x=[]
        yearly_total_ngd=[]
        yearly_emis=[]
        max_gd1=0
        
        for year in range(num_years):
            # Calculate the current cycle for battery replacement
            cycle = year // 10
            # Calculate current year's battery power capacity considering the replacement every 10 years
            bpc = initial_bpc * ((1 - battery_degradation_rate_yearly) ** (year % 10))
        
            # initialization of variables
            yearly_cost = 0
            yearly_unmet_demand_cost = 0
            yearly_dg_cost = 0
            yearly_demand=0
            yearly_emi=0
            yearly_sl=0
            yearly_bl=0
            yearly_gl=0
            yearly_sb=0
            yearly_sg=0
            yearly_gb=0
            yearly_d=0
            yearly_x=0
            yearly_ngd=0
            # Adjust tariff rates for the current year
            peak_tariff=normal_tariff+(normal_tariff*increment_on_peak_tariff)
            non_peak_tariff=normal_tariff-(normal_tariff*decrement_on_non_peak_tariff)
            current_normal_tariff = normal_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
            current_peak_tariff = peak_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
            current_non_peak_tariff = non_peak_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
            current_feed_in_tariff = feed_in_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
            current_vos = vos * ((1 + vos_escalation_rate_yearly) ** year)
            current_dg_cost = dg_cost * ((1 + dg_escalation_rate_yearly) ** year)
        
            monthly_ngd_peak = [0]*13
            monthly_ngd_off_peak = [0]*13
            monthly_ngd_normal = [0]*13
            
            # Iterate over each hour in the year
            for index in range(num_hours_in_year):
                # Calculate the current hour in the overall simulation
                current_hour = year * num_hours_in_year + index
                hour_of_day = index % (24*n)
        
                # Get the current hour's data from the original DataFrame for the first year or from calculated values for subsequent years
            
                if year == 0:
                    s = df.at[index, solar_generation] * solar_system_size    #solar generation
                    l = hourly_load_demand[index]
                else:
                    prev_index = (year - 1) * num_hours_in_year + index
                    s = calculated_values[prev_index]['solar_generation'] * (1 - solar_degradation_rate_yearly) 
                    l = calculated_values[prev_index]['load_demand'] * (1 + demand_escalation_rate_yearly)
        
        
                # Set outage status based on extended outage status list
                o = extended_outage_status[current_hour]
                
                # Add your further calculations and logic here...
                
                # Multiply 'load' and 'outage' for each hour and accumulate it
                l_o = l * o
                # Determine the tariff for the current hour
                if n==1:
                    if 16 <= hour_of_day < 22:  # Peak hours from 5:00 PM to 11:00 PM
                        hourly_tariff = current_peak_tariff
                    elif 22 <= hour_of_day or hour_of_day < 4:  # Non-peak hours from 11:00 PM to 5:00 AM
                        hourly_tariff = current_non_peak_tariff
                    else:  # Normal hours for the remaining time
                        hourly_tariff = current_normal_tariff
        
                if n==2:
                    if 32 <= hour_of_day < 44:  # Peak hours from 5:00 PM to 11:00 PM
                        hourly_tariff = current_peak_tariff
                    elif 44 <= hour_of_day or hour_of_day < 8:  # Non-peak hours from 11:00 PM to 5:00 AM
                        hourly_tariff = current_non_peak_tariff
                    else:  # Normal hours for the remaining time
                        hourly_tariff = current_normal_tariff
                if n==4:
                    if 64 <= hour_of_day < 88:  # Peak hours from 5:00 PM to 11:00 PM
                        hourly_tariff = current_peak_tariff
                    elif 88 <= hour_of_day or hour_of_day < 16:  # Non-peak hours from 11:00 PM to 5:00 AM
                        hourly_tariff = current_non_peak_tariff
                    else:  # Normal hours for the remaining time
                        hourly_tariff = current_normal_tariff
        
        
                # Initialize the variables
                sl= c = sb = d = sg = bg = gb = r = bl = x = gl =gd = gf = ngd = sc = lc = 0
        
                # Solar to load
                sl = min(s, l)
        
                if s > l:
                    c = s - l
                    sb = min(c, bpc, (1 - charge[current_hour]) * (bpc * hos*n))  # solar to battery
        
                    if (s - sl - sb) > 0 and o == 1:
                        d = c - sb  # power curtailment
                    else:
                        if (s - sl - sb) > 0 and o == 0:
                            sg = c - sb  # solar to grid
                        elif (s - sl - sb) < 0 and o == 0 and charge_from_grid:
                            gb = min(bpc, ((1 - charge[current_hour]) * (bpc * hos*n)))  # grid to battery
        
                if s < l and o == 1:
                    r = l - s  # residual load
                    available_charge = max(charge[current_hour] - min_charge, 0) * (bpc * hos * eff)  # prevent discharge below 20%
                    bl = min(available_charge*n, bpc, r)  # battery to the load
                    x = max(r - bl, 0)  # unmet demand
                else:
                    if s < l and o == 0 and hour_of_day in range(16*n, 22*n) and discharge_battery and charge[current_hour] > 0.5:
                        available_charge = max(charge[current_hour] - 0.5, 0) * (bpc * hos * eff)  # prevent discharge below 50%
                        bl = min(available_charge*n, bpc, l - s)  # Battery to the load
                        gl = l - s - bl  # Grid to load
                    else:
                        if s < l and o == 0:
                            gl = l - s  # Grid to load
        
                gd = gb + gl  # Grid draw
                gf = sg + bg  # Grid feed-in
                ngd = gd - gf  # Net grid draw
                sc = sl + sb + sg - s  # Solar check
                lc = sl + bl + gl - l  # Load check
        
                #Calculation of Grid Emission
        
                emi=ngd*(grid_carbon_factor/n)
                yearly_emi+=emi

                yearly_sl+=sl
                yearly_bl+=bl
                yearly_gl+=gl
                yearly_sb+=sb
                yearly_sg+=sg
                yearly_gb+=gb
                yearly_d+=d
                yearly_ngd+=ngd
                yearly_x+=x
                
                if metering_option == 1:
                    # Example usage to populate monthly_ngd_peak based on some data
                    month_key = calculate_month_key(index)
                    if n==1:               
                        if 16 <= hour_of_day < 22:
                            monthly_ngd_peak[month_key] += ngd     
                        elif 22 <= hour_of_day or hour_of_day < 4:
                            monthly_ngd_off_peak[month_key] += ngd              
                        else:
                            monthly_ngd_normal[month_key] += ngd
                    if n==2:               
                        if 32 <= hour_of_day < 44:
                            monthly_ngd_peak[month_key] += ngd     
                        elif 44 <= hour_of_day or hour_of_day < 8:
                            monthly_ngd_off_peak[month_key] += ngd              
                        else:
                            monthly_ngd_normal[month_key] += ngd
        
                    if n==4:               
                        if 64 <= hour_of_day < 88:
                            monthly_ngd_peak[month_key] += ngd     
                        elif 88 <= hour_of_day or hour_of_day < 16:
                            monthly_ngd_off_peak[month_key] += ngd              
                        else:
                            monthly_ngd_normal[month_key] += ngd
                
        
                if metering_option == 2:
                    hourly_electricity_cost = ((gd * hourly_tariff) - (sg * current_feed_in_tariff))/n
                    yearly_cost += hourly_electricity_cost
                    
                # Update maximum values of gd for the current year when there is no outage   
                if o == 0:
                    max_gd1 = max(max_gd1, gd)
            
                
                demand=l/n
                yearly_demand+=demand
            
                # Accumulate the unmet demand cost
                hourly_unmet_demand_cost = (x * current_vos)/n
                yearly_unmet_demand_cost += hourly_unmet_demand_cost 
                    
        
                # Ensure charge does not drop below minimum level
                charge[current_hour + 1] = charge[current_hour] + (((sb + gb) * eff - bl / eff) / (bpc * hos*n))
        
                # Append the calculated values to the list
                calculated_values.append({
                    'Year': year + 1,
                    'Hour': index + 1,
                    'solar_generation': s,
                    'load_demand': l,
                    'outage': o,
                    'sl': sl, 'c': c, 'sb': sb, 'd': d, 'sg': sg, 'bg': bg, 'gb': gb,
                    'r': r, 'bl': bl, 'x': x, 'gl': gl, 'gd': gd, 'gf': gf, 'ngd': ngd, 'sc': sc, 'lc': lc,
                    'hourly_tariff': hourly_tariff,
                    'charge': charge[current_hour]
                
                
                })
        
            # Append yearly maximum values and costs
            max_values_per_year.append({
                'Year': year + 1,
                'max_grid_load1': max_gd1
            })
        
            
                #print(monthly_ngd_peak)
            unitspk = monthly_ngd_peak
            billing_unitspk, total_banked_unitspk = calculate_billing(unitspk)
                #print("Billing units in year pk:", sum(billing_unitspk))
                #print("Total Banked Units at the end of the period:", total_banked_unitspk)
            yearly_peak_cost=((sum(billing_unitspk)*current_peak_tariff/n)-(total_banked_unitspk*(current_feed_in_tariff/n)))
            
            unitsopk = monthly_ngd_off_peak
            billing_unitsopk, total_banked_unitsopk = calculate_billing(unitsopk)
                #print("Billing units in year: opk", sum(billing_unitsopk))
                #print("Total Banked Units at the end of the period:", total_banked_unitsopk)
            yearly_off_peak_cost=(sum(billing_unitsopk)*(current_non_peak_tariff/n)-(total_banked_unitsopk*(current_feed_in_tariff/n)))
            
            unitsn = monthly_ngd_normal
            billing_unitsn, total_banked_unitsn = calculate_billing(unitsn)
                #print("Billing units in year: n", sum(billing_unitsn))
                #print("Total Banked Units at the end of the period:", total_banked_unitsn)
            yearly_nor_cost=(sum(billing_unitsn)*(current_normal_tariff/n)-(total_banked_unitsn*(current_feed_in_tariff/n)))
            
            yearly_cost_nm=yearly_peak_cost+yearly_off_peak_cost+yearly_nor_cost
                #print(yearly_cost)
        
            yearly_electricity_costs.append(yearly_cost*(1/(1+discount_factor)**year))
            yearly_electricity_costs_nm.append(yearly_cost_nm*(1/(1+discount_factor)**year))
            yearly_unmet_demand_costs.append(yearly_unmet_demand_cost*(1/(1+discount_factor)**year))
            yearly_total_demands.append(yearly_demand*(1/(1+discount_factor)**year))
            yearly_total_sl.append (yearly_sl)
            yearly_total_bl.append (yearly_bl)
            yearly_total_gl.append (yearly_gl)
            yearly_total_sb.append (yearly_sb)
            yearly_total_sg.append (yearly_sg)
            yearly_total_gb.append (yearly_gb)
            yearly_total_d.append (yearly_d)
            yearly_total_x.append (yearly_x)
            yearly_total_ngd.append (yearly_ngd)
            yearly_emis.append (yearly_emi)
                
                # Calculate the total fixed component cost over all years
        total_fixed_component_cost = sum(max_values_per_year[year]['max_grid_load1'] *12* demand_charge*((1+demand_escalation_rate_yearly)/(1+discount_factor)**year)
                    for year in range(num_years))
                
                # Calculate the total electricity cost over all years
        if metering_option==1:
            total_electricity_cost = sum(yearly_electricity_costs_nm)
        if metering_option==2:
            total_electricity_cost = sum(yearly_electricity_costs)
                #total demand
        total_demand=sum(yearly_total_demands)
            
                # Calculate the cost of unmet demand
        total_unmet_demand_cost = sum(yearly_unmet_demand_costs)
        
            #Total Carbon emission
        
        total_emi=sum(yearly_emis)
        total_carbon_savings_cost=total_emi*carbon_cost
        
        total_demand=sum(yearly_total_demands)
        
            
                
                # Calculate the solar module cost 
        solar_module_cost = solar_system_size * initial_solar_module_cost
        total_battery_cost = initial_bpc* hos * battery_costs[0] # Initial battery cost
        
                
                # Add the replacement costs
        total_battery_cost += sum([initial_bpc * hos * battery_costs[year] for year in battery_replacement_schedule])
                
                # Total Capex cost
        Capx_cost = solar_module_cost + total_battery_cost
        
        initial_om_cost = 0.01 * (solar_module_cost+ initial_bpc*hos*initial_battery_cost)
            
            
            # O&M cost
        yearly_om_costs=[]
        for year in range(num_years):
            if year == 0:
                yearly_om_cost = initial_om_cost
            else:
                yearly_om_cost = initial_om_cost * ((1 + om_cost_escalation_rate) ** year)
                
            yearly_om_costs.append(yearly_om_cost*(1/(1+discount_factor)**year))
                
                    # Accumulate the total O&M cost
        total_om_cost = sum(yearly_om_costs)
        
            #Total cost for BESS system
            
        total_c = total_fixed_component_cost + total_unmet_demand_cost + Capx_cost + total_om_cost + total_electricity_cost+total_carbon_savings_cost
        

        total_sl=sum(yearly_total_sl)
        total_bl=sum(yearly_total_bl)
        total_gl=sum(yearly_total_gl)
        total_sb=sum(yearly_total_sb)
        total_sg=sum(yearly_total_sg)
        total_d=sum(yearly_total_d)
        total_x=sum(yearly_total_x)
        total_gb=sum(yearly_total_gb)
        total_ngd=sum(yearly_total_ngd)

        
        st.metric(label="Total cost for solar+Grid+BESS system", value=format_indian_currency(total_c))
        st.metric(label="LCOE for solar+Grid+BESS system", value=f"{total_c/total_demand:.2f} INR/kWh")


        
    else:
        # Next block of code when b != 0
        pass

    #Optimization of the battery size
    if option==2:
        
        min_bpc = 1
        max_bpc = max(overall_max_load,solar_system_size)
        iterations = 100
        # Calculate the step size
        step = (max_bpc - min_bpc) / (iterations - 1)
        min_total_cost = float('inf')  # Initialize min_total_cost to infinity
        optimal_bpc = None
        
        # Loop through possible battery sizes
        for i in range(iterations):
            bpc = min_bpc + i * step
            overall_max_load = 0
            yearly_total_demands=[]
            yearly_electricity_costs = []
            yearly_electricity_costs_nm = []
            max_values_per_year = []
            yearly_unmet_demand_costs = []
            yearly_om_costs = []
            yearly_emis=[]
            yearly_total_sl=[]
            yearly_total_bl=[]
            yearly_total_gl=[]
            yearly_total_sb=[]
            yearly_total_gb=[]
            yearly_total_sg=[]
            yearly_total_d=[]
            yearly_total_x=[]
            yearly_total_ngd=[]
            max_gd1=0
            
            for year in range(num_years):
                # Calculate the current cycle for battery replacement
                yearly_cost = 0
                yearly_cost_nm = 0  
                yearly_unmet_demand_cost = 0
                yearly_demand=0
                yearly_emi=0
                yearly_sl=0
                yearly_bl=0
                yearly_gl=0
                yearly_sb=0
                yearly_gb=0
                yearly_sg=0
                yearly_d=0
                yearly_x=0
                yearly_ngd=0
                
                cycle = year // 10
                # Calculate current year's battery power capacity considering the replacement every 10 years
                current_bpc = bpc * ((1 - battery_degradation_rate_yearly) ** (year % 10))
                
                # Adjust tariff rates for the current year
                peak_tariff = normal_tariff + (normal_tariff * increment_on_peak_tariff)
                non_peak_tariff = normal_tariff - (normal_tariff * decrement_on_non_peak_tariff)
                current_normal_tariff = normal_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
                current_peak_tariff = peak_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
                current_non_peak_tariff = non_peak_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
                current_feed_in_tariff = feed_in_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
                current_vos = vos * ((1 + vos_escalation_rate_yearly) ** year)
                current_dg_cost = dg_cost * ((1 + dg_escalation_rate_yearly) ** year)
        
                monthly_ngd_normal = [0]*13
                monthly_ngd_off_peak = [0]*13
                monthly_ngd_peak = [0]*13
                
                # Iterate over each hour in the year
                for index in range(num_hours_in_year):
                    # Calculate the current hour in the overall simulation
                    current_hour = year * num_hours_in_year + index
                    hour_of_day = index % (24*n)
            
                    # Get the current hour's data from the original DataFrame for the first year or from calculated values for subsequent years
                
                    if year == 0:
                        s = df.at[index, solar_generation] * solar_system_size    #solar generation
                        l = hourly_load_demand[index]
                    else:
                        prev_index = (year - 1) * num_hours_in_year + index
                        s = calculated_values[prev_index]['solar_generation'] * (1 - solar_degradation_rate_yearly) 
                        l = calculated_values[prev_index]['load_demand'] * (1 + demand_escalation_rate_yearly)
                    
            
                    # Set outage status based on extended outage status list
                    o = extended_outage_status[current_hour]
                    
                    
                    
                    # Determine the tariff for the current hour
                    if n==1:
                        if 16 <= hour_of_day < 22:  # Peak hours from 5:00 PM to 11:00 PM
                            hourly_tariff = current_peak_tariff
                        elif 22 <= hour_of_day or hour_of_day < 4:  # Non-peak hours from 11:00 PM to 5:00 AM
                            hourly_tariff = current_non_peak_tariff
                        else:  # Normal hours for the remaining time
                            hourly_tariff = current_normal_tariff
        
                    if n==2:
                        if 32 <= hour_of_day < 44:  # Peak hours from 5:00 PM to 11:00 PM
                            hourly_tariff = current_peak_tariff
                        elif 44 <= hour_of_day or hour_of_day < 8:  # Non-peak hours from 11:00 PM to 5:00 AM
                            hourly_tariff = current_non_peak_tariff
                        else:  # Normal hours for the remaining time
                            hourly_tariff = current_normal_tariff
                    if n==4:
                        if 64 <= hour_of_day < 88:  # Peak hours from 5:00 PM to 11:00 PM
                            hourly_tariff = current_peak_tariff
                        elif 88 <= hour_of_day or hour_of_day < 16:  # Non-peak hours from 11:00 PM to 5:00 AM
                            hourly_tariff = current_non_peak_tariff
                        else:  # Normal hours for the remaining time
                            hourly_tariff = current_normal_tariff
                
                
                    # Initialize the variables
                    sl= c = sb = d = sg = gb=bg = r = bl = x = gl =gd = gf = ngd = sc = lc = 0
                    
            
                    # Solar to load
                    sl = min(s, l)
            
                    if s > l:
                        c = s - l
                        sb = min(c, current_bpc, (1 - charge[current_hour]) * (current_bpc * hos*n))  # solar to battery
            
                        if (s - sl - sb) > 0 and o == 1:
                            d = c - sb  # power curtailment
                        else:
                            if (s - sl - sb) > 0 and o == 0:
                                sg = c - sb  # solar to grid
                            elif (s - sl - sb) < 0 and o == 0 and charge_from_grid:
                                gb = min(current_bpc, (1 - charge[current_hour]) * (current_bpc * hos*n))  # grid to battery
            
                    if s < l and o == 1:
                        r = l - s  # residual load
                        available_charge = max(charge[current_hour] - min_charge, 0) * (current_bpc * hos * eff)  # prevent discharge below 20%
                        bl = min(available_charge*n, current_bpc, r)  # battery to the load
                        x = max(r - bl, 0)  # unmet demand
                
                    else:
                        if s < l and o == 0 and hour_of_day in range(16*n, 22*n) and discharge_battery and charge[current_hour] > 0.5:
                            available_charge = max(charge[current_hour] - 0.5, 0) * (current_bpc * hos * eff)  # prevent discharge below 50%
                            bl = min(available_charge*n, current_bpc, l - s)  # Battery to the load
                            gl = l - s - bl  # Grid to load
                        else:
                            if s < l and o == 0:
                                gl = l - s  # Grid to load
            
                    gd = gb + gl  # Grid draw
                    gf = sg + bg  # Grid feed-in
                    ngd = gd - gf  # Net grid draw
                    sc = sl + sb + sg - s  # Solar check
                    lc = sl + bl + gl - l  # Load check
        
                    #Calculation of Grid Emission
        
                    emi=ngd*(grid_carbon_factor/n)
                    yearly_emi+=emi

                    yearly_sl+=sl
                    yearly_bl+=bl
                    yearly_gl+=gl
                    yearly_sb+=sb
                    yearly_sg+=sg
                    yearly_gb+=gb
                    yearly_d+=d
                    yearly_ngd+=ngd
                    yearly_x+=x
                    
        
                    if metering_option == 1:
                        month_key = calculate_month_key(index) 
                        if n==1:           
                            if 16 <= hour_of_day < 22:
                                monthly_ngd_peak[month_key] += ngd       
                            elif 22 <= hour_of_day or hour_of_day < 4:
                                monthly_ngd_off_peak[month_key] += ngd              
                            else:
                                monthly_ngd_normal[month_key] += ngd
                        if n==2:           
                            if 32 <= hour_of_day < 44:
                                monthly_ngd_peak[month_key] += ngd       
                            elif 44 <= hour_of_day or hour_of_day < 8:
                                monthly_ngd_off_peak[month_key] += ngd              
                            else:
                                monthly_ngd_normal[month_key] += ngd
        
                        if n==4:           
                            if 64 <= hour_of_day < 88:
                                monthly_ngd_peak[month_key] += ngd       
                            elif 88 <= hour_of_day or hour_of_day < 16:
                                monthly_ngd_off_peak[month_key] += ngd              
                            else:
                                monthly_ngd_normal[month_key] += ngd
                
        
                    if metering_option == 2:
                        
                        hourly_electricity_cost = ((gd * hourly_tariff) - (sg * current_feed_in_tariff))/n
                        yearly_cost += hourly_electricity_cost
                        
                    
                    # Update maximum values of gd for the current year
                    if o==0:
                        max_gd1 = max(max_gd1, gd)
            
                
                    demand=l/n
                    yearly_demand+=demand
        
            
                    # Accumulate the unmet demand cost
                    hourly_unmet_demand_cost = (x * current_vos)/n
                    yearly_unmet_demand_cost += hourly_unmet_demand_cost
            
                    
                    # Ensure charge does not drop below minimum level
                    charge[current_hour + 1] = charge[current_hour] + (((sb + gb) * eff - bl / eff) / (current_bpc * hos*n))
            
                    
            
                # Append yearly maximum values and costs
                max_values_per_year.append({
                    'Year': year + 1,        
                    'max_grid_load1': max_gd1
                })
        
        
        
                #print(monthly_ngd_peak)
                unitspk = monthly_ngd_peak
                billing_unitspk, total_banked_unitspk = calculate_billing(unitspk)
                #print("Billing units in year pk:", sum(billing_unitspk))
                #print("Total Banked Units at the end of the period:", total_banked_unitspk)
                yearly_peak_cost=((sum(billing_unitspk)*current_peak_tariff/n)-(total_banked_unitspk*(current_feed_in_tariff/n)))
            
                unitsopk = monthly_ngd_off_peak
                billing_unitsopk, total_banked_unitsopk = calculate_billing(unitsopk)
                #print("Billing units in year: opk", sum(billing_unitsopk))
                #print("Total Banked Units at the end of the period:", total_banked_unitsopk)
                yearly_off_peak_cost=(sum(billing_unitsopk)*(current_non_peak_tariff/n)-(total_banked_unitsopk*(current_feed_in_tariff/n)))
            
                unitsn = monthly_ngd_normal
                billing_unitsn, total_banked_unitsn = calculate_billing(unitsn)
                #print("Billing units in year: n", sum(billing_unitsn))
                #print("Total Banked Units at the end of the period:", total_banked_unitsn)
                yearly_nor_cost=(sum(billing_unitsn)*(current_normal_tariff/n)-(total_banked_unitsn*(current_feed_in_tariff/n)))
            
                yearly_cost_nm=yearly_peak_cost+yearly_off_peak_cost+yearly_nor_cost
                #print(yearly_cost)
        
                yearly_electricity_costs.append(yearly_cost*(1/(1+discount_factor)**year))
                yearly_electricity_costs_nm.append(yearly_cost_nm*(1/(1+discount_factor)**year))
                yearly_unmet_demand_costs.append(yearly_unmet_demand_cost*(1/(1+discount_factor)**year))
                yearly_total_demands.append(yearly_demand*(1/(1+discount_factor)**year))
                yearly_emis.append (yearly_emi)
                yearly_total_sl.append (yearly_sl)
                yearly_total_bl.append (yearly_bl)
                yearly_total_gl.append (yearly_gl)
                yearly_total_sb.append (yearly_sb)
                yearly_total_sg.append (yearly_sg)
                yearly_total_gb.append (yearly_gb)
                yearly_total_d.append (yearly_d)
                yearly_total_x.append (yearly_x)
                yearly_total_ngd.append (yearly_ngd)
                
                # Calculate the total fixed component cost over all years
            total_fixed_component_cost = sum(max_values_per_year[year]['max_grid_load1'] *12* demand_charge*((1+demand_escalation_rate_yearly)/(1+discount_factor)**year)
                    for year in range(num_years))
                
                # Calculate the total electricity cost over all years
            if metering_option==1:
                total_electricity_cost = sum(yearly_electricity_costs_nm)
            if metering_option==2:
                total_electricity_cost = sum(yearly_electricity_costs)
                #total demand
            total_demand=sum(yearly_total_demands)
            
                # Calculate the cost of unmet demand
            total_unmet_demand_cost = sum(yearly_unmet_demand_costs)
        
            #Total Carbon emission
        
            total_emi=sum(yearly_emis)
            total_carbon_savings_cost=total_emi*carbon_cost
        
            total_demand=sum(yearly_total_demands)
            
            
                
                # Calculate the solar module cost 
            solar_module_cost = solar_system_size * initial_solar_module_cost
            total_battery_cost = bpc * hos * battery_costs[0] # Initial battery cost
                
                # Add the replacement costs
            total_battery_cost += sum([bpc * hos * battery_costs[year] for year in battery_replacement_schedule])
                
                # Total Capex cost
            Capx_cost = solar_module_cost + total_battery_cost
            initial_om_cost = 0.01 * (solar_module_cost+ bpc*hos*initial_battery_cost)
            
            
            # O&M cost
            yearly_om_costs=[]
            for year in range(num_years):
                if year == 0:
                    yearly_om_cost = initial_om_cost
                else:
                    yearly_om_cost = initial_om_cost * ((1 + om_cost_escalation_rate) ** year)
                
                yearly_om_costs.append(yearly_om_cost*(1/(1+discount_factor)**year))
                
                    # Accumulate the total O&M cost
            total_om_cost = sum(yearly_om_costs)
        
            #Total cost for BESS system
            
            total_c = total_fixed_component_cost + total_unmet_demand_cost + Capx_cost + total_om_cost + total_electricity_cost+total_carbon_savings_cost
            
            total_sl=sum(yearly_total_sl)
            total_bl=sum(yearly_total_bl)
            total_gl=sum(yearly_total_gl)
            total_sb=sum(yearly_total_sb)
            total_sg=sum(yearly_total_sg)
            total_gb=sum(yearly_total_gb)
            total_d=sum(yearly_total_d)
            total_x=sum(yearly_total_x)
            total_ngd=sum(yearly_total_ngd)
            # Update min_total_cost and optimal_bpc if the current total cost is lower
            if (total_c) < min_total_cost:
                min_total_cost = (total_c)
                optimal_bpc = bpc
            #print(f"Evaluated BPC: {bpc}, Total cost: {total_c}")
            

    #Cost Calculation of BESS+Solar+Grid System 

    optimized_fixed_component_cost_solar_grid_bess = 0
    optimized_variable_component_cost_solar_grid_bess = 0
    optimized_unmet_demand_cost_solar_grid_bess = 0
    optimized_capx_cost_solar_grid_bess = 0
    optimized_om_cost_solar_grid_bess = 0
    optimized_total_cost_solar_grid_bess_system = 0
    optimized_lcoe_solar_grid_bess = 0
    optimized_battery_power_capacity_solar_grid_bess = 0
    optimized_battery_size_solar_grid_bess = 0

    if option==2:
        initial_bpc=optimal_bpc
        yearly_total_demands=[]
        yearly_electricity_costs = []
        yearly_electricity_costs_nm = []
        max_values_per_year = []
        yearly_unmet_demand_costs = []
        yearly_om_costs = []
        max_gd1=0
        yearly_emis=[]
        yearly_total_sl=[]
        yearly_total_bl=[]
        yearly_total_gb=[]
        yearly_total_gl=[]
        yearly_total_sb=[]
        yearly_total_sg=[]
        yearly_total_d=[]
        yearly_total_x=[]
        yearly_total_ngd=[]
        
        for year in range(num_years):
            # Calculate the current cycle for battery replacement
            cycle = year // 10
            # Calculate current year's battery power capacity considering the replacement every 10 years
            bpc = initial_bpc * ((1 - battery_degradation_rate_yearly) ** (year % 10))
        
            # initialization of variables
            yearly_cost = 0
            yearly_unmet_demand_cost = 0
            yearly_dg_cost = 0
            yearly_demand=0
            yearly_emi=0
            yearly_sl=0
            yearly_bl=0
            yearly_gl=0
            yearly_sb=0
            yearly_gb=0
            yearly_sg=0
            yearly_d=0
            yearly_x=0
            yearly_ngd=0
            # Adjust tariff rates for the current year
            peak_tariff=normal_tariff+(normal_tariff*increment_on_peak_tariff)
            non_peak_tariff=normal_tariff-(normal_tariff*decrement_on_non_peak_tariff)
            current_normal_tariff = normal_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
            current_peak_tariff = peak_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
            current_non_peak_tariff = non_peak_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
            current_feed_in_tariff = feed_in_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
            current_vos = vos * ((1 + vos_escalation_rate_yearly) ** year)
            current_dg_cost = dg_cost * ((1 + dg_escalation_rate_yearly) ** year)
        
            monthly_ngd_peak = [0]*13
            monthly_ngd_off_peak = [0]*13
            monthly_ngd_normal = [0]*13
            
            # Iterate over each hour in the year
            for index in range(num_hours_in_year):
                # Calculate the current hour in the overall simulation
                current_hour = year * num_hours_in_year + index
                hour_of_day = index % (24*n)
        
                # Get the current hour's data from the original DataFrame for the first year or from calculated values for subsequent years
            
                if year == 0:
                    s = df.at[index, solar_generation] * solar_system_size    #solar generation
                    l = hourly_load_demand[index]
                else:
                    prev_index = (year - 1) * num_hours_in_year + index
                    s = calculated_values[prev_index]['solar_generation'] * (1 - solar_degradation_rate_yearly) 
                    l = calculated_values[prev_index]['load_demand'] * (1 + demand_escalation_rate_yearly)
        
        
                # Set outage status based on extended outage status list
                o = extended_outage_status[current_hour]
                
                # Add your further calculations and logic here...
                
                # Multiply 'load' and 'outage' for each hour and accumulate it
                l_o = l * o
                # Determine the tariff for the current hour
                if n==1:
                    if 16 <= hour_of_day < 22:  # Peak hours from 5:00 PM to 11:00 PM
                        hourly_tariff = current_peak_tariff
                    elif 22 <= hour_of_day or hour_of_day < 4:  # Non-peak hours from 11:00 PM to 5:00 AM
                        hourly_tariff = current_non_peak_tariff
                    else:  # Normal hours for the remaining time
                        hourly_tariff = current_normal_tariff
        
                if n==2:
                    if 32 <= hour_of_day < 44:  # Peak hours from 5:00 PM to 11:00 PM
                        hourly_tariff = current_peak_tariff
                    elif 44 <= hour_of_day or hour_of_day < 8:  # Non-peak hours from 11:00 PM to 5:00 AM
                        hourly_tariff = current_non_peak_tariff
                    else:  # Normal hours for the remaining time
                        hourly_tariff = current_normal_tariff
                if n==4:
                    if 64 <= hour_of_day < 88:  # Peak hours from 5:00 PM to 11:00 PM
                        hourly_tariff = current_peak_tariff
                    elif 88 <= hour_of_day or hour_of_day < 16:  # Non-peak hours from 11:00 PM to 5:00 AM
                        hourly_tariff = current_non_peak_tariff
                    else:  # Normal hours for the remaining time
                        hourly_tariff = current_normal_tariff
        
        
                # Initialize the variables
                sl= c = sb = d = sg = bg = gb = r = bl = x = gl =gd = gf = ngd = sc = lc = 0
        
                # Solar to load
                sl = min(s, l)
        
                if s > l:
                    c = s - l
                    sb = min(c, bpc, (1 - charge[current_hour]) * (bpc * hos*n))  # solar to battery
        
                    if (s - sl - sb) > 0 and o == 1:
                        d = c - sb  # power curtailment
                    else:
                        if (s - sl - sb) > 0 and o == 0:
                            sg = c - sb  # solar to grid
                        elif (s - sl - sb) < 0 and o == 0 and charge_from_grid:
                            gb = min(bpc, ((1 - charge[current_hour]) * (bpc * hos*n)))  # grid to battery
        
                if s < l and o == 1:
                    r = l - s  # residual load
                    available_charge = max(charge[current_hour] - min_charge, 0) * (bpc * hos * eff)  # prevent discharge below 20%
                    bl = min(available_charge*n, bpc, r)  # battery to the load
                    x = max(r - bl, 0)  # unmet demand
                else:
                    if s < l and o == 0 and hour_of_day in range(16*n, 22*n) and discharge_battery and charge[current_hour] > 0.5:
                        available_charge = max(charge[current_hour] - 0.5, 0) * (bpc * hos * eff)  # prevent discharge below 50%
                        bl = min(available_charge*n, bpc, l - s)  # Battery to the load
                        gl = l - s - bl  # Grid to load
                    else:
                        if s < l and o == 0:
                            gl = l - s  # Grid to load
        
                gd = gb + gl  # Grid draw
                gf = sg + bg  # Grid feed-in
                ngd = gd - gf  # Net grid draw
                sc = sl + sb + sg - s  # Solar check
                lc = sl + bl + gl - l  # Load check
        
                #Calculation of Grid Emission
        
                emi=ngd*(grid_carbon_factor/n)
                yearly_emi+=emi

                yearly_sl+=sl
                yearly_bl+=bl
                yearly_gl+=gl
                yearly_sb+=sb
                yearly_gb+=gb
                yearly_sg+=sg
                yearly_d+=d
                yearly_ngd+=ngd
                yearly_x+=x
                
                if metering_option == 1:
                    # Example usage to populate monthly_ngd_peak based on some data
                    month_key = calculate_month_key(index)
                    if n==1:               
                        if 16 <= hour_of_day < 22:
                            monthly_ngd_peak[month_key] += ngd     
                        elif 22 <= hour_of_day or hour_of_day < 4:
                            monthly_ngd_off_peak[month_key] += ngd              
                        else:
                            monthly_ngd_normal[month_key] += ngd
                    if n==2:               
                        if 32 <= hour_of_day < 44:
                            monthly_ngd_peak[month_key] += ngd     
                        elif 44 <= hour_of_day or hour_of_day < 8:
                            monthly_ngd_off_peak[month_key] += ngd              
                        else:
                            monthly_ngd_normal[month_key] += ngd
        
                    if n==4:               
                        if 64 <= hour_of_day < 88:
                            monthly_ngd_peak[month_key] += ngd     
                        elif 88 <= hour_of_day or hour_of_day < 16:
                            monthly_ngd_off_peak[month_key] += ngd              
                        else:
                            monthly_ngd_normal[month_key] += ngd
                
        
                if metering_option == 2:
                    hourly_electricity_cost = ((gd * hourly_tariff) - (sg * current_feed_in_tariff))/n
                    yearly_cost += hourly_electricity_cost
                    
                # Update maximum values of gd for the current year when there is no outage   
                if o == 0:
                    max_gd1 = max(max_gd1, gd)
            
                
                demand=l/n
                yearly_demand+=demand
            
                # Accumulate the unmet demand cost
                hourly_unmet_demand_cost = (x * current_vos)/n
                yearly_unmet_demand_cost += hourly_unmet_demand_cost 
                    
        
                # Ensure charge does not drop below minimum level
                charge[current_hour + 1] = charge[current_hour] + (((sb + gb) * eff - bl / eff) / (bpc * hos*n))
        
                # Append the calculated values to the list
                calculated_values.append({
                    'Year': year + 1,
                    'Hour': index + 1,
                    'solar_generation': s,
                    'load_demand': l,
                    'outage': o,
                    'sl': sl, 'c': c, 'sb': sb, 'd': d, 'sg': sg, 'bg': bg, 'gb': gb,
                    'r': r, 'bl': bl, 'x': x, 'gl': gl, 'gd': gd, 'gf': gf, 'ngd': ngd, 'sc': sc, 'lc': lc,
                    'hourly_tariff': hourly_tariff,
                    'charge': charge[current_hour]
                
                
                })
        
            # Append yearly maximum values and costs
            max_values_per_year.append({
                'Year': year + 1,
                'max_grid_load1': max_gd1
            })
        
            
                #print(monthly_ngd_peak)
            unitspk = monthly_ngd_peak
            billing_unitspk, total_banked_unitspk = calculate_billing(unitspk)
                #print("Billing units in year pk:", sum(billing_unitspk))
                #print("Total Banked Units at the end of the period:", total_banked_unitspk)
            yearly_peak_cost=((sum(billing_unitspk)*current_peak_tariff/n)-(total_banked_unitspk*(current_feed_in_tariff/n)))
            
            unitsopk = monthly_ngd_off_peak
            billing_unitsopk, total_banked_unitsopk = calculate_billing(unitsopk)
                #print("Billing units in year: opk", sum(billing_unitsopk))
                #print("Total Banked Units at the end of the period:", total_banked_unitsopk)
            yearly_off_peak_cost=(sum(billing_unitsopk)*(current_non_peak_tariff/n)-(total_banked_unitsopk*(current_feed_in_tariff/n)))
            
            unitsn = monthly_ngd_normal
            billing_unitsn, total_banked_unitsn = calculate_billing(unitsn)
                #print("Billing units in year: n", sum(billing_unitsn))
                #print("Total Banked Units at the end of the period:", total_banked_unitsn)
            yearly_nor_cost=(sum(billing_unitsn)*(current_normal_tariff/n)-(total_banked_unitsn*(current_feed_in_tariff/n)))
            
            yearly_cost_nm=yearly_peak_cost+yearly_off_peak_cost+yearly_nor_cost
                #print(yearly_cost)
        
            yearly_electricity_costs.append(yearly_cost*(1/(1+discount_factor)**year))
            yearly_electricity_costs_nm.append(yearly_cost_nm*(1/(1+discount_factor)**year))
            yearly_unmet_demand_costs.append(yearly_unmet_demand_cost*(1/(1+discount_factor)**year))
            yearly_total_demands.append(yearly_demand*(1/(1+discount_factor)**year))
            yearly_emis.append (yearly_emi)
            yearly_total_sl.append (yearly_sl)
            yearly_total_bl.append (yearly_bl)
            yearly_total_gl.append (yearly_gl)
            yearly_total_sb.append (yearly_sb)
            yearly_total_sg.append (yearly_sg)
            yearly_total_gb.append (yearly_gb)
            yearly_total_d.append (yearly_d)
            yearly_total_x.append (yearly_x)
            yearly_total_ngd.append (yearly_ngd)
                
                # Calculate the total fixed component cost over all years
        total_fixed_component_cost = sum(max_values_per_year[year]['max_grid_load1'] *12* demand_charge*((1+demand_escalation_rate_yearly)/(1+discount_factor)**year)
                    for year in range(num_years))
                
                # Calculate the total electricity cost over all years
        if metering_option==1:
            total_electricity_cost = sum(yearly_electricity_costs_nm)
        if metering_option==2:
            total_electricity_cost = sum(yearly_electricity_costs)
                #total demand
        total_demand=sum(yearly_total_demands)
            
                # Calculate the cost of unmet demand
        total_unmet_demand_cost = sum(yearly_unmet_demand_costs)
        
            #Total Carbon emission
        
        total_emi=sum(yearly_emis)
        total_carbon_savings_cost=total_emi*carbon_cost
        
        total_demand=sum(yearly_total_demands)
        
            
                
                # Calculate the solar module cost 
        solar_module_cost = solar_system_size * initial_solar_module_cost
        total_battery_cost = initial_bpc* hos * battery_costs[0] # Initial battery cost
        
                
                # Add the replacement costs
        total_battery_cost += sum([initial_bpc * hos * battery_costs[year] for year in battery_replacement_schedule])
                
                # Total Capex cost
        Capx_cost = solar_module_cost + total_battery_cost
        
        initial_om_cost = 0.01 * (solar_module_cost+ initial_bpc*hos*initial_battery_cost)
            
            
            # O&M cost
        yearly_om_costs=[]
        for year in range(num_years):
            if year == 0:
                yearly_om_cost = initial_om_cost
            else:
                yearly_om_cost = initial_om_cost * ((1 + om_cost_escalation_rate) ** year)
                
            yearly_om_costs.append(yearly_om_cost*(1/(1+discount_factor)**year))
                
                    # Accumulate the total O&M cost
        total_om_cost = sum(yearly_om_costs)
        
            #Total cost for BESS system
            
        total_c = total_fixed_component_cost + total_unmet_demand_cost + Capx_cost + total_om_cost + total_electricity_cost+total_carbon_savings_cost
        total_battery_size=optimal_bpc*hos
        total_sl=sum(yearly_total_sl)
        total_bl=sum(yearly_total_bl)
        total_gl=sum(yearly_total_gl)
        total_sb=sum(yearly_total_sb)
        total_sg=sum(yearly_total_sg)
        total_gb=sum(yearly_total_gb)
        total_d=sum(yearly_total_d)
        total_x=sum(yearly_total_x)
        total_ngd=sum(yearly_total_ngd)
        st.metric(label="Optimized LCOE for solar+Grid+BESS system", value=f"{total_c/total_demand:.2f} INR/kWh")
        st.metric(label="Optimized battery size for the solar+Grid+BESS system", value=f"{optimal_bpc:.0f}kW/{total_battery_size:.0f} kWh")


    #Cashflow Table for Grid+Solar+BESS system


    # Initialize numpy arrays for yearly costs
    total_fixed_component_costc = np.zeros(num_years)
    total_electricity_costc = np.zeros(num_years)
    total_unmet_demand_costc = np.zeros(num_years)
    total_electricity_costc_nm= np.zeros(num_years)
    total_om_costc = np.zeros(num_years)
    total_coc = np.zeros(num_years)
    total_capexc = np.zeros(num_years)

    # Assign CAPEX cost for the first year
    total_capexc[0] = Capx_cost

    # Calculate the yearly costs
    for year in range(num_years):
        total_fixed_component_costc[year] = max_values_per_year[year]['max_grid_load1'] * 12 * demand_charge * ((1 + demand_escalation_rate_yearly) / (1 + discount_factor) ** year)
        if metering_option==1:
            total_electricity_costc[year]=yearly_electricity_costs_nm[year]
        if metering_option==2:
            total_electricity_costc[year] = yearly_electricity_costs[year] 
        total_unmet_demand_costc[year] = yearly_unmet_demand_costs[year]
        total_om_costc[year] = yearly_om_costs[year]
        total_coc[year] = total_fixed_component_costc[year] + total_electricity_costc[year] + total_om_costc[year] + total_unmet_demand_costc[year] + total_capexc[year]

    # Print the total costs for verification
    #print("Fixed Cost DG Cost per year: ", total_fixed_component_costc)
    #print("Variable Electricity Bill DG per year: ", total_electricity_costc)
    #print("DG Costs per year: ", total_unmet_demand_costc)
    #print("Total O&M Costs per year: ", total_om_costc)
    #print("CAPEX Cost per year: ", total_capexc)
    #print("Total Costs per year: ", total_coc)

    cashflow_table = np.array([total_fixed_component_costc, total_electricity_costc,total_unmet_demand_costc, total_om_costc, total_capexc, total_coc]).T

    # Print the cashflow table
    #print("\nCashflow Table Array:")
    #print("Year | Fixed Cost | Variable Electricity Bill|  | Unmet Demand Costs | O&M Costs | CAPEX | Total Costs")
    #for year in range(num_years):
    # print(f"{year + 1}    | {total_fixed_component_costc[year]:.2f}        | {total_electricity_costc[year]:.2f}                 | {total_unmet_demand_costc[year]:.2f}     | {total_om_costc[year]:.2f}   | {total_capexc[year]:.2f}   | {total_coc[year]:.2f} ")
    #Calculation of power power for Grid+DG scenario

    calculated_values = []
    max_values_per_year = []
    yearly_dg_costs=[]
    yearly_dg_grid_emis=[]
    yearly_dg_dg_emis=[]
    yearly_electricity_variable_bills_dg = []
    max_gd_dg1=0
    yearly_total_demands=[]

    for year in range(num_years):
        
    # initialization of variables 
        
        yearly_dg_cost = 0
        yearly_electricity_variable_bill_dg_year=0
        max_load=0
        yearly_dg_grid_emi=0
        yearly_demand=0
        yearly_dg_dg_emi=0
        
        # Adjust tariff rates for the current year
        
        peak_tariff=normal_tariff+(normal_tariff*increment_on_peak_tariff)
        non_peak_tariff=normal_tariff-(normal_tariff*decrement_on_non_peak_tariff)
        current_normal_tariff = normal_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
        current_peak_tariff = peak_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
        current_non_peak_tariff = non_peak_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
        current_feed_in_tariff = feed_in_tariff * ((1 + tariff_escalation_rate_yearly) ** year)
        current_dg_cost = dg_cost * ((1 + dg_escalation_rate_yearly) ** year)
        
        # Iterate over each hour in the year
        for index in range(num_hours_in_year):
            # Calculate the current hour in the overall simulation
            current_hour = year * num_hours_in_year + index
            hour_of_day = index % (24*n)

            # Get the current hour's data from the original DataFrame for the first year or from calculated values for subsequent years
        
            if year == 0:
                l = hourly_load_demand[index]
            else:
                prev_index = (year - 1) * num_hours_in_year + index
                l = calculated_values[prev_index]['load_demand'] * (1 + demand_escalation_rate_yearly)
                

            # Set outage status based on extended outage status list
            o = extended_outage_status[current_hour]
            
            # Add your further calculations and logic here...
            demand=l/n
            yearly_demand+=demand
            
            # Multiply 'load' and 'outage' for each hour and accumulate it
            l_o = l * o
            # Determine the tariff for the current hour
            if n==1:
                if 16 <= hour_of_day < 22:  # Peak hours from 5:00 PM to 11:00 PM
                    hourly_tariff = current_peak_tariff
                elif 22 <= hour_of_day or hour_of_day < 4:  # Non-peak hours from 11:00 PM to 5:00 AM
                    hourly_tariff = current_non_peak_tariff
                else:  # Normal hours for the remaining time
                    hourly_tariff = current_normal_tariff

            if n==2:
                if 32 <= hour_of_day < 44:  # Peak hours from 5:00 PM to 11:00 PM
                    hourly_tariff = current_peak_tariff
                elif 44 <= hour_of_day or hour_of_day < 8:  # Non-peak hours from 11:00 PM to 5:00 AM
                    hourly_tariff = current_non_peak_tariff
                else:  # Normal hours for the remaining time
                    hourly_tariff = current_normal_tariff
            if n==4:
                if 64 <= hour_of_day < 88:  # Peak hours from 5:00 PM to 11:00 PM
                    hourly_tariff = current_peak_tariff
                elif 88 <= hour_of_day or hour_of_day < 16:  # Non-peak hours from 11:00 PM to 5:00 AM
                    hourly_tariff = current_non_peak_tariff
                else:  # Normal hours for the remaining time
                    hourly_tariff = current_normal_tariff

            # Initialize the variables
            
            gd_dg=gd_die=0
        

            #Calculation of maximum load 

            max_load=max(max_load,l)

            
            #calculation for Grid+DG
            
            if o==0:
                gd_dg=l
            if o==1:
                gd_die=l
                
            #Carbon emission for Grid+DG

            dg_grid_emi=gd_dg *(grid_carbon_factor/n)
            dg_dg_emi=gd_die*(dg_carbon_factor/n)
            
            yearly_dg_grid_emi+=dg_grid_emi
            yearly_dg_dg_emi+=dg_dg_emi
            
            
            # Update maximum values of gd for the current year when there is no outage   
            if o == 0:
                max_gd_dg1=max(max_gd_dg1,gd_dg)
            
            
            # Accumulate yearly electricity cost
            hourly_electricity_variable_bill_dg = ((l - l_o) * hourly_tariff)/n
            yearly_electricity_variable_bill_dg_year += hourly_electricity_variable_bill_dg

            # Accumulate yearly generator cost
            
            hourly_dg_cost = ((l_o) * current_dg_cost)/n
            yearly_dg_cost += hourly_dg_cost
        

            # Append the calculated values to the list
            calculated_values.append({
                'Year': year + 1,
                'Hour': index + 1,
                'load_demand': l,
                'outage': o,
                'gd_dg':gd_dg, 'gd_die': gd_die,'dg_grid_emi':dg_grid_emi, 'dg_dg_emi':dg_grid_emi, 'hourly_tariff': hourly_tariff,
                
            
            })
        overall_max_load = max(overall_max_load, max_load)
        
        # Append yearly maximum values and costs
        max_values_per_year.append({
            'Year': year + 1,
            'max_grid_load_dg1':max_gd_dg1,
            'max_demand_load':max_load
        })
        
        
        yearly_electricity_variable_bills_dg.append(yearly_electricity_variable_bill_dg_year*(1/(1+discount_factor)**year))
        yearly_dg_costs.append(yearly_dg_cost*(1/(1+discount_factor)**year))
        yearly_dg_grid_emis.append(yearly_dg_grid_emi)
        yearly_dg_dg_emis.append(yearly_dg_dg_emi)
        yearly_total_demands.append(yearly_demand*(1/(1+discount_factor)**year))
        
        
    #print(f'The maximum load value over 25 years is: {overall_max_load}')

    #Cost Calculation of Grid+DG

    #Fixed cost component for DG+Grid
    fixed_cost_dg_cost=sum( max_values_per_year[year]['max_grid_load_dg1'] *12* demand_charge*((1+demand_escalation_rate_yearly)/(1+discount_factor)**year)
        for year in range(num_years))

    # Electricity bill variable component for Grid+DG
    total_electricity_variable_bill_dg = sum(yearly_electricity_variable_bills_dg)

    #DG cost for Grid+DG
    total_yearly_dg_costs = sum(yearly_dg_costs)


    #Calculate the total demand of Grid+DG system
    total_demand=sum(yearly_total_demands)

    #Calculate the carbon emission cost Grid+DG system

    total_dg_grid_emi=sum(yearly_dg_grid_emis)
    total_dg_dg_emi=sum(yearly_dg_dg_emis)
    total_dg_emi=(total_dg_grid_emi+total_dg_dg_emi)
    total_dg_emi_cost=(total_dg_emi)*carbon_cost


    # Calculate the total cost with DG+ grid electricity
    total_cost_dg_grid = fixed_cost_dg_cost + total_electricity_variable_bill_dg + total_yearly_dg_costs+total_dg_emi_cost

    #Calculation of LCOE cost
    grid_dg_lcoe=(total_cost_dg_grid)/(total_demand)


    #st.write(f"Total fixed component cost of electricity for Grid+DG system: {format_indian_currency(fixed_cost_dg_cost)}")
    #st.write(f"Total variable component cost of electricity Grid+DG system: {format_indian_currency(total_electricity_variable_bill_dg)}")
    #st.write(f"Total diesel cost for Grid+DG system: {format_indian_currency(total_yearly_dg_costs)}")
    st.metric(label="Total cost for Grid+DG system", value=format_indian_currency(total_cost_dg_grid))
    st.metric(label="LCOE for Grid+DG system", value=f"{grid_dg_lcoe:.2f} INR/kWh")

    #Cashflow Table for Grid+DG system

    fixed_cost_dg_costs = np.zeros(num_years)
    variable_electricity_bills_dg = np.zeros(num_years)
    dg_costs = np.zeros(num_years)
    total_costs = np.zeros(num_years)


    # Calculate the yearly costs
    for year in range(num_years):
        fixed_cost_dg_costs[year] = max_values_per_year[year]['max_grid_load_dg1'] * 12 * demand_charge * ((1 + demand_escalation_rate_yearly) / (1 + discount_factor) ** year)
        variable_electricity_bills_dg[year] = yearly_electricity_variable_bills_dg[year]
        dg_costs[year] = yearly_dg_costs[year]
        total_costs[year] = fixed_cost_dg_costs[year] + variable_electricity_bills_dg[year] + dg_costs[year]
        
    total_cost_all_components = np.sum(total_costs)

    # Print the total costs for verification
    #print("Fixed Cost DG Cost per year: ", fixed_cost_dg_costs)
    #print("Variable Electricity Bill DG per year: ", variable_electricity_bills_dg)
    #print("DG Costs per year: ", dg_costs)
    #print("Total Costs per year: ", total_costs)

    cashflow_table = np.array([fixed_cost_dg_costs, variable_electricity_bills_dg, dg_costs, total_costs]).T

    # Print the cashflow table
    #print("\nCashflow Table Array:")
    #print("Year | Fixed Cost DG | Variable Electricity Bill DG | DG Costs | Total Costs")
    #for year in range(num_years):
    #    print(f"{year + 1}    | {fixed_cost_dg_costs[year]:.2f}        | {variable_electricity_bills_dg[year]:.2f}                 | {dg_costs[year]:.2f}     | {total_costs[year]:.2f}")

    #Cashflow of Solar+BESS+Grid-Grid+DG System
    cost_difference = total_coc - total_costs
    # Calculate cumulative cost difference
    cumulative_cost_difference = [sum(cost_difference[:i+1]) for i in range(num_years)]

    # Print the resulting cashflow table
    #print("Year |  Total Costs (Solar+BESS) | Total Costs (Grid+DG) | Cost Difference | Cumulative Cost Difference")
    #for year in range(num_years):
    # print(f"{year + 1}    |  {total_coc[year]:.2f}                 | {total_costs[year]:.2f}             | {cost_difference[year]:.2f}             | {cumulative_cost_difference[year]:.2f}")

    # Find the payback period
    payback_period = next((i+1 for i, diff in enumerate(cumulative_cost_difference) if diff <= 0), None)

    #Install if your system doesn't have preinstalled
    #!pip install nump

    # Calculation of IRR

    # Calculate IRR
    anti_discount_factor = [1]*num_years


    for i in range(num_years):
        anti_discount_factor[i] = (1+discount_factor)**i


    cash_flows = ((cost_difference)*(anti_discount_factor))

    irr = npf.irr(cash_flows)

    # Print IRR
    #print(f"Internal Rate of Return (IRR): {irr:.2%}")

    #Dashboard Data
    net_savings=total_cost_dg_grid-total_c+Capx_cost

    # Display the System CAPX Cost
    #st.write(f"System Capx cost: {format_indian_currency(Capx_cost)}")

    # Display the System NPV
    #st.write(f"System NPV: {format_indian_currency(net_savings - Capx_cost)}")

    st.metric(label="Payback Period", value=f"{payback_period} years")

    st.metric(label="Internal Rate of Return (IRR)", value=f"{irr:.2%}")

    st.metric(label="Lifetime savings", value=format_indian_currency(net_savings))

    st.metric(label="Lifetime avoided emissions", value=f"{(total_dg_emi - total_emi) / 1000:.0f} tCO2")

    if option == 2:
        st.metric(label="Optimized battery size for the solar+Grid+BESS system", value=f"{optimal_bpc:.0f}kW/{total_battery_size:.0f} kWh")



    # Display the Total Demand over the 25 Years Period
    #st.write(f"The total demand over the 25 years period is: {sum(yearly_total_demands_nd):.0f} kWh")



    # Data to plot
    labels = ['Solar', 'BESS', 'Grid', 'Unmet Demand']
    sizes = [total_sl, total_bl, total_gl, total_x]
    colors = ['#009CD8', '#8DB824', '#EA5813', '#9D9D9C']

    # Pie Chart for Share of Demand Met from Sources
    fig1 = go.Figure(data=[go.Pie(labels=labels, values=sizes, hole=.3)])
    fig1.update_traces(marker=dict(colors=colors, line=dict(color='white', width=3)))
    fig1.update_layout(title_text='Share of Demand Met from sources')

    # Data to plot for share of usage of solar energy
    labels1 = ['Direct to load', 'Charging the battery', 'Fed to the Grid', 'Power Curtailed']
    sizes1 = [total_sl, total_sb, total_sg, total_d]
    colors1 = ['#009CD8', '#8DB824', '#EA5813', '#9D9D9C']

    # Pie Chart for Share of Usage of Solar Energy
    fig2 = go.Figure(data=[go.Pie(labels=labels1, values=sizes1, hole=.3)])
    fig2.update_traces(marker=dict(colors=colors1, line=dict(color='white', width=3)))
    fig2.update_layout(title_text='Share of Usage of Solar Energy')

    # Data for the gross electricity drawn from the grid
    categories = ['Electricity from Grid to load', 'Electricity from Grid to battery', 'Electricity Fed to Grid from Solar', 'Net Electricity from Grid']
    values = [total_gl / (n * 1000), total_gb / (n * 1000), -total_sg / (n * 1000), total_ngd / (n * 1000)]
    colors2 = ['#009CD8', '#8DB824', '#EA5813', '#9D9D9C']

    # Waterfall Chart for Lifetime Electricity Consumption from Grid
    fig3 = go.Figure()
    cumulative_values = [0] + [sum(values[:i + 1]) for i in range(len(values) - 1)]
    for i, (category, value, cumulative) in enumerate(zip(categories, values, cumulative_values)):
        fig3.add_trace(go.Bar(
            x=[category],
            y=[value],
            base=[cumulative],
            marker_color=colors2[i],
            name=category
        ))

    fig3.update_layout(title_text='Lifetime Electricity Consumption from Grid', yaxis_title='Electricity (MWh)', barmode='stack')

    # Data for total cost of ownership
    categories1 = ['Total Grid+DG cost', 'System Component cost', 'Diesel Savings', 'Demand Charges', 'Energy Charges', 'Unmet Demand Cost', 'Solar+BESS+Grid']
    values1 = [total_cost_dg_grid / 1000000, (Capx_cost + total_om_cost) / 1000000, -total_yearly_dg_costs / 1000000, (total_fixed_component_cost - fixed_cost_dg_cost) / 1000000, (total_electricity_cost - total_electricity_variable_bill_dg) / 1000000, total_unmet_demand_cost / 1000000, total_c / 1000000]

    # Waterfall Chart for Total Cost of Ownership
    fig4 = go.Figure()
    cumulative_values1 = [0] + [sum(values1[:i + 1]) for i in range(len(values1) - 1)]
    colors3 = ['#009CD8'] + ['#8DB824' if v > 0 else '#EA5813' for v in values1[1:-1]] + ['#9D9D9C']

    for i, (category, value, cumulative) in enumerate(zip(categories1, values1, cumulative_values1)):
        fig4.add_trace(go.Bar(
            x=[category],
            y=[value],
            base=[cumulative],
            marker_color=colors3[i],
            name=category
        ))

    fig4.update_layout(title_text='Total Cost of Ownership - Solar + BESS + Grid vs Grid + DG Set', yaxis_title='₹ Lakh', barmode='stack')

    # Data for total cost of ownership in terms of LCOE
    categories2 = ['Total Grid+DG cost', 'System Component cost', 'Diesel Savings', 'Demand Charges', 'Energy Charges', 'Unmet Demand Cost', 'Solar+BESS+Grid']
    values2 = [total_cost_dg_grid / total_demand, (Capx_cost + total_om_cost) / total_demand, -total_yearly_dg_costs / total_demand, (total_fixed_component_cost - fixed_cost_dg_cost) / total_demand, (total_electricity_cost - total_electricity_variable_bill_dg) / total_demand, total_unmet_demand_cost / total_demand, total_c / total_demand]

    # Waterfall Chart for Total Cost of Ownership in terms of LCOE
    fig5 = go.Figure()
    cumulative_values2 = [0] + [sum(values2[:i + 1]) for i in range(len(values2) - 1)]
    colors4 = ['#009CD8'] + ['#8DB824' if v > 0 else '#EA5813' for v in values2[1:-1]] + ['#9D9D9C']

    for i, (category, value, cumulative) in enumerate(zip(categories2, values2, cumulative_values2)):
        fig5.add_trace(go.Bar(
            x=[category],
            y=[value],
            base=[cumulative],
            marker_color=colors4[i],
            name=category
        ))

    fig5.update_layout(title_text='Total Cost of Ownership - Solar + BESS + Grid vs Grid + DG Set (LCOE)', yaxis_title='₹/kWh', barmode='stack')

    # Displaying in Streamlit
    st.title('Energy System Analysis')

    # First row: Pie charts
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.plotly_chart(fig2, use_container_width=True)

    # Second row: Waterfall charts for electricity consumption and total cost of ownership
    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(fig3, use_container_width=True)
    with col4:
        st.plotly_chart(fig4, use_container_width=True)

    # Third row: Waterfall chart for total cost of ownership in terms of LCOE
    st.plotly_chart(fig5, use_container_width=True)
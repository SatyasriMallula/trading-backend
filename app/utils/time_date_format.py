from datetime import datetime

def format_date(date_obj: datetime):  
    # Use the provided date_obj instead of always using current time
    formatted_date = date_obj.strftime("%Y-%m-%d")
    return formatted_date

def format_time(date_obj: datetime):  
    # Use the provided date_obj instead of always using current time
    formatted_time = date_obj.strftime("%H:%M:%S")
    return formatted_time
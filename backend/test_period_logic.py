from datetime import datetime

start_date = datetime(2026, 1, 1, 0, 0, 0)
end_date = datetime(2027, 12, 31, 23, 59, 59)

# Simulate a date after the feedback period closes
test_now = datetime(2028, 1, 1, 0, 0, 0)

is_open = start_date <= test_now <= end_date

print("Feedback period open:", is_open)
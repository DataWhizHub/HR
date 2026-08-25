"""
Central configuration for the HR Leave Request app.
Change these values to match how you set up your Google Sheet.
"""

# ---- Google Sheet ----
SHEET_NAME = "HR_Leave_System"      # The exact name of your Google Sheet (spreadsheet file)
USERS_TAB = "Users"                 # Tab that holds login + employee master data
REQUESTS_TAB = "LeaveRequests"      # Tab that holds every leave request

USER_COLUMNS = [
    "Username", "PasswordHash", "EmpNo", "Name", "Designation", "Email", "Role",
]

REQUEST_COLUMNS = [
    "RequestID", "Username", "EmpNo", "Name", "Designation",
    "ActingOfficerUsername", "ActingOfficerName", "ActingOfficerEmail",
    "LeaveType", "LeaveDate", "ReturnDate", "Reason",
    "Status", "HRRemarks", "RequestedOn", "DecidedOn",
]

LEAVE_TYPES = ["Annual Leave", "Casual Leave", "Medical Leave", "Short Leave", "Other"]

STATUS_PENDING = "Pending"
STATUS_APPROVED = "Approved"
STATUS_REJECTED = "Rejected"

ROLE_USER = "User"
ROLE_HR = "HR-KMN"

import os
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"  # Default to 5000 if PORT is not set
workers = 1
threads = 1
timeout = 300


# Meetup endpoints
MEETUP_API_URI="https://api.meetup.com/2/"
MEETUP_EVENTS_URI="{m}events/".format(m=MEETUP_API_URI)
MEETUP_RSVPS_URI="{m}rsvps/".format(m=MEETUP_API_URI)

# GDATA / Docs List
# This is the Google recommended chunk size.  
CHUNK_SIZE = 10485760

#====== Specific to you and your event ================
# The group name that appears in the Meetup URL.
# For example, http://www.meetup.com/NYC-GTUG/
GROUP_URLNAME="your_meetup_url_name"

# You must obtain a Meetup API key. http://www.meetup.com/meetup_api/ 
API_KEY="your_key"

# Your Google email and password for client authentication
EMAIL="your_email!@gmail.com"
PASSWORD="your_password"

# A dictionary of people with whom you want to share the spreadsheet.
# A dictionary is a Python key:value structure, and in this case the key is
# the recipients Google email and the value is a string that indicate their
# collaboration role.  Either "reader" or "writer".
COLLABORATORS = {"bilbo.baggins@gmail.com":"writer", "someone@gmail.com":"reader"}
# Meetup endpoints
MEETUP_API_URI="https://api.meetup.com/2/"
MEETUP_EVENTS_URI="{m}events/".format(m=MEETUP_API_URI)
MEETUP_RSVPS_URI="{m}rsvps/".format(m=MEETUP_API_URI)

#====== Meetup API ================
# The group name that appears in the Meetup URL.
# For example, http://www.meetup.com/NYC-GDG/
GROUP_URLNAME="NYC-GDG"

# You must obtain a Meetup API key. http://www.meetup.com/meetup_api/ 
API_KEY="your api key" #browser


#=========== Google Drive API ============
#GOOGEL_SERVER_API_KEY="AIzaSyB6sBKzf5f3s0SeJZzUK-Se-QLkUBubnTw"
CLIENT_ID = "you Google API client id"
CLIENT_SECRET = "your Google API client secret"
# Redirect URI for installed apps
REDIRECT_URI = 'redirect uri'

# Check https://developers.google.com/drive/scopes for all available scopes
OAUTH_SCOPE = 'https://www.googleapis.com/auth/drive'

# A dictionary of people with whom you want to share the spreadsheet.
# key is the collaborator's Google email
# value is 'owner', 'writer' or 'reader'
COLLABORATORS = {"hancock.robert.test@gmail.com":"writer"}

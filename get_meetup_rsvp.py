"""
Retrieve the "yes" entries for a specific Meetup id.
Write the names to a Google Drive spreadsheet.
"""
import os.path
import sys
import json
import operator
import time
import string
import pprint
import optparse
import codecs
import webbrowser
from datetime import datetime
from apiclient import errors
import requests as req

#import mechanize

if sys.version[0:3] != "2.7":
    print("The Google API client requires Python 2.7.x.")
    sys.exit(-1)
    
try:
    import settings
except ImportError:
    sys.stderr.write("You need to have settings.py in the same directory as this file.")
    sys.exit(1)

try:    
    import httplib2    
except ImportError as e:
    sys.stderr.write("You need to install httplib2.  You can get it at http://code.google.com/p/httplib2/")
    sys.exit(1)

try:    
    import requests
except ImportError as e:
    sys.stderr.write("You need to install requests.  See http://docs.python-requests.org/en/latest/user/install/#install")
    sys.exit(1)

from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from oauth2client.client import OAuth2WebServerFlow

    
__author__ = "hancock.robert@gmail.com"
__version__ = "1.2"


class HTTPError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr("HTTPError: "+self.value)

        
def get_next_eventid():
    """ Get the next event, from today, in this group.
    
    Returns
        event id as a string
    """
    get_events_uri = "{u}?key={k}&sign=true&status=upcoming&group_urlname={i}".format(u=settings.MEETUP_EVENTS_URI,
                                                                                      k=settings.API_KEY,
                                                                                      i=settings.GROUP_URLNAME)
    resp = req.get(get_events_uri)
    if resp.status_code != 200:
        raise HTTPError("Status code={c}".format(c=resp.status_code))
    
    j = resp.json()
    event_url =  j["results"][0]["event_url"]
    components = event_url.split('/')
    
    return components[-2]
    
        
class RSVP():
    """ The Meetup RSVP class.
    
    args
        event_id   The unique id that Meetup uses to identify this event.
    
    """
    def __init__(self, event_id, strict_names=False):
        self.event_id = event_id
        self.json_rsvps = {}
        self.names = []
        self.tempfile = None
        self.tempfile_name = os.path.join(os.getcwd(), str(int(time.time()))) + ".csv"
        self.strict_names = strict_names
        self.trans = list(string.punctuation) # for unicode cleaning
        
        
    def download(self):
        """
        Get the "YES" RSVPs for this event.
        
        return
           a dictionary of the json contents
        """

        get_rsvps_uri = "{u}?key={k}&sign=true&event_id={i}".format(u=settings.MEETUP_RSVPS_URI, k=settings.API_KEY, i=self.event_id)
        resp = req.get(get_rsvps_uri)
        if resp.status_code != 200:
            raise HTTPError('Status code={c}'.format(c=resp.status_code))

        self.json_rsvps = resp.json()

        
    def get_names(self):
        """
        Extract first, middle, and last name from json and create a 
        list, the instance variable self.names, sorted by last name.
        
        Since these are likely to be printed on small badges we ignore middle initials
        and concentate on last names that consist of more than one word or have titles 
        after them.
        
        Bilbo B. Baggins, Esq.
        Zeljko R. Miscosich Rentlanich
        
        becomes [fname] [lname]
        
        [Bilbo] [Baggins, Esq.]
        [Zeljko] [Miscosich Rentlanich]
        
        Encode everything to UTF-8.
        """
        results = self.json_rsvps["results"]
        
        for line in results:
            # For debugging: it "pretty prints" the dictonary to stdout
            #if line["member"]:
                #pprint.pprint(line)
                #print("-"*75)
                
            if line["response"] != 'yes':
                continue
            
            name = unicode(line["member"]["name"])
            name = self._clean_unicode(name)

            if self.strict_names:
                if len(name) < 4:
                    sys.stderr.write("Removed: '{f}' - invalid full name.\n".format(f=name))
                    continue
            
            name_components = name.strip().strip(',').split()
            if not name_components:
                continue
            
            if self.strict_names and len(name_components) < 2:
                    sys.stderr.write("Removed: '{f}' - invalid full name.\n".format(f=name))
                    continue
                            
            fname = lname = ""
            
            fname = name_components[0]
            if self.strict_names and len(fname) == 1:
                    sys.stderr.write("Removed: '{f}' - first name cannot be one letter.\n".format(f=name))
                    continue
            
            fname = fname[0].upper()+fname[1:]
            lname = " ".join(name_components[1:])
            
            if lname:
                lname = lname[0].upper()+lname[1:]
                if self.strict_names and len(lname) == 1:
                        sys.stderr.write("Removed: '{l}' last name cannot be one letter.\n".format(l=name))
                        continue
                
            self.names.append((fname,lname))
            
        self.names = sorted(self.names, key=operator.itemgetter(1))

    
    def write_to_file(self):
        """ Write the list of names to a CSV file. """
        with codecs.open(self.tempfile_name, mode="w", encoding="utf-8") as self.tempfile:
            for entry in self.names:
                fname, lname = entry
                self.tempfile.write(fname+","+lname+"\n")
        
        
    def _clean_unicode(self, s):
        """ A naive way to clean punctuations chars from the unicode string. """
        for c in s:
            if c in self.trans:
                i = s.find(c)
                if i == len(s) - 1:
                    s = s[:1]
                else:
                    s = s[:i] + s[i+1:]
        return s
 
 
def get_oauth_creds():
    """OAuth credentials to access the Google Driver service.
    """
    flow = OAuth2WebServerFlow(settings.CLIENT_ID, settings.CLIENT_SECRET, 
                               settings.OAUTH_SCOPE, settings.REDIRECT_URI)
    authorize_url = flow.step1_get_authorize_url()
    #TODO:  mechanize
    #br = mechanize.Browser()
    #br.open(authorize_url)
    #br.select_form(nr=0)
    #resp = br.submit()
    
    #  req = br.click(id="submit_approve_access", name="true", type="submit", nr=0)
    # br.open(req)        
    #        resp = br.submit()
    #       data = resp.get_data()
    
    # web browser verson
    webbrowser.open_new_tab(authorize_url)
    code = raw_input('Enter verification code: ').strip()
    credentials = flow.step2_exchange(code)
    
    # Create an httplib2.Http object and authorize it with our credentials
    http = httplib2.Http()
    creds = credentials.authorize(http)
    return creds

  	    
def upload_csv(creds, fname, title):
    """Upload csv file to Drive spreadsheet. """

    drive_service = build('drive', 'v2', http=creds)
    
    media_body = MediaFileUpload(fname, mimetype='text/csv', resumable=True)
    body = {
        'title': title,
        'description': 'GDG RSVP LIST',
        'mimeType': 'text/csv'
    }
    
    f = drive_service.files().insert(body=body, media_body=media_body, 
                                     convert=True).execute() 
    
    return (drive_service, f)


def add_collaborators(service, file_id):
    """Add colloborators to the spreadsheet.
    
    Args:
    service: Drive API service instance.
    file_id: ID of the file to which you want to add collaborators.
    
    """
    for email, role in settings.COLLABORATORS.iteritems():
        new_permission = {
            'value': email,
            'type': "user",
            'role': role
        }
    
        try:
            service.permissions().insert(fileId=file_id, 
                                         body=new_permission).execute()
        except errors.HttpError, error:
            raise("HTTP Error: %s" % error)
    
    
def main():
    usage = "%prog [-inv]"
    parser = optparse.OptionParser(usage)
    parser.add_option("-i", "--event-id",
                      action="store", type="string", dest="eventid",
                      help="Use this event id and do not attempt to find the next one automatically on Meetup.")
    parser.add_option("-v", "--version",
                      action="store_true", dest="version",
                      help="Print version.")
    parser.add_option("-n", "--strict-name-filtering",
                      action="store_true", dest="strict_name_filtering",
                      help="Use strict name filtering rules.")
    
    [options, args] = parser.parse_args()
    if options.version:
        print("Version: {v}".format(v=__version__))
        return 0
    
    use_strict_names = True if options.strict_name_filtering else False
    
    if not options.eventid:
        try:
            event_id = get_next_eventid()
        except HTTPError as e:
            print("Error obtaining next event id from Meetup: %s" % e)
            sys.exit(1)
    else:
        event_id = options.eventid
        
    
    # Get the YES responses from Meetup and filter.
    rsvp = RSVP(event_id, strict_names=use_strict_names)
    try:
        rsvp.download()
    except HTTPError as e:
        sys.stderr.write("Cannot download event {i}: {e}".format(i=event_id, e=e))
        sys.exit(1)
        
    rsvp.get_names()
    if not rsvp.names:
        sys.stderr.write("No names were found for event id {ei}.".format(ei=event_id))
        sys.exit(-1)
        
    rsvp.write_to_file()
    
    # This is the text that will appear in the Google Drive as the spreadsheet name.
    title = "{g}-RSVP--eventid-{id}-creation-{t}".format(g=settings.GROUP_URLNAME, 
                                  id=event_id, t=str(datetime.now()).replace(" ", "_"))

    # Upload csv file to a Google Drive spreadsheet.
    oauthtcreds = get_oauth_creds()
    drive_service, f = upload_csv(oauthtcreds, rsvp.tempfile_name, title)
    if os.path.isfile(rsvp.tempfile_name):
        os.remove(rsvp.tempfile_name)

    if settings.COLLABORATORS:
        try:
            add_collaborators(drive_service, f["id"])
        except HTTPError as e:
            print("Error while adding collaborators:{e}".format(e=e))
            sys.exit()
            
    print("Created spreadsheet at {u}".format(u=f["alternateLink"]))
    
    
if __name__ == "__main__":
    main()

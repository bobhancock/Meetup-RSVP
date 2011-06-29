"""
Retrieve the "yes" rsvps for a specific Meetup id.
Get first and last name.
Write to a Google Docs spreadsheet.
"""
import os.path
import sys
import json
import operator
import tempfile
import time
import string

try:
    import settings
except ImportError:
    sys.stderr.write("You need to have settings.py in the same directory as this file.")
    sys.exit(1)

try:
    import atom.data
    import gdata.client
    import gdata.docs.client
    import gdata.docs.data
    import gdata.acl.data
except ImportError:
    sys.stderr.write("Failed to import the gdata client library: {ex}".format(ex=e))
    sys.exit(1)

try:    
    import httplib2    
except ImportError as e:
    sys.stderr.write("You need to install httplib2.  You can get it at http://code.google.com/p/httplib2/")
    sys.exit(1)
    
__author__ = "hancock.robert@gmail.com"
__version__ = "1.0"

class HTTPError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr("HTTPError: "+self.value)

    
class MeetupEvent():
    """ Meetup event class.
    
    args
        group_url_name     The group name from the Meetup URL>
    """
    def __init__(self, group_url_name):
        self.group_url_name = group_url_name
        
    def get_next_event(self):
        """ Get the next event, from today, in this group.

        return
            event id as a string
        """
        h = httplib2.Http(".cache")
        get_events_uri = "{u}?key={k}&sign=true&status=upcoming&group_urlname={i}".format(u=settings.MEETUP_EVENTS_URI,
                                                                                          k=settings.API_KEY, i=self.group_url_name)

        resp, content = h.request(get_events_uri, "GET")

        status = resp["status"]
        if status != "200":
            raise HTTPError('HTTP status code: {s}'.format(s=status))

        self.json_events = json.loads(content)
    
        event_url =  self.json_events["results"][0]["event_url"]
        components = event_url.split('/')
        return components[-2]
    
        
class RSVP():
    """ The Meetup RSVP class.
    
    args
        event_id   The unique id that Meetup uses to identify this event.
    
    """
    def __init__(self, event_id):
        self.event_id = event_id
        self.json_rsvps = {}
        self.names = []
        self.tempfile = ""
        # A translation table to filter out punctuation characters.
        self.trans = string.maketrans(string.punctuation, " "*len(string.punctuation))
        

    def download(self):
        """
        Get the "YES" RSVPs for this event.
        
        return
           a dictionary of the json contents
        """

        h = httplib2.Http(".cache")
        get_rsvps_uri = "{u}?key={k}&sign=true&event_id={i}".format(u=settings.MEETUP_RSVPS_URI, k=settings.API_KEY, i=self.event_id)

        resp, content = h.request(get_rsvps_uri, "GET")

        status = resp["status"]
        if status != "200":
            raise HTTPError('HTTP status code: {s}'.format(s=status))

        self.json_rsvps = json.loads(content)

        
    def get_names(self):
        """
        Extract first, middle, and last name from json and create a 
        list, the instance variable self.names, sorted by last name.
        
        Since these are likely to be printed on small badges we ignore middle initials
        and concentate last names which consist of more than one word or have titles 
        after them.
        
        Bilbo B. Baggins, Esq.
        Zeljko R. Miscosich Rentlanich
        
        becomes [fname] [lname]
        
        [Bilbo] [Baggins, Esq.]
        [Zeljko] [Miscosich Rentlanich]
        """
        results = self.json_rsvps["results"]
        
        for line in results:
            if line["response"] != 'yes':
                continue
            
            name = str(line["member"]["name"])
            name = name.translate(self.trans)
                
            name_components = name.strip().split()
            if not name_components:
                continue
            
            l = len(name_components)
            fname = lname = ""
            
            fname = name_components[0]
            fname = fname[0].upper()+fname[1:]
            if l == 2:
                lname = name_components[1]
            elif l > 2:
                lname = " ".join(name_components[2:])
            
            if lname:
                # The last name cannot be one letter or one letter plus a period
                lname = lname[0].upper()+lname[1:]
                if len(lname) ==1:
                    continue
                
                if len(lname) ==2:
                    if lname[1] == ".":
                        continue
                    

            self.names.append((fname,lname))
            
        self.names = sorted(self.names, key=operator.itemgetter(1))
    
        
    def write_to_file(self):
        """ Write the list of names to a CSV file. """
        f = tempfile.NamedTemporaryFile(delete=False, suffix="csv")
        self.tempfile = f.name
        
        for entry in self.names:
            fname, lname = entry
            f.write("{f},{l}\n".format(f=fname, l=lname))
        f.close()
        
        
class Spreadsheet():
    """ Upload CSV file to a Google Docs spreadsheet. 
    
    args
        title    The name of the spreadsheet in Google Docs.
        fil      The fully qualified path name of the source CSV file.
    """
    def __init__(self, title, fil):
        self.fil = fil
        self.title = title
        self.client = ""
        self.entry = ""
        
    def upload(self):
        self.client = gdata.docs.client.DocsClient(source=self.title)
        self.client.ClientLogin(settings.EMAIL, settings.PASSWORD, self.client.source)
        
        try:
            self.entry = self.client.Upload(self.fil, self.title, content_type='text/csv')        
        except Exception as e:
            print(e)
            return
        

    def share(self):
        """ Share your spreadsheet with other Google Doc users. """
        for email, role_value in settings.COLLABORATORS.iteritems():
            scope = gdata.acl.data.AclScope(value=email, type='user')
            role = gdata.acl.data.AclRole(value=role_value)
            acl_entry = gdata.docs.data.Acl(scope=scope, role=role)

            new_acl = self.client.Post(acl_entry, self.entry.GetAclFeedLink().href)
            #print "%s %s added as a %s" % (new_acl.scope.type, new_acl.scope.value, new_acl.role.value)
    
def main():
    m = MeetupEvent(settings.GROUP_URLNAME)
    event_id = m.get_next_event()
    
    rsvp = RSVP(event_id)
    rsvp.download()
    rsvp.get_names()
    rsvp.write_to_file()
    
    title = "{g}-{id}-{t}".format(g=settings.GROUP_URLNAME, 
                                  id=event_id, t=str(time.time()))
    s = Spreadsheet(title, rsvp.tempfile)
    s.upload()
    s.share()
    
    os.remove(rsvp.tempfile)
    
if __name__ == "__main__":
    main()
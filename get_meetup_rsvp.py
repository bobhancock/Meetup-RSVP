"""
Retrieve the "yes" rsvps for a specific Meetup id.
Get first and last name.
Filter out last names that are only one letter.
Write to a Google Docs spreadsheet.
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
except ImportError as e:
    sys.stderr.write("Failed to import the gdata client library: {ex}".format(ex=e))
    sys.exit(1)

try:    
    import httplib2    
except ImportError as e:
    sys.stderr.write("You need to install httplib2.  You can get it at http://code.google.com/p/httplib2/")
    sys.exit(1)
    
__author__ = "hancock.robert@gmail.com"
__version__ = "1.1"

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
    def __init__(self, event_id, filternames=True):
        self.event_id = event_id
        self.json_rsvps = {}
        self.names = []
        self.tempfile = None
        self.tempfile_name = os.path.join(os.getcwd(), str(int(time.time()))) + ".csv"
        self.filternames = filternames
        self.trans = list(string.punctuation) # for unicode cleaning
        
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
            if self.filternames:
                if len(name) < 4:
                    sys.stderr.write("Removed: '{f}' - invalid full name.\n".format(f=name))
                    continue
                
                name_components = name.strip().strip(',').split()
                if not name_components:
                    continue
                
                if len(name_components) < 2:
                    sys.stderr.write("Removed: '{f}' - invalid full name.\n".format(f=name))
                    continue
                                
                fname = lname = ""
                
                fname = name_components[0]
                if len(fname) == 1:
                    sys.stderr.write("Removed: '{f}' - first name cannot be one letter.\n".format(f=name))
                    continue
                
                fname = fname[0].upper()+fname[1:]
                #lname = " ".join(name_components[2:])
                lname = " ".join(name_components[1:])
                
                if lname:
                    # The last name cannot be one letter.
                    lname = lname[0].upper()+lname[1:]
                    if len(lname) == 1:
                        sys.stderr.write("Removed: '{l}' last name cannot be one letter.\n".format(l=name))
                        continue
                    
                self.names.append((fname,lname))
            else:
                self.names.append((name,""))
            
        if self.filternames:
            self.names = sorted(self.names, key=operator.itemgetter(1))
        else:
            self.names.sort()
    
    
    def write_to_file(self):
        """ Write the list of names to a CSV file. """

        self.tempfile = codecs.open(self.tempfile_name, mode="w", encoding="utf-8")
        
        for entry in self.names:
            fname, lname = entry

            self.tempfile.write(fname+","+lname+"\n")
        
        self.tempfile.close()
        
        
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
        
        # If this fails, let the exception bubble up
        self.entry = self.client.Upload(self.fil, self.title, content_type='text/csv')        
        

    def share(self):
        """ Share your spreadsheet with other Google Doc users. """
        for email, role_value in settings.COLLABORATORS.iteritems():
            scope = gdata.acl.data.AclScope(value=email, type='user')
            role = gdata.acl.data.AclRole(value=role_value)
            acl_entry = gdata.docs.data.Acl(scope=scope, role=role)

            new_acl = self.client.Post(acl_entry, self.entry.GetAclFeedLink().href)
            #print "%s %s added as a %s" % (new_acl.scope.type, new_acl.scope.value, new_acl.role.value)
    
    
def main():
    usage = "%prog [-inv]"
    parser = optparse.OptionParser(usage)
    parser.add_option("-i", "--event-id",
                      action="store", type="string", dest="eventid",
                      help="Use this event id and do not attempt to find the next one automatically on Meetup.")
    parser.add_option("-v", "--version",
                      action="store_true", dest="version",
                      help="Print version.")
    parser.add_option("-n", "--skip-name-filtering",
                      action="store_true", dest="skip_name_filtering",
                      help="Ignore name filtering rules.")
    
    [options, args] = parser.parse_args()
    if options.version:
        print("Version: {v}".format(v=__version__))
        return 0
    
    if not options.eventid:
        m = MeetupEvent(settings.GROUP_URLNAME)
        event_id = m.get_next_event()
    else:
        event_id = options.eventid
        
    filter_names = False if options.skip_name_filtering else True
    rsvp = RSVP(event_id, filternames=filter_names)
    try:
        rsvp.download()
    except Exception as e:
        sys.stderr.write("Cannot download event {i}: {e}".format(i=event_id, e=e))
        sys.exit(-1)
        
    rsvp.get_names()
    if not rsvp.names:
        sys.stderr.write("No names were found for event id {ei}.".format(ei=event_id))
        sys.exti()
        
    #print("{n} names".format(n=len(rsvp.names)))
    rsvp.write_to_file()
    
    title = "{g}-{id}-{t}".format(g=settings.GROUP_URLNAME, 
                                  id=event_id, t=str(time.time()))
    s = Spreadsheet(title, rsvp.tempfile_name)
    try:
        s.upload()       
    except Exception as e:
        sys.stderr.write("Could not create Google docs spreadsheet: {e}".format(e=e))
        sys.exit()

    try:
        s.share()
    except Exception as e:
        sys.stderr.write("Could not share spreadsheet: {e}".format(e=e))
        sys.exit()
    
    os.remove(rsvp.tempfile_name)
    
if __name__ == "__main__":
    main()
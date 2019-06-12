from bs4 import BeautifulSoup
import requests, re, json, time, os

SUCCESS = 1
FAILURE = 0

DEBUG = 0

# Structure for faculty details
class facultyObj(object):
     def __init__(self, name, designation, institute, gscholar_id):
        self.name        = name
        self.designation = designation
        self.institute   = institute
        self.gscholar_id = gscholar_id

# Function cleans user-centric Email-Id
def cleanMailID(data):
    data = re.sub(r'AT', "@", data)
    data = re.sub(r'DOT', ".", data)
    data = re.sub(r' ', "", data)
    return data

# Function crawls CSE Faculty Web Page
def crawlIITHydFacultyWebpage():
    IITHurl = 'http://cse.iith.ac.in/?q=People/Faculty'

    # Data Structure for maintaing Faculty details
    facultyData = {}

    raw_html = requests.get(IITHurl)
    soup = BeautifulSoup(raw_html.content)
    g_data = soup.find_all("tbody")

    for faculty in g_data[0]:
        # Fetch hyperlink
        link_item = faculty.find_all("a")
        webName = link_item[0].text
        name = webName.strip().title().encode('ascii', "ignore")

        # Consider only 'ascii' data
        data = faculty.text
        data = data.strip(' \t\n\r')
        data = data.encode('ascii', "ignore")
        webName = webName.encode('ascii', "ignore")
             
        # Retreive Designation
        my_regex = re.compile(r"^(%s)(?P<designation>[^\n]*)(Address:)([^\n]*)*" % webName)
        match = re.search(my_regex, data)

        facultyData[name] = match.group('designation').strip()

    return facultyData

# Crawl Google Scholar ID of the faculty
def crawlGScholarCode(name, institute):
    searchResult = 0
    name = name.strip().replace(".", "").title()
    nameString = name.split(" ")
    url = "https://scholar.google.co.in/citations?mauthors="
    for word in nameString:
        url = url + word + "+"
    url = url + "IIT+hyderabad&hl=en&view_op=search_authors"
    
    raw_html = requests.get(url)
    soup = BeautifulSoup(raw_html.content, "html.parser")
    g_data = soup.find_all("div", {"class":"gsc_1usr gs_scl"})

    # Iterate over all results
    for item in g_data:
        data = item.contents[1]

        verifiedEmailDiv = data.find_all("div", {"class":"gsc_1usr_eml"})
        if verifiedEmailDiv is None:
            continue

        # Extract Data
        my_regex = re.compile(r"user=(?P<gScholarId>.*)&hl=en")
        match = re.search(my_regex, data.a.get("href"))
        gScholarCode = match.group('gScholarId')

        verifiedEmail = data.find_all("div", {"class":"gsc_1usr_eml"})[0].text

        if institute == "IITH" and verifiedEmail == "Verified email at iith.ac.in":
            link = "https://scholar.google.co.in/citations?user=" + str(gScholarCode) + "&hl=en&cstart=0&pagesize=1000"
            return gScholarCode
        elif institute == "IITD" and verifiedEmail == "Verified email at cse.iitd.ac.in":
            link = "https://scholar.google.co.in/citations?user=" + str(gScholarCode) + "&hl=en&cstart=0&pagesize=1000"
            return gScholarCode
        elif institute == "IITM" and verifiedEmail == "Verified email at iitm.ac.in":
            link = "https://scholar.google.co.in/citations?user=" + str(gScholarCode) + "&hl=en&cstart=0&pagesize=1000"
            return gScholarCode
        elif institute == "IITK" and verifiedEmail == "Verified email at cse.iitk.ac.in":
            link = "https://scholar.google.co.in/citations?user=" + str(gScholarCode) + "&hl=en&cstart=0&pagesize=1000"
            return gScholarCode

# Crawl Google Scholar for Publication details
def crawlGScholar(url, name, parsedLinks):
    raw_html = requests.get(url)
    soup = BeautifulSoup(raw_html.content, "html.parser")
       
    toBeVisitedLinks = []

    # Retreive all publication links
    for a_set in soup.find_all('a'):
        try:
            next_link = str(a_set.get('href'))
        except:
            continue

        subURLToMatch = "/citations?view_op=view_citation&hl=en&oe=ASCII&user="
        if subURLToMatch in next_link:
            toBeVisitedLinks.append( "https://scholar.google.co.in" + next_link )
    
    # Parse each Publication Link
    for linkToParse in toBeVisitedLinks:

        if linkToParse in parsedLinks:
            continue

        raw_html = requests.get(linkToParse)
        soupDoc = BeautifulSoup(raw_html.content, "html.parser")

        publication = soupDoc.find(name='div', attrs={'id': 'gsc_title'})
        PublicationTitle = publication.get_text()

        PublicationLink = soupDoc.find(name='a', attrs={'class': 'gsc_title_link'})
        PublicationLink  = PublicationLink.get('href')

        field = soupDoc.findAll(name='div', attrs={'class': 'gsc_field'})
        value = soupDoc.findAll(name='div', attrs={'class': 'gsc_value'})

        date = ""
        for index in range(0,len(field)):
            if field[index].get_text() == "Publication date":
                dateValue = value[index].get_text()
                dateElems = dateValue.split("/")
                for dateElem in dateElems:
                    if len(dateElem) == 4:
                        date = dateElem
                        break

                if date == "":
                    print "Error: " + str(field[index].get_text()) + " : " + str(value[index].get_text())
                else:
                    print date + " : " + PublicationTitle
                    parsedLinks.append(linkToParse)
                    break
        time.sleep(20)

    return parsedLinks

# Read JSON File
def readJSONFile(fileName):
    # Sanity Check whether the file exists
    if os.path.exists(fileName):
        json_data = open(fileName).read()
        json_data = json.loads(json_data)
    else:
        json_data = {}
        json_data['parsedLinks'] = []

    return json_data

# Write JSON File
def writeJSONFile(fileName, data):
    with io.open(fileName, 'w', encoding='utf-8') as file:
        file.write(json.dumps(data, ensure_ascii=False))
    return

def crawlIITDelhiFacultyWebpage():
    IITDurl = "http://www.cse.iitd.ernet.in/index.php/2011-12-29-23-14-30/faculty"

    # Data Structure for maintaing Faculty details
    facultyData = {}

    raw_html = requests.get(IITDurl)
    soup = BeautifulSoup(raw_html.content, "html.parser")
    rawData = soup.find_all("tr")

    designationNotToCrawl = ['Visiting Faculty', 'Emeritus professors', 'Guest faculty']

    for data in rawData:

        # Do not crawl data for Visiting Faculty, Emeritus professors, Guest faculty
        for designation in designationNotToCrawl:
            if designation in data.text:
                break

        # Retreive Name and Designation
        if data.find("a") is not None:
            text = data.get_text().encode('utf8', 'ignore').replace(",'", '').strip()
            text = text.split("\n")
            if len(text) > 2 and ("Professor" in text[1] or "Head" in text[1]):
                facultyData[text[0]] = text[1]
                print str(text[0]) + " : " + str(text[1])

    return facultyData

def crawlIITMadrasFacultyWebpage():
    IITMurl = "http://www.cse.iitm.ac.in/listpeople.php?arg=MSQw"

    # Data Structure for maintaing Faculty details
    facultyData = {}

    raw_html = requests.get(IITMurl)
    soup = BeautifulSoup(raw_html.content, "html.parser")
    rawData = soup.find_all("td")

    for data in rawData:
        if data.find("a") is not None:
            text = data.get_text().encode('utf8', 'ignore').strip().replace('\n','').replace('\r','').replace('\t','')
            if "Professor" in text:
                # Retreive Name and Designation
                my_regex = re.compile(r"^(?P<name>[^\(]*)\((?P<designation>[^\)]*)([^\n]*)*")
                match = re.search(my_regex, text)
                name = match.group('name').strip()
                designation = match.group('designation').strip()
                facultyData[name] = designation

    return facultyData

def crawlIITKanpurFacultyWebpage():
    IITKurl = "https://www.cse.iitk.ac.in/pages/Faculty.html"

    # Data Structure for maintaing Faculty details
    facultyData = {}

    raw_html = requests.get(IITKurl)
    soup = BeautifulSoup(raw_html.content, "html.parser")
    rawData = soup.findAll(name='div', attrs={'class': 'facdescr'})

    for data in rawData:
        text = data.get_text()
        if "Professor" in text:
            # Retreive Name and Designation
            my_regex = re.compile(r"^(?P<name>[^\(]*)\(([^\)]*)\)(?P<designation>[^\n]*)(Tel:)([^\n]*)*")
            match = re.search(my_regex, text)
            if match is None:
                continue
            name = match.group('name').strip()
            designation = match.group('designation').strip()
            facultyData[name] = designation

    print len(facultyData)
    return facultyData

def crawlIIScFacultyWebpage():
    IIScurl = "http://www.csa.iisc.ernet.in/people/people-faculty.php"

    # Data Structure for maintaing Faculty details
    facultyData = {}

    raw_html = requests.get(IIScurl)
    soup = BeautifulSoup(raw_html.content, "html.parser")
    rawData = soup.findAll(name='td', attrs={'class': 'peoplecell'})
    possibleDesignation = ['Associate', 'Assistant']

    for data in rawData:
        text = data.get_text().replace('\n', ' ').strip()
        if "Professor" in text:
            # Retreive Name and Designation
            my_regex = re.compile(r"^(?P<name>[^\n]*)( Professor)([^\n]*)*")
            match = re.search(my_regex, text)
            # Sanity Check
            if match is None:
                continue
            name = match.group('name').strip()
            words = name.split()

            # Tweak to retreive the designation as
            # the data is entirely in text
            designation = [x for x in possibleDesignation if words[-1] == x]
            if designation == []:
                designation = "Professor"
            else:
                name = name.replace(designation[0], '').strip()
                designation = designation[0] + " Professor"
            facultyData[name] = designation

    print len(facultyData)
    return facultyData

def crawlIITRFacultyWebpage():
    IITRurl = "http://www.iitr.ac.in/departments/CSE/pages/People+Faculty_List.html"

    # Data Structure for maintaing Faculty details
    facultyData = []

    raw_html = requests.get(IITRurl)
    soup = BeautifulSoup(raw_html.content, "html.parser")
    rawData = soup.findAll(name='div', attrs={'class': 'detail'})
    possibleDesignation = ['Associate', 'Assistant']

    for data in rawData:
        text = data.get_text()
        text = text.replace("Website", '') # Special Case
        
        # Retreive Name and Designation
        my_regex = re.compile(r"^(?P<name>[^\n]*)( Professor)([^\n]*)*")
        match = re.search(my_regex, text)
        # Sanity Check
        if match is None:
            # Handle Head of Departments whose designation is not mentioned
            if 'Head' in text:
                my_regex_head = re.compile(r"^(?P<name>[^\n]*)(Head)([^\n]*)*")
                match_head = re.search(my_regex_head, text)
                if match_head is not None:
                    name = match_head.group('name').strip()
                    # Assuming all Head of Departments without mentioned designation to be Professors
                    facultyData.append(facultyObj(name, "Professor", "", ""))
            continue
        name = match.group('name').strip()
        words = name.split()

        # Tweak to retreive the designation as
        # the data is entirely in text
        designation = [x for x in possibleDesignation for word in words if x in word]
        if designation == []:
            designation = "Professor"
        else:
            name = name.replace(" (On Leave)",'') # Special Case
            name = name.replace(designation[0], '').strip()
            designation = designation[0] + " Professor"
        facultyData.append(facultyObj(name, designation, "", ""))

    for item in facultyData:
        name = item.name
        designation = item.designation
        print str(name) + " : " + str(designation)

    print len(facultyData)
    return facultyData

def crawlInstitueFacultyWebpage(instituteName):
    if instituteName == 'IITH':
        return crawlIITHydFacultyWebpage()
    elif instituteName == 'IITD':
        return crawlIITDelhiFacultyWebpage()
    elif instituteName == 'IITM':
        return crawlIITMadrasFacultyWebpage()
    elif instituteName == 'IITK':
        return crawlIITKanpurFacultyWebpage()
    elif instituteName == 'IISc':
        return crawlIIScFacultyWebpage()
    elif instituteName == 'IITR':
        return crawlIITRFacultyWebpage()


# Main-function
def main():

    facultyData = {}

    #institutes = ['IITH', 'IITD', 'IITM', 'IITK', 'IISc']
    institutes = ['IITR']

    for institute in institutes:
        facultyData[institute] = crawlInstitueFacultyWebpage(institute)

    
    '''
    # Crawl Faculty Information
    #facultyData = crawlFacultyWebpage()
    #facultyGScholarIDs = getFacultyGScholarID(dbHandle, facultyData)

    # Crawl Google Scholar for publications
    # Bheemarjuna Reddy Tamma FYHCD2kAAAAJ
    JSONFilePrefix = "JSON_VisitedLinks_"

    fileInstituteJSON = JSONFilePrefix + "IITH"

    # Read the institute's JSON File
    json_data = readJSONFile(fileInstituteJSON)

    gscholarID = "FYHCD2kAAAAJ"
    fName = "Bheemarjuna Reddy Tamma"
    nextSeed = "https://scholar.google.co.in/citations?user=" + gscholarID + "&hl=en&cstart=0&pagesize=1000";

    json_data['parsedLinks'] = crawlGScholar(nextSeed, fName, json_data['parsedLinks'])

    # Write to the institute's  JSON File
    writeJSONFile(fileInstituteJSON, json_data)
    '''

if __name__ == "__main__": main()
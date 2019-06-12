import time, logging, requests, re, io, os, json, MySQLdb, datetime, json
from bs4 import BeautifulSoup

LOG_FILENAME = 'pms_python_ext.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)

SUCCESS = 1
FAILURE = 0

DEBUG = 1

next_call = time.time()

# Structure for faculty details
class facultyObj(object):
     def __init__(self, name, designation, institute, gscholar_id):
        self.name        = name
        self.designation = designation
        self.institute   = institute
        self.gscholar_id = gscholar_id

# Function connects to the MySql DB
def connectDB():
    db = MySQLdb.connect(host="127.0.0.1", user="root", passwd="111", db="ext_pms")
    return db

# DB related functions
def DBAddUniqueEntry(curHandle, tableName, columnSet, valueSet, condition):
    sql_query = "INSERT INTO %s (%s) SELECT %s FROM DUAL WHERE NOT EXISTS (SELECT %s FROM %s WHERE %s);" % (tableName, columnSet, valueSet, columnSet, tableName, condition)
    if DEBUG:
        logging.debug(sql_query)
    try:
        curHandle.execute(sql_query)
    except MySQLdb.Error as exception:
        logging.error(sql_query)
        logging.error(exception)
        return FAILURE
    return SUCCESS


def DBUpdateEntry(curHandle, tableName, column, value, condition):
    sql_query = "UPDATE %s SET %s=%s WHERE %s;" % (tableName, column, value, condition)
    if DEBUG:
        logging.debug(sql_query)
    try:
        curHandle.execute(sql_query)
    except MySQLdb.Error as exception:
        logging.error(sql_query)
        logging.error(exception)
        return FAILURE
    return SUCCESS

def DBFetchMultipleEntries(curHandle, tableName, columnSet, matchSet):
    sql_query = "SELECT %s FROM %s WHERE %s;" % (columnSet, tableName, matchSet)
    if DEBUG:
        logging.debug(sql_query)
    try:
        curHandle.execute(sql_query)
        # fetch all of the rows from the query
        resBuffer = curHandle.fetchall()

    except MySQLdb.Error as exception:
        logging.error(sql_query)
        logging.error(exception)
        return FAILURE,""
    return SUCCESS,resBuffer

def DBRemoveEntry(curHandle, tableName, condition):
    if condition == "":
        sql_query = "DELETE FROM %s;" % tableName
    else:
        sql_query = "DELETE FROM %s WHERE %s;" % (tableName, condition)
    try:
        if DEBUG:
            logging.debug(sql_query)
        curHandle.execute(sql_query)
    except MySQLdb.Error as exception:
        logging.error(exception)
        return FAILURE
    return SUCCESS


# Function cleans user-centric Email-Id
def cleanMailID(data):
    data = re.sub(r'AT', "@", data)
    data = re.sub(r'DOT', ".", data)
    data = re.sub(r' ', "", data)
    return data

# Crawl Google Scholar ID of the faculty
def crawlGScholarCode(name, institute):
    searchResult = 0
    gScholarCode = ""
    fullInstituteName = ""
    toVerifyEmail = []
    name = name.strip().replace(".", "").title()
    nameString = name.split(" ")

    if institute == "IITH":
        toVerifyEmail.append("iith.ac.in")
        fullInstituteName = "IIT+hyderabad"

    elif institute == "IITD":
        toVerifyEmail.append("cse.iitd.ac.in")
        toVerifyEmail.append("iitd.ernet.in")
        fullInstituteName = "IIT+delhi"

    elif institute == "IITM":
        toVerifyEmail.append("iitm.ac.in")
        fullInstituteName = "IIT+madras"

    elif institute == "IITK":
        toVerifyEmail.append("cse.iitk.ac.in")
        fullInstituteName = "IIT+kanpur"

    elif institute == "IISc":
        toVerifyEmail.append("csa.iisc.ernet.in")
        fullInstituteName = "IISc+bangalore"

    else:
        logging.info("Programming Error. Incorrect Institute Name.")
        print "Programming Error. Incorrect Institute Name."
        return ""

    url = "https://scholar.google.co.in/citations?mauthors="
    for word in nameString:
        url = url + word + "+"
    url = url + fullInstituteName + "&hl=en&view_op=search_authors"
    
    raw_html = requests.get(url)
    soup = BeautifulSoup(raw_html.content, "html.parser")
    
    try:
        g_data = soup.find_all("div", {"class":"gsc_1usr gs_scl"})
    except:
        logging.debug("Faculty %s from %s does not contain Google Scholar account." % (name,institute))
        return gScholarCode

    # Iterate over all results
    for item in g_data:
        data = item.contents[1]

        # Extract Data
        my_regex = re.compile(r"user=(?P<gScholarId>.*)&hl=en")
        match = re.search(my_regex, data.a.get("href"))
        gScholarCode = match.group('gScholarId')

        # Handle if the Account is not verified by an email-Id
        try:
            gScholarVerifiedEmail = data.find_all("div", {"class":"gsc_1usr_eml"})[0].text
            gScholarVerifiedEmail = gScholarVerifiedEmail.replace("Verified email at ", "")
        except:
            logging.debug("Faculty %s from %s does not contain a verified email at Google Scholar." % (name,institute))
            return gScholarCode

        if gScholarVerifiedEmail in toVerifyEmail:
            link = "https://scholar.google.co.in/citations?user=" + str(gScholarCode) + "&hl=en&cstart=0&pagesize=1000"
            return gScholarCode
        else:
            gScholarCode = ""

    return gScholarCode

# Read JSON File
def readJSONFile(fileName):
    createDSFlag = 0
    # Sanity Check whether the file exists
    if os.path.exists(fileName):
        json_data = open(fileName).read()
        try:
            json_data = json.loads(json_data)
        except:
            createDSFlag = 1
    else:
        createDSFlag = 1

    if createDSFlag:
        json_data = []

    return json_data

# Write JSON File
def writeJSONFile(fileName, data):
    with io.open(fileName, 'w', encoding='utf-8') as file:
        tempJSONdump = json.dumps(data, ensure_ascii=False)

        if isinstance(tempJSONdump, str):
            tempJSONdump = tempJSONdump.decode("utf-8")

        file.write(tempJSONdump)
    return


def crawlIITHydFacultyWebpage():
    IITHurl = 'http://cse.iith.ac.in/?q=People/Faculty'

    # List of facultyObj - Data Structure for maintaing Faculty details
    facultyData = []

    raw_html = requests.get(IITHurl)
    soup = BeautifulSoup(raw_html.content, "html.parser")
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
        designation = match.group('designation').strip()

        facultyData.append(facultyObj(name, designation, "IITH", ""))

    return facultyData

def crawlIITDelhiFacultyWebpage():
    IITDurl = "http://www.cse.iitd.ernet.in/index.php/2011-12-29-23-14-30/faculty"

    # List of facultyObj - Data Structure for maintaing Faculty details
    facultyData = []

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
                facultyData.append(facultyObj(text[0], text[1], "IITD", ""))
                print str(text[0]) + " : " + str(text[1])

    return facultyData

def crawlIITMadrasFacultyWebpage():
    IITMurl = "http://www.cse.iitm.ac.in/listpeople.php?arg=MSQw"

    # List of facultyObj - Data Structure for maintaing Faculty details
    facultyData = []

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
                facultyData.append(facultyObj(name, designation, "IITM", ""))

    return facultyData

def crawlIITKanpurFacultyWebpage():
    IITKurl = "https://www.cse.iitk.ac.in/pages/Faculty.html"

    # List of facultyObj - Data Structure for maintaing Faculty details
    facultyData = []

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
            facultyData.append(facultyObj(name, designation, "IITK", ""))

    print len(facultyData)
    return facultyData

def crawlIIScFacultyWebpage():
    IIScurl = "http://www.csa.iisc.ernet.in/people/people-faculty.php"

    # List of facultyObj - Data Structure for maintaing Faculty details
    facultyData = []

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
                facultyData.append(facultyObj(name, designation, "IISc", ""))

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

# Function updates the Google Scholar Code of each faculty in the list into the DB
def updateFacultyWithGScholarID(dbHandle, facultyCrawledData, institute):
    curHandle = dbHandle.cursor()

    newFacultyData = []
    gScholarCode = ""

    for data in facultyCrawledData:
        name = data.name
        designation = data.designation

        # Check whether faculty information exists in the DB
        resCode,resultBuffer = DBFetchMultipleEntries(curHandle, "all_faculty_details", "*", "name = '%s'" % name)
        if resCode != SUCCESS:
            logging.error("Failed to retreive from all_faculty_details")

        if resultBuffer:
            # Check whether gScholarCode exists
            if resultBuffer[0][4] == "":
                continue # TODO Remove 
                gScholarCode = crawlGScholarCode(name, institute)

                if gScholarCode:
                    # Update DB for future reference
                    if SUCCESS != DBUpdateEntry(curHandle, 'all_faculty_details', "gscholar_id", "'%s'" % gScholarCode, "name = '%s'" % name):
                        logging.error("Failed to update gScholar code for %s" % name)
                    else:
                        if DEBUG:
                            logging.debug("Updated gScholarCode for faculty: %s" % name)
                else:
                    logging.debug("Failed to fetch Google Scholar ID for faculty: %s." % name)
            else:
                gScholarCode = resultBuffer[0][4]

        # Add a new entry about the faculty information into the DB
        else:
            
            #Firstly, get gScholar Code for the faculty
            gScholarCode = crawlGScholarCode(name, institute)

            # Add a new entry into the DB
            sqlValString = "'%s','%s','%s','%s'" % (institute, name, designation, gScholarCode)
            if SUCCESS != DBAddUniqueEntry(curHandle, 'all_faculty_details', "institute, name, designation, gscholar_id", sqlValString, "institute = '%s' and name = '%s'" % (institute,name)):
                logging.error("Failed to add entry for %s (%s)" % (name,institute) )
                continue
            else:
                if DEBUG:
                    logging.debug("Inserted data for %s(%s)" % (name,institute))
            print str(name) + " : " + str(gScholarCode)

        newFacultyData.append(facultyObj(name,designation,institute,gScholarCode))

        # Commit the changes
        dbHandle.commit()

    return newFacultyData


# Crawl Google Scholar for Publication details
def crawlGScholar(dbHandle, gScholarCode, name, institute, parsedLinks):
    curHandle = dbHandle.cursor()
    gScholarSeed = "https://scholar.google.co.in/citations?user=" + gScholarCode + "&hl=en&cstart=0&pagesize=1000";

    raw_html = requests.get(gScholarSeed)
    soup = BeautifulSoup(raw_html.content, "html.parser")
       
    toBeVisitedLinks = []
    fid = ""

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

        # Check whether publication is already crawled or not.
        if linkToParse in parsedLinks:
            continue

        print "Parsing: " + str(linkToParse)

        try:
            raw_html = requests.get(linkToParse)
            soupDoc = BeautifulSoup(raw_html.content, "html.parser")

            publication = soupDoc.find(name='div', attrs={'id': 'gsc_title'})
            PublicationTitle = publication.get_text()

            PublicationLink = soupDoc.find(name='a', attrs={'class': 'gsc_title_link'})
            PublicationLink  = PublicationLink.get('href')

            field = soupDoc.findAll(name='div', attrs={'class': 'gsc_field'})
            value = soupDoc.findAll(name='div', attrs={'class': 'gsc_value'})

        except:
            continue

        year = ""
        for index in range(0,len(field)):
            # Inspect only Publication Date
            if field[index].get_text() == "Publication date":
                dateValue = value[index].get_text()
                dateElems = dateValue.split("/")
                for dateElem in dateElems:
                    if len(dateElem) == 4:
                        year = dateElem
                        break

                # Date not found
                if year == "":
                    print "Error: " + str(field[index].get_text()) + " : " + str(value[index].get_text())
                    # Ignore all publications before the year 2013 TODO
                    #elif int(year) < 2014:                    
                    #    continue
                else:
                    # Fetch fid of the faculty DB, once                    
                    if fid == "" :
                        resCode,resultBuffer = DBFetchMultipleEntries(curHandle, "all_faculty_details", "fid", "name = '%s' and institute='%s'" % (name,institute))
                        if resCode == SUCCESS and len(resultBuffer):
                            fid = resultBuffer[0][0]
                        else:
                            if(DEBUG):
                                logging.debug("Failed to retreive information from all_faculty_details for %s(%s)." % (name,institute)) 

                                # No need to parse any more as all insert operations would fail
                                return parsedLinks
                    
                    count = 0
                    resCode,resultBuffer = DBFetchMultipleEntries(curHandle, "publication_count", "pub_count", "fid='%s' and year='%s'" % (fid,year))
                    if resCode == SUCCESS and len(resultBuffer):
                        # Update the entry for this year
                        count = int(resultBuffer[0][0]) + 1
                        if SUCCESS != DBUpdateEntry(curHandle, 'publication_count', "pub_count", "'%s'" % count, "fid='%s' and year='%s'" % (fid,year)):
                            logging.error("Failed to update publication_count for %s(%s) for the year %s" % (name, fid, year))
                            continue
                        else:
                            if DEBUG:
                                logging.debug("Updated publication_count for %s(%s) for the year %s" % (name, fid, year))

                    else:
                        # Add a new entry into the DB
                        count = 1 # TODO Remove
                        sqlValString = "'%s','%s','%s'" % (fid, year, 1)
                        if SUCCESS != DBAddUniqueEntry(curHandle, 'publication_count', "fid, year, pub_count", sqlValString, "fid='%s' and year='%s'" % (fid,year)):
                            logging.error("Failed to add entry for %s(%s) for the year %s" % (name, fid, year))
                            continue
                        else:
                            if DEBUG:
                                logging.debug("Inserted data for %s(%s) for the year %s" % (name, fid, year))

                    print str(count) + " | " + str(year) + " : " + str(name) + " - " + str(institute)
                    parsedLinks.append(linkToParse)
                    writeJSONFile("JSON_VisitedLinks_" + institute, parsedLinks) # TODO Remove
       
                    # Commit the changes
                    dbHandle.commit()
        
        print "Going to Sleep"
        time.sleep(60)
        print "Time for some Work!!!"

    return parsedLinks

def updatePublicationDetail(dbHandle, facultyData, institute):

    # Read the institute's JSON File
    json_data = readJSONFile("JSON_VisitedLinks_" + institute)

    # Check whether gScholarCode exists
    for data in facultyData:

        if data.gscholar_id == "" or data.gscholar_id == None:
            print "Skipped: " + str(data.name) + " : " + str(data.institute)
            continue

        # Fetch all publication links of the faculty
        json_data = crawlGScholar(dbHandle, data.gscholar_id, data.name, data.institute, json_data)

    # Write to the institute's  JSON File
    writeJSONFile("JSON_VisitedLinks_" + institute, json_data)

# Main-function
def main():

    dbHandle = connectDB()

    facultyData = []

    #institutes = ['IITH', 'IITD', 'IITM', 'IITK', 'IISc']
    #institutes = ['IITH', 'IITD', 'IITM', 'IITK']
    institutes = ['IITH']
    for institute in institutes:

        # Crawl Faculty Information
        facultyData = crawlInstitueFacultyWebpage(institute)

        # Add-Update Faculty Information
        # Return value contains the gScholarCode which reduces a DB query
        facultyData = updateFacultyWithGScholarID(dbHandle, facultyData, institute)
    
        # Crawl for each faculty's publications
        updatePublicationDetail(dbHandle, facultyData, institute)
    
     
if __name__ == "__main__": main()

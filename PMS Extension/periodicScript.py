import datetime, threading, time, logging
from bs4 import BeautifulSoup
import requests, re, io, os, json, MySQLdb
import smtplib, datetime

LOG_FILENAME = 'pms_python.log'
logging.basicConfig(filename=LOG_FILENAME,level=logging.INFO)
#logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG)
SUCCESS = 1
FAILURE = 0

DEBUG = 1
JSONFileName = "json_output.json"

next_call = time.time()

# Function connects to the MySql DB
def connectDB():
    db = MySQLdb.connect(host="127.0.0.1", user="root", passwd="111", db="pms")
    return db

# Function cleans user-centric Email-Id
def cleanMailID(data):
    data = re.sub(r'AT', "@", data)
    data = re.sub(r'DOT', ".", data)
    data = re.sub(r' ', "", data)
    return data

# Function crawls CSE Faculty Web Page
def crawlFacultyWebpage():
    url = 'http://cse.iith.ac.in/?q=People/Faculty'
    # Data Structure for maintaing Faculty details
    facultyData = []
	
    raw_html = requests.get(url)
    soup = BeautifulSoup(raw_html.content, "html.parser")

    g_data = soup.find_all("tbody")

    for faculty in g_data[0]:
        entity = dict()

        # Fetch hyperlink
        link_item = faculty.find_all("a")
        name = link_item[0].text
        entity['link'] = link_item[0].get("href").strip()
        entity['name'] = name.strip().title()
        img_item = faculty.find_all("img")
        entity['image_link'] = img_item[0].get("src")

        # Consider only 'ascii' data        
        data = faculty.text
        data = data.strip(' \t\n\r')
        data = data.encode('ascii', "ignore")
        name = name.encode('ascii', "ignore")
             
        # TODO : Minor issue with this Profile, contact CSE Web Team
        if name == "Saurabh Joshi":
            my_regex = re.compile(r"^(%s)(?P<designation>[^\n]*)(Address:)(?P<address>[^\n]*)(Phone:)(?P<phone>[^\n]*)(Email:)(?P<mail>[^\n]*)(Research Interests:)(?P<interests>[^\n]*)" % name)
        elif re.search(r"Phone", data):
            # TODO: Improve this code
            my_regex = re.compile(r"^(%s)(?P<designation>[^\n]*)(Address:)(?P<address>[^\n]*)(Email:)(?P<mail>[^\n]*)(Phone:)(?P<phone>[^\n]*)(Research Interests:)(?P<interests>[^\n]*)" % name)
        else:
            my_regex = re.compile(r"^(%s)(?P<designation>[^\n]*)(Address:)(?P<address>[^\n]*)(Email:)(?P<mail>[^\n]*)(Research Interests:)(?P<interests>[^\n]*)" % name)

        match = re.search(my_regex, data)

        entity['designation'] = match.group('designation').strip()
        entity['interests'] = match.group('interests').strip()
        # Minor change for addreslocalhost/phpmyadmin/index.phps
        entity['address'] = re.sub(r'HyderabadKandi', 'Hyderabad Kandi', match.group('address')).strip()
        # Entity: Phone may or may not exists
        if re.search(r"Phone", data):
            entity['phone'] = match.group('phone').strip()
        # Special handling for mails: AT, DOT
        entity['mail'] = cleanMailID(match.group('mail')).strip()

        facultyData.append(entity)

    return facultyData

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


# Inserts faculty related data into the DB
def insertFacultyData(dbHandle, facultyData, facultyGScholarIDs):
    curHandle = dbHandle.cursor()

    for entity in facultyData:
        # Check if entry already exists
        resCode,resultBuffer = DBFetchMultipleEntries(curHandle, "faculty_details", "name", "name = '%s'" % entity['name'])
        if resCode == SUCCESS and len(resultBuffer):
            continue
        else:
            logging.info("Information added for new faculty : %s." % str(entity['name']))

        if 'phone' not in entity:
            entity['phone'] = ""

        # Handle google scholar IDs
        if entity['name'] in facultyGScholarIDs:
            entity['gscholarID'] = facultyGScholarIDs[entity['name']]
        else:
            entity['gscholarID'] = ""

        # Add a new entry into the DB
        sqlValString = "'%s','%s','%s','%s','%s','%s','%s','%s'" % (entity['name'], entity['designation'], entity['mail'], entity['address'], entity['phone'], entity['link'], entity['gscholarID'], entity['image_link'])
        if SUCCESS != DBAddUniqueEntry(curHandle, 'faculty_details', "name, designation, mail_id, address, contact, site_link, gscholar_id, image_link", sqlValString, "name = '%s'" % entity['name']):
            logging.error("Failed to add entry for %s" % entity['name'])
            continue
        else:
            if DEBUG:
                logging.debug("Inserted data for %s" % entity['name'])

        # Retreive 'fid' of the faculty
        resCode,resultBuffer = DBFetchMultipleEntries(curHandle, "faculty_details", "fid", "name = '%s'" % entity['name'])
        if resCode != SUCCESS:
            logging.error("Failed to retreive from faculty_details")
            continue
        fid = resultBuffer[0][0]

        # Map Research Area to Miscellaneous
        resCode,resultBuffer = DBFetchMultipleEntries(curHandle, "research_area", "rid", "area_name = 'Miscellaneous'")
        if resCode != SUCCESS:
            logging.error("Failed to retreive from research_area")
            continue
        
        rid = resultBuffer[0][0]

        # Add a new entry 'map_faculty_rsch' into the DB
        sqlValString = "'%s','%s'" % (rid,fid)
        if SUCCESS != DBAddUniqueEntry(curHandle, 'map_faculty_rsch', "rid,fid", sqlValString, "rid = '%s' and fid = '%s'" % (rid,fid)):
            logging.error("Failed to add entry in map_faculty_rsch for name: %s" % entity['name'])
            continue
        else:
            sendMail(fid, entity['name'], entity['mail'])
            logging.info("Mail sent to Prof. %s about profile creation at %s." % (entity['name'], entity['mail']))
            if DEBUG:
                logging.debug("Inserted data in map_faculty_rsch")


        # Commit the changes
        dbHandle.commit()

# Crawl Google Scholar ID of the faculty
def crawlGScholarCode(name):
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
        if verifiedEmail == "Verified email at iith.ac.in":
            link = "https://scholar.google.co.in/citations?user=" + str(gScholarCode) + "&hl=en&cstart=0&pagesize=1000"
            return gScholarCode

# Retreives faculty gScholar ID either from DB or crawls google Scholar
def getFacultyGScholarID(dbHandle, facultyCrawledData):
    curHandle = dbHandle.cursor()
    facultyGScholarIDs = {}

    for entity in facultyCrawledData:
        name = entity['name']
        gScholarCode = ''

        # Fetch from DB
        resCode,resultBuffer = DBFetchMultipleEntries(curHandle, "faculty_details", "gscholar_id", "name = '%s'" % name)
        if resCode != SUCCESS:
            logging.error("Failed to retreive from faculty_details") 

        if resultBuffer:
            gScholarCode = resultBuffer[0][0]

        # Else Fetch from Google Scholar website
        if gScholarCode == "":
            gScholarCode = crawlGScholarCode(name)

            if gScholarCode:
                # Update DB for future reference
                facultyGScholarIDs[name] = gScholarCode
                if SUCCESS != DBUpdateEntry(curHandle, 'faculty_details', "gscholar_id", "'%s'" % gScholarCode, "name = '%s'" % name):
                    logging.error("Failed to update gScholar code for %s" % name)
                else:
                    if DEBUG:
                        logging.debug("Updated gScholarCode for faculty: %s" % name)
            else:
                logging.debug("Failed to fetch Google Scholar ID for faculty: %s." % name)
        else:
            facultyGScholarIDs[name] = gScholarCode

    return facultyGScholarIDs

# Retrieves faculty Data from DB
def getFacultyDataFromDB(dbHandle):
    curHandle = dbHandle.cursor()
    facultyDBData = []
    resCode,resultBuffer = DBFetchMultipleEntries(curHandle, "faculty_details", "fid,name", "1")
    if resCode != SUCCESS:
        logging.error("Failed to retrieve data from faculty_details table")
        return None
    
    for item in resultBuffer:
        facultyDBData.append(item)

    return facultyDBData

# Debugging: Tweak Faculty Data to delete from DB
def tweakfacultyCrawledData(facultyCrawledData):
    #delName = 'Kotaro Kataoka'
    delName = 'Sparsh Mittal'

    facultyCrawledDataNew = []

    for entity in facultyCrawledData:
        if delName != entity['name']:
            facultyCrawledDataNew.append(entity)

    facultyCrawledData = facultyCrawledDataNew
    # TODO: Remove
    #for entity in facultyCrawledData:
     #   logging.warning(entity['name'])

    return facultyCrawledData

# Function removes all links to the publications with this gScholarID
def removeEntriesFromJSONFile(gScholarCode):
    
    modData = {}
    modData['parsedLinks'] = []

    # Sanity Check whether the file exists
    if not os.path.exists(JSONFileName):
        return

    json_data = open(JSONFileName).read()
    json_data = json.loads(json_data)

    for data in json_data['parsedLinks']:
        if data.find(gScholarCode) == -1:
            modData['parsedLinks'].append(data)

    with io.open(JSONFileName, 'w', encoding='utf-8') as file:
        file.write(json.dumps(modData, ensure_ascii=False))

# Delete Faculty Data who has left from DB
def deleteFacultyData(dbHandle, facultyCrawledData, facultyDBData, facultyGScholarIDs):
    curHandle = dbHandle.cursor()
    for data in facultyDBData:
        fName = data[1]
        fid = data[0]

        flag = 0
        # Check if Faculty Name in DB with Crawled Data
        for entity in facultyCrawledData:
            if fName == entity['name']:
                flag = 1
                break

        # Remove all entries for this Faculty from DB
        if flag == 0:
            logging.debug("Observed faculty : " + str(fName) + " : " + str(fid) + " has left.")

            # 1a. Retreve all research Areas faculty was related to
            resCode,resultBuffer = DBFetchMultipleEntries(curHandle, "map_faculty_rsch", "rid", "fid='%s'" % fid)
            if resCode != SUCCESS:
                logging.error("Failed to retrieve data from map_faculty_rsch table")
                continue

            for result in resultBuffer:
                rid = result[0]
                # 1b. Check, if unique research area by faculty
                resAnotherCode,resultAnotherBuffer = DBFetchMultipleEntries(curHandle, "map_faculty_rsch", "fid", "rid='%s'" % rid)
                if resAnotherCode != SUCCESS:
                    logging.error("Failed to retrieve data from map_faculty_rsch table for rid %s" % rid)
                    continue
                else:
                    if len(resultAnotherBuffer) == 1:
                        # (i). Remove, unique Research Area by the faculty
                        if SUCCESS == DBRemoveEntry(curHandle, "research_area", "rid = '%s' and area_name != 'Miscellaneous'" % rid):
                            logging.debug("Removed DB entry from research_area")
                        else:
                            logging.error("Failed to remove entry from research_area for rid %s " % rid)

            # 1c. Remove faculty-research_area mapping
            if SUCCESS == DBRemoveEntry(curHandle, "map_faculty_rsch", "fid = '%s'" % fid):
                logging.debug("Removed DB entrie(s) from map_faculty_rsch")
            else:
                logging.error("Failed to remove entry from map_faculty_rsch for fid %s " % fid)

            # 2. Remove all publication specific of the faculty
            # 2a. Retrieve all publication-id(s) by the faculty
            resCode,resultBuffer = DBFetchMultipleEntries(curHandle, "map_faculty_publ", "pid", "fid='%s'" % fid)
            if resCode != SUCCESS:
                logging.error("Failed to retrieve data from map_faculty_publ table")
                return None

            # 2b. From 'publications'
            for result in resultBuffer:
                pid = result[0]
                # Check if publication is by multiple faculties
                resAnotherCode,resultAnotherBuffer = DBFetchMultipleEntries(curHandle, "map_faculty_publ", "fid", "pid='%s'" % pid)
                if resAnotherCode != SUCCESS:
                    logging.error("Failed to retrieve data from map_faculty_publ table")
                    continue
                else:
                    if len(resultAnotherBuffer) == 1:
                        # (i) Remove, unique Publications by the faculty
                        if SUCCESS == DBRemoveEntry(curHandle, "publications", "pid = '%s'" % pid):
                            logging.debug("Removed DB entry from publications")
                        else:
                            logging.error("Failed to remove entry from publications for pid %s " % pid)

                        # (ii) Remove all co-authors
                        if SUCCESS == DBRemoveEntry(curHandle, "authors", "pid = '%s'" % pid):
                            logging.debug("Removed DB entry from authors")
                        else:
                            logging.error("Failed to remove entry from authors for pid %s " % pid)

                        # (iii) Remove from map_publ_rsch
                        if SUCCESS == DBRemoveEntry(curHandle, "map_publ_rsch", "pid = '%s'" % pid):
                            logging.debug("Removed DB entry from map_publ_rsch")
                        else:
                            logging.error("Failed to remove entry from map_publ_rsch for pid %s " % pid)

            # 2c. From 'map_faculty_publ'
            if SUCCESS == DBRemoveEntry(curHandle, "map_faculty_publ", "fid = '%s'" % fid):
                logging.debug("Removed DB entrie(s) from map_faculty_publ")
            else:
                logging.error("Failed to remove entry from map_faculty_publ for fid %s " % fid)

            # 3. Remove parsedLinks from JSON file
            removeEntriesFromJSONFile(facultyGScholarIDs[fName])
            
            # 4. Remove from 'faculty_details'
            if SUCCESS == DBRemoveEntry(curHandle, "faculty_details", "name = '%s'" % fName):
                logging.debug("Removed DB entry from faculty_details")
            else:
                logging.error("Failed to remove entry from faculty_details for name %s " % fName)

            logging.info("Successfully deleted all entries for %s from DB. GoodBye!!!" % fName)
           
            # Commit the changes
            dbHandle.commit()


# Performs work after a period of time
def doWork():
    dbHandle = connectDB()

    # Crawl Faculty Information
    facultyCrawledData = crawlFacultyWebpage()
    facultyGScholarIDs = getFacultyGScholarID(dbHandle, facultyCrawledData)
    facultyDBData = getFacultyDataFromDB(dbHandle)

    # Insert New Faculty information into DB
    insertFacultyData(dbHandle, facultyCrawledData, facultyGScholarIDs)

    # Debugging
    #facultyCrawledData = tweakfacultyCrawledData(facultyCrawledData)

    # Delete Left Faculty information from DB
    deleteFacultyData(dbHandle, facultyCrawledData, facultyDBData, facultyGScholarIDs)

    # Cleanup
    dbHandle.close()


# Sends mail to Faculty about his Profile Creation
def sendMail(fid, facultyName, facultyMailId):
    FROMADDR = "researchcseiith@gmail.com"
    LOGIN    = FROMADDR
    PASSWORD = "research@iith"
    TOADDRS  = ["researchcseiith@gmail.com"]
    #TOADDRS  = [facultyMailId]
    #TOADDRS  = ["cs16mtech11009@iith.ac.in"]
    SUBJECT  = "Publication Management System(PMS) Profile Created"

    date = datetime.datetime.now().strftime( "%d/%m/%Y %H:%M" )

    msg = ("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % (FROMADDR, ", ".join(TOADDRS), SUBJECT) )
    msg += "*** This is an automatically generated email, please do not reply ***\n\n"
    msg += "Hello Prof. %s \nWelcome to the Department of Computer Science and Engineering, IIT Hyderabad.\n" % (facultyName)
    msg += "This is to inform you that your Publication Management System(PMS) profile is created.\n"
    msg += "Follow the link below to view your profile.\n\n"
    msg += "http://cse.iith.ac.in/pms/profile_new.php?id=%s\n\n" % (fid)
    msg += "Date: %s\n\n Regards\nPMS Module, Dept. of CSE, IIT Hyderabad\n" % ( date )
    msg += "To be sent Mail Id: %s" % (facultyMailId)

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(LOGIN, PASSWORD)
    server.sendmail(FROMADDR, TOADDRS, msg)
    server.quit()

# Main-function
def main():
    global next_call
    logging.info("Periodic Timer started at: " + str(datetime.datetime.now()))

    # Performs work for this iteration
    doWork()
    
    logging.info("Periodic Timer finished at: " + str(datetime.datetime.now()))

    #next_call = next_call + 100
    #threading.Timer( next_call - time.time(), main ).start()

if __name__ == "__main__": main()

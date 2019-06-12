from bs4 import BeautifulSoup
import requests, re, json, MySQLdb

SUCCESS = 1
FAILURE = 0

DEBUG = 0

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
        print sql_query
    try:
        curHandle.execute(sql_query)
    except MySQLdb.Error as exception:
        print sql_query
        print exception
        return FAILURE
    return SUCCESS

def DBFetchMultipleEntries(curHandle, tableName, columnSet, matchSet):
    sql_query = "SELECT %s FROM %s WHERE %s;" % (columnSet, tableName, matchSet)
    if DEBUG:
        print sql_query
    try:
        curHandle.execute(sql_query)
        # fetch all of the rows from the query
        resBuffer = curHandle.fetchall()
    except MySQLdb.Error as exception:
        print sql_query
        print exception
        return FAILURE,""
    return SUCCESS,resBuffer

def DBRemoveEntry(curHandle, tableName, condition):
    if condition == "":
        sql_query = "DELETE FROM %s;" % tableName
    else:
        sql_query = "DELETE FROM %s WHERE %s;" % (tableName, condition)
    try:
        if DEBUG:
            print sql_query
        curHandle.execute(sql_query)
    except MySQLdb.Error as exception:
        print exception
        return FAILURE

# Debugging: Functions cleans the table
def cleanDB(dbHandle):
    curHandle = dbHandle.cursor()
    DBRemoveEntry(curHandle, 'faculty_details', "")
    DBRemoveEntry(curHandle, 'research_area', "")
    DBRemoveEntry(curHandle, 'map_faculty_rsch', "")
    dbHandle.commit()
    open("/home/michail/eclipse/pms/json_output.json", 'w').close()

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
            print "Failed to retreive from faculty_details"

        if resultBuffer:
            gScholarCode = resultBuffer[0][0]

        # Else Fetch from Google Scholar website
        if gScholarCode == "":
            gScholarCode = crawlGScholarCode(name)

            if gScholarCode:
                # Update DB for future reference
                facultyGScholarIDs[name] = gScholarCode
            else:
                print "Failed to fetch Google Scholar ID for faculty: %s." % name
        else:
            facultyGScholarIDs[name] = gScholarCode

    return facultyGScholarIDs

# Inserts faculty related data into the DB
def insertFacultyData(dbHandle, facultyData, facultyGScholarIDs):
    curHandle = dbHandle.cursor()

    for entity in facultyData:
        if 'phone' not in entity:
            entity['phone'] = ""

        # Handle google scholar IDs
        if entity['name'] in facultyGScholarIDs:
            entity['gscholarID'] = facultyGScholarIDs[entity['name']]
        else:
            entity['gscholarID'] = ""

        sqlValString = "'%s','%s','%s','%s','%s','%s','%s','%s'" % (entity['name'], entity['designation'], entity['mail'], entity['address'], entity['phone'], entity['link'], entity['gscholarID'], entity['image_link'])
        if SUCCESS != DBAddUniqueEntry(curHandle, 'faculty_details', "name, designation, mail_id, address, contact, site_link, gscholar_id, image_link", sqlValString, "name = '%s'" % entity['name']):
            print "Failed to add entry for %s" % entity['name']
        else:
            if DEBUG:
                print "Inserted data for %s" % entity['name']

    # Commit the changes
    dbHandle.commit()

# Inserts data for all the Research Areas
def insertResearchAreaData(dbHandle):
    curHandle = dbHandle.cursor()
    rschAreas = []
    rschAreas.append("Algorithms and Theory");
    rschAreas.append("Compilers");
    rschAreas.append("Networking");
    rschAreas.append("Machine Learning and Computer Vision");
    rschAreas.append("Distributed Systems and Parallel Computing");
    rschAreas.append("Data Mining");
    rschAreas.append("Computer Architecture");
    rschAreas.append("Miscellaneous");

    for item in rschAreas:
        if SUCCESS != DBAddUniqueEntry(curHandle, 'research_area', "area_name", "'%s'"%item, "area_name = '%s'"%item):
            print "Failed to add entry for Research Area: %s" % item
        else:
            if DEBUG:
                print "Inserted data for Research Area: %s" % item

    # Commit the changes
    dbHandle.commit()


# Function updates DB with Faculty and their Research Areas
def mapFacultyWithRschArea(dbHandle):
    curHandle = dbHandle.cursor()

    frMap = {}
    frMap['Algorithms and Theory'] = ["M. V. Panduranga Rao", "N. R. Aravind", "Saurabh Joshi", "Sobhan Babu", "Subrahmanyam Kalyanasundaram"];
    frMap['Compilers'] = ["Ramakrishna Upadrasta"];
    frMap['Networking'] = ["Bheemarjuna Reddy Tamma", "Antony Franklin", "Kotaro Kataoka"]
    frMap['Machine Learning and Computer Vision'] = ["Srijith P. K.", "C. Krishna Mohan", "Vineeth N Balasubramanian"]
    frMap['Data Mining'] = ["Maunendra Sankar Desarkar", "Manish Singh", "Manohar Kaul", "Sobhan Babu"]
    frMap['Distributed Systems and Parallel Computing'] = ["Sathya Peri"]
    frMap['Computer Architecture'] = ["Sparsh Mittal"]
    
    resCode,resultBuffer = DBFetchMultipleEntries(curHandle, "research_area", "rid, area_name", "1")
    if resCode != SUCCESS:
        print "Failed to retreive details from 'research_area' table";
        return

    for item in resultBuffer:
        rid = item[0]
        area_name = item[1]

        if area_name in frMap:
            for fName in frMap[area_name]:
                resCode,resBuff = DBFetchMultipleEntries(curHandle, "faculty_details", "fid", "name='%s'" % fName)

                if resCode != SUCCESS:
                    print "Failed to retreive information for %s" % fName
                    continue
                else:
                    fid = resBuff[0][0]
                    if SUCCESS != DBAddUniqueEntry(curHandle, 'map_faculty_rsch', "rid, fid", "%s,%s" % (rid,fid), "rid=%s and fid=%s" % (rid,fid)):
                        print "Failed to add entry for %s,%s in 'map_faculty_rsch'" % (rid,fid)

    # Commit the changes
    dbHandle.commit()

# Main-function
def main():

    dbHandle = connectDB()

    # If required, clean the DB.
    cleanDB(dbHandle)

    # Crawl Faculty Information
    facultyData = crawlFacultyWebpage()
    facultyGScholarIDs = getFacultyGScholarID(dbHandle, facultyData)

    # Insert Faculty information into DB
    insertFacultyData(dbHandle, facultyData, facultyGScholarIDs)

    # Insert Research Areas information into DB
    insertResearchAreaData(dbHandle)

    # Map - Faculty : Research Area
    mapFacultyWithRschArea(dbHandle)

    # Cleanup
    dbHandle.close()

    print "Completed"

if __name__ == "__main__": main()

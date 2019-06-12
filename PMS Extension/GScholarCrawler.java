import java.io.File;
import java.io.FileInputStream;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.PrintWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.Properties;
import java.util.StringTokenizer;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.nodes.Node;
import org.jsoup.select.Elements;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;

public class GScholarCrawler {

    static boolean SUCCESS = true;
    static boolean FAILURE = false;

    static boolean DEBUG_SQL_QUERIES = false;
    static boolean DEBUG = false;

    static ResultSet resultBuffer;

    public static String capitalize(String value) {

        char[] array = value.toCharArray();
        // Uppercase first letter.
        array[0] = Character.toUpperCase(array[0]);

        // Uppercase all letters that follow a whitespace character.
        for (int i = 1; i < array.length; i++) {
            if (Character.isWhitespace(array[i - 1])) {
                array[i] = Character.toUpperCase(array[i]);
            }
        }

        // Result.
        return new String(array);
    }

    public static boolean DBAddUniqueEntry(Statement smt, String tableName, String columnSet, String valueSet, String condition)
    {
        try {
            String sqlString = "INSERT INTO " + tableName + "(" + columnSet + ")" + " SELECT " + valueSet + " FROM DUAL WHERE NOT EXISTS ( SELECT " +
                columnSet + " FROM " + tableName + " WHERE " + condition + ");";
            if(DEBUG_SQL_QUERIES)
                System.out.println(sqlString);

            smt.execute(sqlString);
        } catch (SQLException e) {
            System.out.println(e);
            return FAILURE;
        }
        return SUCCESS;
    }

    public static boolean DBFetchMultipleEntries(Statement smt, String tableName, String columnSet, String matchSet)
    {
        try {
            String sqlString = "SELECT " + columnSet + " FROM " + tableName + " WHERE " + matchSet + ";";
            if(DEBUG_SQL_QUERIES)
                System.out.println(sqlString);

            resultBuffer = smt.executeQuery(sqlString);
        } catch (SQLException e) {
            System.out.println(e);
            return FAILURE;
        }
        return SUCCESS;
    }

    public static boolean DBRemoveEntry(Statement smt, String tableName, String condition)
    {
        try {
            String sqlString = (condition != null && condition.isEmpty()) ? 
                "DELETE FROM " + tableName + " WHERE " + condition + ";" :
                "DELETE FROM " + tableName + ";";

            if(DEBUG_SQL_QUERIES)
                System.out.println(sqlString);
            smt.execute(sqlString);
        } catch (SQLException e) {
            System.out.println(e);
            return FAILURE;
        }
        return SUCCESS;
    }

    public static JSONObject readJSONFile(String filePath) {
        JSONParser parser = new JSONParser();
        JSONObject jsonObject = null;

        try {
            if (new File(filePath).exists())
            {
                Object obj = parser.parse(new FileReader(filePath));
                jsonObject = (JSONObject) obj;
            }
            else
            {
                //Create the file and return it as object
                System.out.println("File " + filePath + " does not exists.");                
                jsonObject = new JSONObject();
            }
        } catch (IOException | ParseException e) {
            e.printStackTrace();
        }

        System.out.println("JSON read contents: " + jsonObject);
        return jsonObject;
    }

    public static void writeJSONFile(JSONObject jsonObject, String filePath) {

        try (FileWriter file = new FileWriter(filePath)) {

            file.write(jsonObject.toJSONString());
            file.flush();

        } catch (IOException e) {
            e.printStackTrace();
        }

        System.out.println("JSON write contents: " + jsonObject);
    }

    public static boolean checkNameSimilarity(String name, String fName) {

        // Matching can be done if both names have atleast 3 words
        String[] fNameSplit = fName.split("\\s+");
        String[] nameSplit  = name.split("\\s+");

        int matchCriteria = 0;
        String nameWord, fNameWord;

        for(int i = 0; i < fNameSplit.length; i++)
        {
            for(int j = 0; j < nameSplit.length; j++)
            {
                nameWord = nameSplit[j];
                fNameWord = fNameSplit[i];
                if( nameWord.length() > 1 && fNameWord.length() > 1 && nameWord.equals(fNameWord))
                    matchCriteria = matchCriteria + 1;
            }
        }
        return (matchCriteria >= 2) ? true : false;
    }

    public static String matchFacultyNames(String name, String[] facultyNames) {

        String matchedName = "", fName = "";
        for(int i=0; i<facultyNames.length && facultyNames[i] != null; i++)
        {
            fName = facultyNames[i];
            if(checkNameSimilarity(name, fName) == true)
            {
                matchedName = fName;
                break;
            }        
        }
        return matchedName;
    }

    public static void doCrawling(String[] currentfacultyNames, String seed, int facultyID)
    {
        Document seedDoc;

        String PublicationTitle=null;
        String Publisher=null;
        String PublisherType=null;
        String Abstract = null;
        String PublicationGScholarID = null;
        String PublicationLink = null;
        String Bibtex = null;
        String Authors = null;
        String Pages=null;
        String Owner = null;
        String TotalCitations = null;
        String PublicationDate = null;
        String sqlValString;

        HashSet<String> linksToBeVisited = new HashSet<String>();

        try {
            // Connect to mySQL database 
            Class.forName("com.mysql.jdbc.Driver").newInstance();
            Connection con = DriverManager.getConnection("jdbc:mysql://localhost:3306/", "root", "111");
            Statement smt = con.createStatement();
            smt.execute("USE pms");

            String JSONfilePath = "json_output.json";

            // Read existing JSON File
            JSONObject obj = readJSONFile(JSONfilePath);
            JSONArray parsedLinks = null;

            if(obj == null)
            {
                obj = new JSONObject();
                parsedLinks = new JSONArray();
            }
            else
            {
                parsedLinks = (JSONArray)obj.get("parsedLinks");
                if(parsedLinks == null)
                    parsedLinks = new JSONArray();
            }


            // getting links from seed URL 
            seedDoc = Jsoup.connect(seed).userAgent("Mozilla/5.0 (Windows NT 6.1; WOW64; rv:5.0) Gecko/20100101 Firefox/5.0").timeout(30000).get();

            //getting Author/owner name
            Owner = seedDoc.getElementById("gsc_prf_in").text();

            // Extracting all internal links and storing them into a hashSet
            Elements links = seedDoc.select("a");

            // Adding publication links to HashSet 
            for (Element link : links) {
                if(link.absUrl("href").startsWith("https://scholar.google.co.in/citations?view_op=view_citation"))
                    linksToBeVisited.add(link.absUrl("href"));
            }

            // printing number of internal links from each seed URL
            if(DEBUG)
                System.out.println("Number of internal links in " + seed + " : " + linksToBeVisited.size());

            // Iterator to access each internal link from HashSet
            Iterator<String> linkIterator = linksToBeVisited.iterator();
            Iterator<String> contentIterator = linksToBeVisited.iterator();
            linkIterator.next();
            contentIterator.next();

            int counter = 30;
            while (linkIterator.hasNext() && counter > 0) {
                try {

                    String nextLinkToParse = linkIterator.next().toString();                    
                    if (parsedLinks.contains(nextLinkToParse))
                    {
                        if(DEBUG)
                            System.out.println("Link skipped: " + nextLinkToParse); 
                        continue;
                    }

                    // Get Publication Details using publication URL
                    Document internalLinkDoc = Jsoup.connect(nextLinkToParse) .userAgent("Mozilla/5.0 (Windows NT 6.1; WOW64; rv:5.0) Gecko/20100101 Firefox/5.0") .timeout(20000).validateTLSCertificates(false) .get();

                    Elements TitleDetails = internalLinkDoc.getElementsByClass("gsc_title_link");
                    PublicationLink = TitleDetails.attr("href");
                    PublicationTitle = TitleDetails.text();

                    // Extracting fields and its values 
                    Elements Details = internalLinkDoc.select("div.gs_scl");
                    Elements FieldTags= Details.select("div.gsc_field");
                    Elements ValueTags= Details.select("div.gsc_value");
                    Iterator FieldIterator = FieldTags.iterator();
                    Iterator ValueIterator = ValueTags.iterator();

                    while(FieldIterator.hasNext()){

                        org.jsoup.nodes.Element Field=(org.jsoup.nodes.Element) FieldIterator.next();

                        switch (Field.text()) {
                            case "Authors":  
                                org.jsoup.nodes.Element AuthorsValue=(org.jsoup.nodes.Element) ValueIterator.next();    
                                Authors = AuthorsValue.text();
                                break;
                            case "Publication date":
                                org.jsoup.nodes.Element DateValue=(org.jsoup.nodes.Element) ValueIterator.next();    
                                PublicationDate =  DateValue.text().replaceAll("\'", "\\\\'");
                                if(PublicationDate.length() > 20)
                                    System.out.println("Improper Publication Date: " + PublicationDate);
                                break;
                            case "Conference":
                            case "Journal":
                                org.jsoup.nodes.Element PblTypeValue=(org.jsoup.nodes.Element) ValueIterator.next();    
                                PublisherType =  PblTypeValue.text().replaceAll("\'", "\\\\'");
                                break;
                            case "Pages":  
                                org.jsoup.nodes.Element PagesValue=(org.jsoup.nodes.Element) ValueIterator.next();    
                                Pages=  PagesValue.text();
                                break;
                            case "Publisher":  
                                org.jsoup.nodes.Element PublisherValue=(org.jsoup.nodes.Element) ValueIterator.next();
                                Publisher =  PublisherValue.text().replaceAll("\'", "\\\\'");
                                break;
                            case "Description":  
                                org.jsoup.nodes.Element AbstractValue=(org.jsoup.nodes.Element) ValueIterator.next();    
                                Abstract=  AbstractValue.text().replaceAll("\'", "\\\\'");
                                break;
                            case "Total citations":  
                                org.jsoup.nodes.Element CitationValue=(org.jsoup.nodes.Element) ValueIterator.next();    
                                TotalCitations = CitationValue.text();
                                break;
                            default:
                                break;
                        }
                    }

                    PublicationGScholarID = internalLinkDoc.getElementById("gsc_ab_btns").getElementsByAttributeValue("name", "s").attr("value");

                    // Extracting BibTex contents
                    Elements Scripts = internalLinkDoc.getElementsByTag("script");
                    int i=0;
                    for (Element script : Scripts) {
                        i++;
                        if(i==3){
                            String str = script.data().substring(262, 474);    
                            String str1=str.replaceAll("x3d", "=");
                            String str2= str1.replaceAll("x26", "&");
                            String BibTexURL=str2.replace('\\', ' ').replaceAll("\\s+","");
                            Document BibTexDoc = Jsoup.connect(BibTexURL).userAgent("Mozilla/5.0 (Windows NT 6.1; WOW64; rv:5.0) Gecko/20100101 Firefox/5.0") .timeout(20000).validateTLSCertificates(false) .get();
                            Bibtex = BibTexDoc.text().replaceAll("\'", "\\\\'");
                        }
                    }

                    // 1a. Insert publication_details into DB
                    sqlValString = String.format("'%s','%s','%s','%s','%s','%s','%s','%s'", 
                            PublicationTitle, Publisher, PublisherType, PublicationDate,
                            Abstract, PublicationGScholarID, PublicationLink, Bibtex);

                    if( SUCCESS != DBAddUniqueEntry(smt,"publications", "title, publisher, publisher_type, publication_date,"
                                + "abstract, gscholar_id, link, bibtex", sqlValString, "title = '" + PublicationTitle + "'"))
                    {
                        System.out.println("Failed to add publication entry for " + PublicationTitle);
                        continue;
                    }
                    System.out.println("Added: " + PublicationTitle);

                    // 1b. Extract auto-incremented 'pid' of the above publication
                    if( SUCCESS != DBFetchMultipleEntries(smt, "publications", "pid", "title = '" + PublicationTitle + "'"))
                    {
                        System.out.println("Failed to fetch 'pid' for title: " + PublicationTitle + " from 'publications' table");
                        continue;
                    }
                    resultBuffer.next();
                    int publicationID = resultBuffer.getInt("pid");;
                    // 2. Insert co-authors - Tweak : Add 'fid' to authors who are also faculty
                    String[] authorsArray = Authors.split(",");
                    int authorOrder = 1;
                    String matchedName = "", authorName = "";
                    for (String author : authorsArray) 
                    {
                        // Check whether author is one of our faculties
                        matchedName = matchFacultyNames(author, currentfacultyNames);
                        if(matchedName != "")
                        {
                            if( SUCCESS != DBFetchMultipleEntries(smt, "faculty_details", "fid", "name = '" + matchedName.trim() + "'"))
                            {
                                System.out.println("Failed to fetch 'fid' for faculty: " + matchedName.trim() + " from 'faculty_details' table");
                                continue;
                            }
                            resultBuffer.next();
                            authorName = String.format("%02d", resultBuffer.getInt("fid")) + matchedName.trim();
                        }
                        else
                            authorName = author;
                        // Insert author into 'authors' table in DB
                        sqlValString = String.format("'%s','%s','%s'", publicationID, authorName, authorOrder);
                        if( SUCCESS != DBAddUniqueEntry(smt, "authors", "pid,name,author_order", sqlValString,
                                    "pid = '" + publicationID + "' and name = '" + authorName + "'"))
                            System.out.println("Failed to add publication entry for " + PublicationTitle);
                        authorOrder++;
                    }

                    // 3. Map faculty with its publication
                    sqlValString = String.format("'%s','%s'", publicationID, facultyID);
                    if( SUCCESS != DBAddUniqueEntry(smt, "map_faculty_publ", "pid,fid", sqlValString, "pid = '" + publicationID + "' and fid = '" + facultyID + "'"))
                        System.out.println("Failed to map publication entry" + publicationID + " with faculty" + facultyID);

                    // 4. Map publication with its research area
                    HashSet<Integer> researchAreasID = new HashSet<Integer>();
                    if( SUCCESS != DBFetchMultipleEntries(smt, "map_faculty_rsch", "rid", "fid = '" + facultyID + "'"))
                    {
                        System.out.println("Failed to fetch 'rid' for faculty: " + facultyID + " from 'faculty_details' table");
                        continue;
                    }                

                    // Retrieve result
                    while(resultBuffer.next())
                        researchAreasID.add(resultBuffer.getInt("rid"));

                    Iterator<Integer> IdIterator = researchAreasID.iterator();
                    while (IdIterator.hasNext())
                    {
                        int rid = IdIterator.next();
                        sqlValString = String.format("'%s','%s'", rid, publicationID);
                        if( SUCCESS != DBAddUniqueEntry(smt, "map_publ_rsch", "rid,pid", sqlValString, "rid = '" + rid + "' and pid = '" + publicationID + "'"))
                            System.out.println("Failed to map publication entry" + publicationID + " with researchArea");
                    }

                    // 5. All DB entries successful. Skip link for future traversals
                    if (!parsedLinks.contains(nextLinkToParse))
                        parsedLinks.add(nextLinkToParse);

                    System.out.println("I am going to sleep. Use this time.");
                    TimeUnit.SECONDS.sleep(30);

                } catch (IOException | NoSuchElementException | NullPointerException | InterruptedException | SQLException e) {
                    System.out.println(e);
                    linkIterator.next();
                }
            }

            // Close connections
            smt.close();
            con.close();

            // Dump JSON File
            if(DEBUG)
                System.out.println("Dump: " + parsedLinks);
            obj.put("parsedLinks", parsedLinks);
            writeJSONFile(obj, JSONfilePath);
        } catch (IOException | NoSuchElementException | InstantiationException | IllegalAccessException | ClassNotFoundException | SQLException e) {
            System.out.println(e);
        }

    }

    public static void main(String[] args) throws IOException, InterruptedException {

        try {
            // Connect to mySQL database 
            Class.forName("com.mysql.jdbc.Driver").newInstance();
            Connection conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/", "root", "111");
            Statement smt = conn.createStatement();
            smt.execute("USE pms");

            String sqlQuery  =     "SELECT fid, name, gscholar_id FROM faculty_details;";

            int i = 0;
            ResultSet iterator = smt.executeQuery(sqlQuery);
            String[] currentfacultyNames = new String[50];
            while(iterator.next())
            {
                String facultyName = capitalize(iterator.getString("name"));
                currentfacultyNames[i++] = facultyName;
            }

            // Extract data of faculty for Crawling Google Scholar 
            ResultSet result = smt.executeQuery(sqlQuery);

            // Iterate through the result
            boolean flag = true;
            while (flag && result.next()) 
            {
                int fid = result.getInt("fid");
                String facultyName = capitalize(result.getString("name"));
                String gscholarID = result.getString("gscholar_id");

                if(flag && (gscholarID == null || !gscholarID.isEmpty()))
                {
                    String nextSeed = "https://scholar.google.co.in/citations?user=" + gscholarID + "&hl=en&cstart=0&pagesize=1000";

                    System.out.println("Crawling started for Faculty: " + facultyName); 

                    // Performs crawling w.r.t. faculty
                    doCrawling(currentfacultyNames, nextSeed, fid);

                    TimeUnit.SECONDS.sleep(30);

                    //flag = false;
                }
            }
        } catch (NoSuchElementException | InstantiationException | IllegalAccessException | ClassNotFoundException | SQLException e) {
            System.out.println(e);
        }
    }
}

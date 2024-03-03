package edu.cmu.cc.minisite;
import com.google.gson.JsonObject;
import com.mongodb.MongoClient;
import com.mongodb.MongoClientURI;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.Objects;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.bson.Document;
import com.google.gson.JsonArray;
import com.mongodb.client.FindIterable;
import com.mongodb.client.model.Projections;
import com.mongodb.client.model.Sorts;
import com.google.gson.JsonElement;
import com.mongodb.client.model.Filters;
import java.util.List;
import java.util.ArrayList;
import com.mongodb.client.FindIterable;
import com.mongodb.client.model.Filters;
import org.bson.Document;
import org.bson.conversions.Bson;
import com.google.gson.JsonParser;
import static com.mongodb.client.model.Projections.excludeId;
import static com.mongodb.client.model.Projections.fields;
import com.google.gson.Gson;

 
/**
 * Task 3:
 * Implement your logic to return all the comments authored by this user.
 *
 * You should sort the comments by ups in descending order (from the largest to the smallest one).
 * If there is a tie in the ups, sort the comments in descending order by their timestamp.
 */
public class HomepageServlet extends HttpServlet {

    /**
     * The endpoint of the database.
     *
     * To avoid hardcoding credentials, use environment variables to include
     * the credentials.
     *
     * e.g., before running "mvn clean package exec:java" to start the server
     * run the following commands to set the environment variables.
     * export MONGO_HOST=...
     */
    private static final String MONGO_HOST = System.getenv("MONGO_HOST");
    /**
     * MongoDB server URL.
     */
    private static final String URL = "mongodb://" + MONGO_HOST + ":27017";
    /**
     * Database name.
     */
    private static final String DB_NAME = "reddit_db";
    /**
     * Collection name.
     */
    private static final String COLLECTION_NAME = "posts";
    /**
     * MongoDB connection.
     */
    private static MongoCollection<Document> collection;

    /**
     * Initialize the connection.
     */
    public HomepageServlet() {
        Objects.requireNonNull(MONGO_HOST);
        MongoClientURI connectionString = new MongoClientURI(URL);
        MongoClient mongoClient = new MongoClient(connectionString);
        MongoDatabase database = mongoClient.getDatabase(DB_NAME);
        collection = database.getCollection(COLLECTION_NAME);
    }

    /**
     * Implement this method.
     *
     * @param request  the request object that is passed to the servlet
     * @param response the response object that the servlet
     *                 uses to return the headers to the client
     * @throws IOException      if an input or output error occurs
     * @throws ServletException if the request for the HEAD
     *                          could not be handled
     */
    @Override
    protected void doGet(final HttpServletRequest request,
                         final HttpServletResponse response) throws ServletException, IOException {

        JsonObject result = new JsonObject();
        String id = request.getParameter("id");
        // TODO: To be implemented
        result.add("comments", getComments(id));
        response.setContentType("text/html; charset=UTF-8");
        response.setCharacterEncoding("UTF-8");
        PrintWriter writer = response.getWriter();
        writer.write(result.toString());
        writer.close();

    }

    
public JsonArray getComments(String id) {
    JsonArray commentsArray = new JsonArray();

    FindIterable<Document> comments = collection.find(new Document("uid", id))
            .projection(Projections.excludeId())
            .sort(Sorts.descending("ups", "timestamp"));

     for (Document comment : comments) {

            JsonObject commentObject = new JsonObject();
            
            commentObject.addProperty("uid", comment.getString("uid"));
            commentObject.addProperty("downs", comment.getInteger("downs"));
            commentObject.addProperty("parent_id", comment.getString("parent_id"));
            commentObject.addProperty("ups", comment.getInteger("ups"));
            commentObject.addProperty("subreddit", comment.getString("subreddit"));
            commentObject.addProperty("timestamp", comment.getString("timestamp"));
            commentObject.addProperty("content", comment.getString("content"));
            commentObject.addProperty("cid", comment.getString("cid"));
            commentsArray.add(commentObject);
        }

        return commentsArray;     
}


public JsonArray getTopComments(JsonArray followees) {
    
    JsonArray commentsArray = new JsonArray();
    List<Bson> followeesList = new ArrayList<>();

    for (JsonElement element : followees) {
    if (element.isJsonObject()) {
        JsonObject jsonObject = element.getAsJsonObject();
        String name = jsonObject.get("name").getAsString();
        followeesList.add(Filters.eq("uid", name));
    }
}
    Bson combinedFilter;  
   if (!followeesList.isEmpty()) {
    combinedFilter = Filters.or(followeesList);
    FindIterable<Document> comments = collection.find(combinedFilter).sort(Filters.and(Sorts.descending("ups"), Sorts.descending("timestamp"))).limit(30);
       for (Document comment : comments) {

        JsonObject commentObject = new JsonObject();
        commentObject.addProperty("uid", comment.getString("uid"));
        commentObject.addProperty("downs", comment.getInteger("downs"));
        commentObject.addProperty("parent_id", comment.getString("parent_id"));
        commentObject.addProperty("ups", comment.getInteger("ups"));
        commentObject.addProperty("subreddit", comment.getString("subreddit"));
        commentObject.addProperty("content", comment.getString("content"));
        commentObject.addProperty("cid", comment.getString("cid"));
        commentObject.addProperty("timestamp", comment.getString("timestamp"));
        
        if(comment.getString("parent_id") != null)
        {
            Document parent = collection.find(Filters.eq("cid",comment.getString("parent_id"))).projection(fields(excludeId())).first();
            
            if(parent != null)
            {
            JsonObject parentjson = new JsonParser().parse(parent.toJson()).getAsJsonObject();
            commentObject.add("parent", parentjson);
            }
        if (parent != null && parent.getString("parent_id") != null) {
            Document grandparent = collection.find(Filters.eq("cid", parent.getString("parent_id"))).projection(fields(excludeId())).first();
            if(grandparent !=null)
            {

            JsonObject grandparentjson = new JsonParser().parse(grandparent.toJson()).getAsJsonObject();

            commentObject.add("grand_parent", grandparentjson);

            }

}

        }
        
        commentsArray.add(commentObject);
    }
   }
    
    return commentsArray; 
}
}
            









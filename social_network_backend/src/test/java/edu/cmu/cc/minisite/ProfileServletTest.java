package edu.cmu.cc.minisite;

import com.google.gson.JsonObject;
import org.junit.Assert;
import org.junit.Before;
import org.junit.Test;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.MockitoAnnotations;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

// Class for Mockito tests
public class ProfileServletTest {

    // Mock Connection and PreparedStatement
    @Mock private Connection mockConnection;
    @Mock private PreparedStatement preparedMockStatement;

    // Mock ResultSet
    private final ResultSet mockResultSet = Mockito.mock(ResultSet.class);

    // This method sets up the Mockito framework
    @Before
    public void setUp() throws SQLException {

        // Initialize this class's mocks
        MockitoAnnotations.initMocks(this);

        // Handle prepareStatements and the executeQuery methods
        when(mockConnection.prepareStatement(anyString())).thenReturn(preparedMockStatement);
        when(mockConnection.prepareStatement(anyString()).executeQuery()).thenReturn(mockResultSet);
    }

    // Test for correct credentials
    @Test
    public void checkJsonResultForCorrectLogin() throws Exception {
        // Mock behaviour of the ResultSet
        when(mockResultSet.getString("username")).thenReturn("xylo");
        when(mockResultSet.getString("pwd")).thenReturn("password");
        when(mockResultSet.getString("profile_photo_url")).thenReturn("https://mockurl.com/mock.jpg");

        // One record only
        when(mockResultSet.isBeforeFirst()).thenReturn(true).thenReturn(false);
        when(mockResultSet.next()).thenReturn(true).thenReturn(false);

        // Spy on a ProfileServlet instance
        ProfileServlet mockProfileServlet = Mockito.spy(new ProfileServlet(mockConnection) );

        // Construct the expected JsonObject
        JsonObject correctResult = new JsonObject();
        correctResult.addProperty("name", "xylo");
        correctResult.addProperty("profile", "https://mockurl.com/mock.jpg");

        // Execute the method to test
        JsonObject value = mockProfileServlet.validateLoginAndReturnResult("xylo", "password");

        // Check for null object, and print a meaningful test case result
        if (value == null || value.get("name") == null || value.get("profile") == null) {
            value = new JsonObject();
            value.addProperty("name", "null");
            value.addProperty("profile", "null");
        }

        // Check if we get the expected result
        Assert.assertEquals(correctResult, value);

        // Verify the use of prepareStatement, and executeQuery
        Mockito.verify(mockConnection, Mockito.atLeastOnce()).prepareStatement(anyString());
        Mockito.verify(preparedMockStatement, Mockito.atLeastOnce()).executeQuery();
    }

    // Test for incorrect credentials
    @Test
    public void checkJsonResultForIncorrectLogin() throws Exception {
        // Mock behaviour of the ResultSet
        when(mockResultSet.getString(anyString())).thenThrow(new SQLException());

        // No records
        when(mockResultSet.isBeforeFirst()).thenReturn(false);
        when(mockResultSet.next()).thenReturn(false);

        // Spy on a ProfileServlet instance
        ProfileServlet mockProfileServlet = Mockito.spy(new ProfileServlet(mockConnection));

        // Execute the method to test
        JsonObject value = mockProfileServlet.validateLoginAndReturnResult("xylo", "wrong password");

        // Check for null object, and print a meaningful test case result
        if (value == null || value.get("name") == null || value.get("profile") == null) {
            value = new JsonObject();
            value.addProperty("name", "null");
            value.addProperty("profile", "null");
        }

        // Check if we get the expected result
        Assert.assertEquals("Unauthorized", value.get("name").getAsString());

        // Verify the use of prepareStatement, and executeQuery
        Mockito.verify(mockConnection, Mockito.atLeastOnce()).prepareStatement(anyString());
        Mockito.verify(preparedMockStatement, Mockito.atLeastOnce()).executeQuery();
    }
}

package org.acme.mcp;

import io.quarkus.test.junit.QuarkusTest;
import jakarta.inject.Inject;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

@QuarkusTest
class MonkeySpeciesMcpServerTest {

    @Inject
    MonkeySpeciesMcpServer mcpServer;

    @Test
    void testListMonkeySpecies() {
        String result = mcpServer.listMonkeySpecies();
        
        assertNotNull(result);
        assertFalse(result.contains("Error"));
        assertTrue(result.contains("Available Monkey Species"));
        assertTrue(result.contains("Proboscis Monkey"));
    }

    @Test
    void testGetMonkeySpeciesDetailsWithValidName() {
        String result = mcpServer.getMonkeySpeciesDetails("Proboscis Monkey");
        
        assertNotNull(result);
        assertFalse(result.contains("Error"));
        assertTrue(result.contains("Species Name: Proboscis Monkey"));
        assertTrue(result.contains("Location: Borneo"));
    }

    @Test
    void testGetMonkeySpeciesDetailsWithInvalidName() {
        String result = mcpServer.getMonkeySpeciesDetails("Nonexistent Monkey");
        
        assertNotNull(result);
        assertTrue(result.contains("not found"));
        assertTrue(result.contains("Available species include"));
    }

    @Test
    void testGetMonkeySpeciesDetailsWithEmptyName() {
        String result = mcpServer.getMonkeySpeciesDetails("");
        
        assertNotNull(result);
        assertTrue(result.contains("Error: Species name cannot be empty"));
    }

    @Test
    void testGetMonkeySpeciesDetailsWithNullName() {
        String result = mcpServer.getMonkeySpeciesDetails(null);
        
        assertNotNull(result);
        assertTrue(result.contains("Error: Species name cannot be empty"));
    }

    @Test
    void testGetRandomMonkeySpecies() {
        String result = mcpServer.getRandomMonkeySpecies();
        
        assertNotNull(result);
        assertFalse(result.contains("Error"));
        assertTrue(result.contains("Here's a random monkey species"));
        assertTrue(result.contains("Species Name:"));
    }

    @Test
    void testGetMonkeySpeciesStats() {
        String result = mcpServer.getMonkeySpeciesStats();
        
        assertNotNull(result);
        assertFalse(result.contains("Error"));
        assertTrue(result.contains("Monkey Species Database Statistics"));
        assertTrue(result.contains("Total Species:"));
        assertTrue(result.contains("Total Population:"));
    }
}

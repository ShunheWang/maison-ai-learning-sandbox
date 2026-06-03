package org.acme.mcp;

import org.acme.model.MonkeySpecies;
import org.acme.service.MonkeySpeciesService;
import io.quarkiverse.mcp.server.Tool;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import java.util.List;
import java.util.Optional;
import java.util.stream.Collectors;

@ApplicationScoped
public class MonkeySpeciesMcpServer {
    
    @Inject
    MonkeySpeciesService monkeySpeciesService;
    
    @Tool(name = "list_monkey_species", description = "List all available monkey species with their basic information")
    public String listMonkeySpecies() {
        try {
            List<MonkeySpecies> allSpecies = monkeySpeciesService.getAllSpecies();
            
            if (allSpecies.isEmpty()) {
                return "No monkey species found in the database.";
            }
            
            StringBuilder result = new StringBuilder();
            result.append("Available Monkey Species (").append(allSpecies.size()).append(" total):\n\n");
            
            for (MonkeySpecies species : allSpecies) {
                String fictionalFlag = species.isFictional() ? " *FAKE*" : "";
                result.append("• ").append(species.speciesName()).append(fictionalFlag)
                      .append(" (").append(species.location()).append(")")
                      .append(" - Population: ").append(species.population())
                      .append("\n");
            }
            
            return result.toString();
        } catch (Exception e) {
            return "Error retrieving monkey species list: " + e.getMessage();
        }
    }
    
    @Tool(name = "get_monkey_species_details", description = "Get detailed information for a specific monkey species by name")
    public String getMonkeySpeciesDetails(String speciesName) {
        if (speciesName == null || speciesName.trim().isEmpty()) {
            return "Error: Species name cannot be empty. Please provide a valid species name.";
        }
        
        try {
            Optional<MonkeySpecies> species = monkeySpeciesService.getSpeciesDetails(speciesName);
            
            if (species.isPresent()) {
                return species.get().toFormattedString();
            } else {
                // Provide helpful suggestions
                List<String> availableSpecies = monkeySpeciesService.getAllSpeciesNames();
                String suggestions = availableSpecies.stream()
                        .limit(5)
                        .collect(Collectors.joining(", "));
                
                return String.format("Monkey species '%s' not found. Available species include: %s", 
                                   speciesName, suggestions);
            }
        } catch (Exception e) {
            return "Error retrieving species details: " + e.getMessage();
        }
    }
    
    @Tool(name = "get_random_monkey_species", description = "Get a random monkey species with full details")
    public String getRandomMonkeySpecies() {
        try {
            Optional<MonkeySpecies> randomSpecies = monkeySpeciesService.getRandomSpecies();
            
            if (randomSpecies.isPresent()) {
                return "Here's a random monkey species:\n\n" + randomSpecies.get().toFormattedString();
            } else {
                return "No monkey species available in the database.";
            }
        } catch (Exception e) {
            return "Error retrieving random monkey species: " + e.getMessage();
        }
    } 
    
    @Tool(name = "get_monkey_species_stats", description = "Get statistics about the monkey species database")
    public String getMonkeySpeciesStats() {
        try {
            int totalSpecies = monkeySpeciesService.getSpeciesCount();
            List<MonkeySpecies> allSpecies = monkeySpeciesService.getAllSpecies();
            
            if (allSpecies.isEmpty()) {
                return "Database is empty - no monkey species available.";
            }
            
            // Calculate total population
            long totalPopulation = allSpecies.stream()
                    .mapToLong(species -> species.population() != null ? species.population() : 0)
                    .sum();
            
            // Find most accessed species
            Optional<MonkeySpecies> mostAccessed = allSpecies.stream()
                    .max((a, b) -> Integer.compare(a.accessed(), b.accessed()));
            
            // Count unique locations
            long uniqueLocations = allSpecies.stream()
                    .map(MonkeySpecies::location)
                    .distinct()
                    .count();
            
            StringBuilder stats = new StringBuilder();
            stats.append("Monkey Species Database Statistics:\n\n");
            stats.append("• Total Species: ").append(totalSpecies).append("\n");
            stats.append("• Total Population: ").append(String.format("%,d", totalPopulation)).append("\n");
            stats.append("• Unique Locations: ").append(uniqueLocations).append("\n");
            
            if (mostAccessed.isPresent()) {
                MonkeySpecies popular = mostAccessed.get();
                stats.append("• Most Accessed: ").append(popular.speciesName())
                     .append(" (").append(popular.accessed()).append(" times)\n");
            }
            
            return stats.toString();
        } catch (Exception e) {
            return "Error retrieving database statistics: " + e.getMessage();
        }
    }
}

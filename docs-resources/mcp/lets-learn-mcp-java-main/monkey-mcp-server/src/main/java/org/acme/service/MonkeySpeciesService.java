package org.acme.service;

import org.acme.model.MonkeySpecies;
import org.acme.repository.MonkeySpeciesRepository;
import jakarta.enterprise.context.ApplicationScoped;
import jakarta.inject.Inject;
import java.util.List;
import java.util.Optional;

/**
 * Service layer for monkey species operations.
 * Provides business logic and acts as an intermediary between MCP tools and repository.
 */
@ApplicationScoped
public class MonkeySpeciesService {
    
    @Inject
    MonkeySpeciesRepository repository;
    
    /**
     * Retrieves all monkey species.
     * 
     * @return A list of all monkey species with their basic information
     */
    public List<MonkeySpecies> getAllSpecies() {
        return repository.findAll();
    }
    
    /**
     * Gets detailed information for a specific monkey species.
     * This method increments the access counter for the species.
     * 
     * @param speciesName The name of the species to retrieve
     * @return An Optional containing the species details if found, empty otherwise
     */
    public Optional<MonkeySpecies> getSpeciesDetails(String speciesName) {
        if (speciesName == null || speciesName.trim().isEmpty()) {
            return Optional.empty();
        }
        
        // Normalize the species name for case-insensitive lookup
        String normalizedName = speciesName.trim();
        
        // Find the species with case-insensitive matching
        return repository.findAll().stream()
                .filter(species -> species.speciesName().equalsIgnoreCase(normalizedName))
                .findFirst()
                .map(species -> repository.findByNameAndIncrementAccess(species.speciesName()).orElse(species));
    }
    
    /**
     * Gets a random monkey species.
     * This method increments the access counter for the selected species.
     * 
     * @return An Optional containing a random species if any exist, empty otherwise
     */
    public Optional<MonkeySpecies> getRandomSpecies() {
        return repository.findRandomAndIncrementAccess();
    }
    
    /**
     * Checks if a species exists in the database.
     * 
     * @param speciesName The name of the species to check
     * @return true if the species exists, false otherwise
     */
    public boolean speciesExists(String speciesName) {
        if (speciesName == null || speciesName.trim().isEmpty()) {
            return false;
        }
        
        return repository.findAll().stream()
                .anyMatch(species -> species.speciesName().equalsIgnoreCase(speciesName.trim()));
    }
    
    /**
     * Gets the total number of species in the database.
     * 
     * @return The count of species
     */
    public int getSpeciesCount() {
        return repository.getSpeciesCount();
    }
    
    /**
     * Gets a list of all species names for easy reference.
     * 
     * @return A list of species names
     */
    public List<String> getAllSpeciesNames() {
        return repository.findAll().stream()
                .map(MonkeySpecies::speciesName)
                .sorted()
                .toList();
    }
}

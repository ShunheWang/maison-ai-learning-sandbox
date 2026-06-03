package org.acme.repository;

import org.acme.model.MonkeySpecies;
import jakarta.enterprise.context.ApplicationScoped;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Repository for managing monkey species data.
 * Handles thread-safe operations for immutable MonkeySpecies records.
 */
@ApplicationScoped
public class MonkeySpeciesRepository {
    
    private final Map<String, MonkeySpecies> speciesDatabase = new ConcurrentHashMap<>();
    private final Random random = new Random();
    
    /**
     * Initializes the repository with sample monkey species data.
     */
    public MonkeySpeciesRepository() {
        initializeData();
    }
    
    /**
     * Retrieves all monkey species.
     * 
     * @return A list of all monkey species
     */
    public List<MonkeySpecies> findAll() {
        return new ArrayList<>(speciesDatabase.values());
    }
    
    /**
     * Finds a monkey species by name and increments its access count.
     * 
     * @param speciesName The name of the species to find
     * @return An Optional containing the species if found, empty otherwise
     */
    public Optional<MonkeySpecies> findByNameAndIncrementAccess(String speciesName) {
        if (speciesName == null || speciesName.trim().isEmpty()) {
            return Optional.empty();
        }
        
        return Optional.ofNullable(speciesDatabase.get(speciesName.toLowerCase()))
                .map(species -> {
                    MonkeySpecies updatedSpecies = species.withIncrementedAccess();
                    speciesDatabase.put(speciesName.toLowerCase(), updatedSpecies);
                    return updatedSpecies;
                });
    }
    
    /**
     * Gets a random monkey species and increments its access count.
     * 
     * @return An Optional containing a random species if any exist, empty otherwise
     */
    public Optional<MonkeySpecies> findRandomAndIncrementAccess() {
        List<String> speciesNames = new ArrayList<>(speciesDatabase.keySet());
        if (speciesNames.isEmpty()) {
            return Optional.empty();
        }
        
        String randomSpeciesName = speciesNames.get(random.nextInt(speciesNames.size()));
        return findByNameAndIncrementAccess(randomSpeciesName);
    }
    
    /**
     * Checks if a species exists by name.
     * 
     * @param speciesName The name of the species to check
     * @return true if the species exists, false otherwise
     */
    public boolean existsByName(String speciesName) {
        if (speciesName == null || speciesName.trim().isEmpty()) {
            return false;
        }
        return speciesDatabase.containsKey(speciesName.toLowerCase());
    }
    
    /**
     * Gets the total count of species in the database.
     * 
     * @return The number of species
     */
    public int getSpeciesCount() {
        return speciesDatabase.size();
    }
    
    /**
     * Initializes the repository with sample monkey species data.
     */
    private void initializeData() {
        List<MonkeySpecies> initialSpecies = Arrays.asList(
            // Real monkey species
            new MonkeySpecies(
                "Proboscis Monkey",
                "Borneo",
                "The proboscis monkey or long-nosed monkey, known as the bekantan in Malay, is a reddish-brown arboreal Old World monkey that is endemic to the south-east Asian island of Borneo.",
                15000,
                0.961883,
                114.55485,
                0,
                false
            ),
            new MonkeySpecies(
                "Golden Snub-nosed Monkey",
                "China",
                "The golden snub-nosed monkey is an Old World monkey in the subfamily Colobinae. It is endemic to a small area in temperate, mountainous forests of central and southwestern China.",
                8000,
                33.5000,
                104.0000,
                0,
                false
            ),
            new MonkeySpecies(
                "Howler Monkey",
                "Central and South America",
                "Howler monkeys are among the largest of the New World monkeys. They are famous for their loud howls, which can travel more than one mile through dense rain forest.",
                50000,
                10.0000,
                -84.0000,
                0,
                false
            ),
            new MonkeySpecies(
                "Japanese Macaque",
                "Japan",
                "The Japanese macaque, also known as the snow monkey, is a terrestrial Old World monkey species that is native to Japan. They are notable for their ability to survive in very cold climates.",
                114000,
                36.2048,
                138.2529,
                0,
                false
            ),
            new MonkeySpecies(
                "Mandrill",
                "Equatorial Africa",
                "The mandrill is a primate of the Old World monkey family. It is one of the most colorful mammals in the world, with red and blue skin on their face and posterior.",
                800000,
                0.4162,
                9.4673,
                0,
                false
            ),
            new MonkeySpecies(
                "Spider Monkey",
                "Central and South America",
                "Spider monkeys are New World monkeys belonging to the genus Ateles. They are characterized by their long, slender limbs and prehensile tails.",
                25000,
                -2.1833,
                -79.8833,
                0,
                false
            ),
            // Fictional monkey species (NOT real!)
            new MonkeySpecies(
                "Crystal Fur Monkey",
                "Glacial Peaks of Zenthara",
                "A mystical primate with translucent fur that refracts light like crystal. Found only in the mythical frozen mountains of Zenthara, these monkeys can survive temperatures as low as -50°C and their fur sparkles like diamonds in moonlight.",
                500,
                71.2345,
                -156.7890,
                0,
                true
            ),
            new MonkeySpecies(
                "Volcanic Ember Monkey",
                "Molten Caverns of Pyrothia",
                "A fire-resistant primate that lives near active volcanic chambers. These monkeys have heat-resistant fur that glows with an orange-red hue and they feed on sulfur-rich plants. They are known to leap across lava flows in the fictional realm of Pyrothia.",
                1200,
                19.4567,
                -155.8901,
                0,
                true
            ),
            new MonkeySpecies(
                "Quantum Phase Monkey",
                "Interdimensional Nexus of Voidland",
                "A theoretical primate that exists in multiple dimensions simultaneously. Native to the non-existent plane of Voidland, these monkeys can phase through solid matter and communicate through quantum entanglement with their interdimensional counterparts.",
                300,
                90.0000,
                0.0000,
                0,
                true
            ),
            new MonkeySpecies(
                "Luminous Cloud Monkey",
                "Floating Islands of Aerios",
                "An aerial primate that lives in perpetual flight among the mythical floating islands of Aerios. These monkeys have gossamer-like fur and can glide effortlessly through clouds. They feed on atmospheric particles and glowing sky fruits.",
                800,
                -45.1234,
                168.5678,
                0,
                true
            ),
            new MonkeySpecies(
                "Temporal Weaver Monkey",
                "Chrono Sanctuaries of Timenia",
                "A time-manipulating primate from the imaginary realm of Timenia. These monkeys can slow down time around them to catch prey and have been observed to age at different rates. They are rumored to have existed across all timelines simultaneously.",
                150,
                42.3456,
                -87.6543,
                0,
                true
            )
        );
        
        for (MonkeySpecies species : initialSpecies) {
            speciesDatabase.put(species.speciesName().toLowerCase(), species);
        }
    }
}

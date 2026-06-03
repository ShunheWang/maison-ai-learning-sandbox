package org.acme.model;

/**
 * Represents a monkey species with all relevant information.
 * This is an immutable record that contains species data including
 * location, population, coordinates, and access tracking.
 */
public record MonkeySpecies(
    String speciesName,
    String location,
    String details,
    Integer population,
    Double latitude,
    Double longitude,
    Integer accessed,
    Boolean isFictional
) {
    
    /**
     * Creates a new MonkeySpecies with incremented access count.
     * 
     * @return A new MonkeySpecies instance with accessed count incremented by 1
     */
    public MonkeySpecies withIncrementedAccess() {
        return new MonkeySpecies(
            this.speciesName,
            this.location,
            this.details,
            this.population,
            this.latitude,
            this.longitude,
            this.accessed + 1,
            this.isFictional
        );
    }
    
    /**
     * Formats the monkey species information for display.
     * 
     * @return A formatted string containing all species information
     */
    public String toFormattedString() {
        String fictionalFlag = isFictional ? " *FAKE*" : "";
        return String.format("""
            Species Name: %s%s
            Location: %s
            Details: %s
            Population: %d
            Lat/Lon: %f, %f
            Accessed: %d times
            """, 
            speciesName, fictionalFlag, location, details, population, latitude, longitude, accessed);
    }
}

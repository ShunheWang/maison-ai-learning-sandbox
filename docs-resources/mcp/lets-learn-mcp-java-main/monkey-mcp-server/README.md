# Monkey Species MCP Server

A Model Context Protocol (MCP) server built with Java 21 and Quarkus that provides tools for exploring monkey species data.

## Features

This MCP server provides the following tools:

- **list_monkey_species**: Lists all available monkey species with basic information
- **get_monkey_species_details**: Gets detailed information for a specific monkey species by name
- **get_random_monkey_species**: Returns a random monkey species with full details
- **get_monkey_species_stats**: Provides statistics about the monkey species database

## Architecture

The application follows a layered architecture:

- **Model Layer**: Immutable record types (`MonkeySpecies`)
- **Repository Layer**: Thread-safe data management (`MonkeySpeciesRepository`)
- **Service Layer**: Business logic (`MonkeySpeciesService`)
- **MCP Layer**: MCP tools implementation (`MonkeySpeciesMcpServer`)

## Data Model

Each monkey species contains:
- Species Name
- Location
- Detailed description
- Population count
- Geographic coordinates (Lat/Lon)
- Access counter (tracks how often the species data is accessed)

## Quick Start

### Prerequisites
- Java 21
- Maven 3.8+

### Running the Application

```bash
# Development mode (with live reload)
./mvnw quarkus:dev

# Production mode
./mvnw clean package
java -jar target/quarkus-app/quarkus-run.jar
```

### Accessing the MCP Server

The MCP server is available at:
```
http://localhost:8080/mcp/sse
```

## Sample Data

The server comes pre-loaded with information about various monkey species including:

- **Proboscis Monkey** (Borneo)
- **Golden Snub-nosed Monkey** (China)
- **Howler Monkey** (Central and South America)
- **Japanese Macaque** (Japan)
- **Mandrill** (Equatorial Africa)
- **Spider Monkey** (Central and South America)

## Usage Examples

### Using with MCP Client

Connect your MCP client to `http://localhost:8080/mcp/sse` and use the available tools:

1. **List all species**: Call `list_monkey_species`
2. **Get specific details**: Call `get_monkey_species_details` with a species name
3. **Random discovery**: Call `get_random_monkey_species`
4. **Database stats**: Call `get_monkey_species_stats`

### Tool Examples

```json
// List all species
{
  "tool": "list_monkey_species"
}

// Get details for a specific species
{
  "tool": "get_monkey_species_details",
  "parameters": {
    "speciesName": "Proboscis Monkey"
  }
}

// Get a random species
{
  "tool": "get_random_monkey_species"
}

// Get database statistics
{
  "tool": "get_monkey_species_stats"
}
```

## Development

### Running Tests

```bash
./mvnw test
```

### Code Structure

```
src/main/java/org/acme/
├── model/
│   └── MonkeySpecies.java          # Immutable data model
├── repository/
│   └── MonkeySpeciesRepository.java # Data management
├── service/
│   └── MonkeySpeciesService.java   # Business logic
└── mcp/
    └── MonkeySpeciesMcpServer.java # MCP tools
```

## Configuration

Key configuration properties in `src/main/resources/application.properties`:

```properties
quarkus.application.name=monkey-mcp-server
quarkus.http.port=8080
```

## Error Handling

All MCP tools are designed to:
- Never return `null`
- Provide meaningful error messages
- Validate input parameters
- Handle edge cases gracefully

## Thread Safety

The application is designed to be thread-safe:
- Immutable data models using Java records
- Thread-safe repository operations using `ConcurrentHashMap`
- Stateless service components

## Technology Stack

- **Java 21**: Modern Java features and performance
- **Quarkus 3.24.3**: Supersonic subatomic Java framework
- **MCP Server SSE Extension**: HTTP Server-Sent Events transport for MCP
- **CDI**: Contexts and Dependency Injection
- **JUnit 5**: Testing framework

## License

This project is open source and available under the [MIT License](LICENSE).

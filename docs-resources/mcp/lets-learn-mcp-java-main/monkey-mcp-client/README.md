# Monkey MCP Console Application

A Quarkus console application that integrates with AI models through Ollama and registers MCP (Model Context Protocol) servers for additional tools and capabilities.

## Features

- **Chat Interface**: Interactive console chat with Ollama LLMs
- **MCP Integration**: Connect to the Monkey species MCP server via HTTP SSE transport
- **Tool Discovery**: List and use available tools from MCP servers
- **Modular Design**: Clean separation of concerns with services and commands

## Technology Stack

- **Java 21** with Maven
- **Picocli** for console application interface
- **LangChain4J** for AI chat interactions and MCP client support
- **Ollama** for local LLM hosting
- **Jackson** for JSON processing

## Prerequisites

1. **Java 21** or later
2. **Ollama** running locally on `http://localhost:11434` with `llama3.2` model
3. **Monkey MCP Server** running on `http://localhost:8080/mcp/sse`

## Quick Start

### 1. Install Ollama and pull the model
```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama service
ollama serve

# Pull the llama3.2 model
ollama pull llama3.2
```

### 2. Start the Monkey MCP Server
Ensure the monkey species MCP server is running at `http://localhost:8080/mcp/sse`.

### 3. Build the project
```bash
# Build
./mvnw verify
```

## Available Commands

### Help Command
Show available commands:
```bash
java -jar target/cli-monkey-mcp-client.jar -h
```

### Tools Command
List all available MCP tools from registered servers:
```bash
java -jar target/cli-monkey-mcp-client.jar tools
```

### Chat Command
Start an interactive chat session with the Ollama LLM:
```bash
java -jar target/cli-monkey-mcp-client.jar chat
```


## MCP Configuration

The application connects to MCP servers defined in `mcp.json` file located where the application is launched from (working directory):

```json
{
  "servers": {
    "monkey-species": {
      "type": "sse",
      "url": "http://localhost:8080/mcp/sse"
    }
  }
}
```

## Project Structure

```
src/main/java/org/acme/
├── McpClientApplication.java    # Main application class
├── client/
│   ├── ChatService.java         # Ollama chat service
│   └── ToolsService.java        # MCP client service
└── command/
    ├── ChatCommand.java         # Chat command implementation
    └── ToolsCommand.java        # Tools command implementation
```

## Example Usage

### Chat Session
```
$ java -jar target/cli-monkey-mcp-client.jar chat

═══════════════════════════════════
      Java MCP Chat Client
═══════════════════════════════════
→ Starting chat with local Ollama (llama3.2) + MCP Tools
→ Available tools: 2 monkey species tools

💡 Try asking:
   • 'What monkey species do you know?'
   • 'Tell me about a random monkey'

Type 'exit', 'quit', or 'bye' to end the conversation
───────────────────────────────────

You: Tell me about capuchin monkeys
AI: I can help you with monkey species information! I have access to MCP tools that can provide details about various monkey species, their habitats, and characteristics...

You: List all monkey species
AI: I have access to several MCP tools for monkey species information:
- get_monkey_species: Get detailed information about a specific species
- list_monkey_species: List all available monkey species
- get_monkey_habitat: Get habitat information for a species

You: exit
👋 Goodbye!
```

### Tools Listing
```
$ java -jar target/cli-monkey-mcp-client.jar tools
...

═════ MCP Tools ═════

Tool: get_monkey_species_details
  Description: Get detailed information for a specific monkey species by name
  Parameters: JsonObjectSchema {description = null, properties = {speciesName=JsonStringSchema {description = null }}, required = [speciesName], additionalProperties = null, definitions = {} }

Tool: get_monkey_species_stats
  Description: Get statistics about the monkey species database
  Parameters: JsonObjectSchema {description = null, properties = {}, required = [], additionalProperties = null, definitions = {} }

Tool: get_random_monkey_species
  Description: Get a random monkey species with full details
  Parameters: JsonObjectSchema {description = null, properties = {}, required = [], additionalProperties = null, definitions = {} }

Tool: list_monkey_species
  Description: List all available monkey species with their basic information
  Parameters: JsonObjectSchema {description = null, properties = {}, required = [], additionalProperties = null, definitions = {} }

───────────────────────────────────
Total: 4 tools available
→ Shutting down MCP tools service...
✓ MCP client monkeymcp closed
✓ All MCP clients closed
```

## Troubleshooting

1. **Ollama Connection Issues**: Ensure Ollama is running on `localhost:11434`
2. **MCP Server Connection**: Verify the monkey MCP server is accessible at `localhost:8080/mcp/sse`
3. **Model Not Found**: Pull the required model with `ollama pull llama3.2`

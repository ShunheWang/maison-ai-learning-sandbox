# Part 3: Using the MCP Client Application

> **Navigation**: [← Back to MCP Server](01_MCP_SERVER.md) | [Back to Overview](README.md)

## Overview

In this section, you'll learn how to use the pre-built MCP client application that's already implemented in the `monkey-mcp-client` folder. This console application demonstrates how to:

- Connect to an MCP server via HTTP SSE transport
- List available MCP tools from the server
- Chat with AI models while having access to MCP tools
- Handle responses and display results in a user-friendly format

## 🎯 What You'll Learn

- How to run and use the existing MCP client implementation
- Understanding the architecture and code structure
- How the client integrates LangChain4j with Ollama and MCP servers
- How to configure MCP servers via JSON configuration
- Ideas for building your own MCP client applications

## Prerequisites

Before using the MCP client, ensure you have:

1. **Java 21** or later installed
2. **Ollama** running locally with the `llama3.2` model
3. **Monkey MCP Server** running on `http://localhost:8080/mcp/sse`

### Setting up Ollama

If you don't have Ollama installed yet:

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama service
ollama serve

# In another terminal, pull the required model
ollama pull llama3.2
```

## Using the Pre-built MCP Client

### 1. Navigate to the Client Directory

```bash
cd monkey-mcp-client
```

### 2. Build the Client Application

```bash
./mvnw package
```

This creates an executable JAR file `target/cli-mcp-client.jar` using Maven Assembly Plugin.

### 3. Start the Monkey MCP Server

In another terminal, make sure your MCP server is running:

```bash
cd ../monkey-mcp-server
./mvnw quarkus:dev
```

### 4. Use the Client Commands

The client provides three main commands:

#### Show Help
```bash
java -jar target/cli-mcp-client.jar -h
```

#### List Available MCP Tools
```bash
java -jar target/cli-mcp-client.jar tools
```

Expected output:
```
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
```

#### Start Interactive Chat
```bash
java -jar target/cli-mcp-client.jar chat
```

Example conversation:
```
═══════════════════════════════════
      Java MCP Chat Client
═══════════════════════════════════
→ Starting chat with local Ollama (llama3.2) + MCP Tools
→ Available tools: 4 monkey species tools

💡 Try asking:
   • 'What monkey species do you know?'
   • 'Tell me about a random monkey'

Type 'exit', 'quit', or 'bye' to end the conversation
───────────────────────────────────

You: What monkey species do you know?
→ Initializing MCP tools...
✓ MCP tools initialized successfully
AI: I can help you with information about various monkey species! Let me check what species are available in our database...

[The AI will use the MCP tools to list and provide information about monkey species]

You: Tell me about a random monkey
AI: [The AI will call the get_random_monkey_species tool and provide interesting facts]

You: exit
👋 Goodbye!
```

## Understanding the Implementation

### Project Structure

The MCP client is organized as follows:

```
monkey-mcp-client/
├── src/main/java/org/acme/
│   ├── McpClientApplication.java    # Main application with CLI setup
│   ├── client/
│   │   ├── ChatService.java         # Ollama chat integration
│   │   └── ToolsService.java        # MCP client and tools management
│   ├── command/
│   │   ├── ChatCommand.java         # Chat command implementation
│   │   └── ToolsCommand.java        # Tools listing command
│   └── model/
│       └── Bot.java                 # AI service interface
├── src/main/resources/
│   ├── mcp.json                     # MCP server configuration
│   └── logging.properties           # Logging configuration
├── mcp.json                         # Runtime MCP configuration
└── pom.xml                          # Maven dependencies and build
```

### Key Components

#### 1. Main Application (`McpClientApplication.java`)
- Uses **PicoCLI** for command-line interface
- Configures logging from properties file
- Defines subcommands for `chat` and `tools`

#### 2. Chat Service (`ChatService.java`)
- Integrates **LangChain4j** with **Ollama** for AI chat
- Uses `OllamaChatModel` with `llama3.2` model
- Implements chat memory for conversation context
- Automatically integrates MCP tools via `ToolsService`

#### 3. Tools Service (`ToolsService.java`)
- Reads `mcp.json` configuration file
- Registers MCP servers using `DefaultMcpClient` with `HttpMcpTransport`
- Creates `McpToolProvider` for AI integration
- Handles JSON parsing with Jackson ObjectMapper

#### 4. MCP Configuration (`mcp.json`)
```json
{
  "servers": {
    "monkeymcp": {
      "type": "sse",
      "url": "http://localhost:8080/mcp/sse"
    }
  }
}
```

### Technology Stack

- **Java 21**: Modern Java with records and pattern matching
- **Maven**: Build and dependency management
- **PicoCLI**: Command-line interface framework
- **LangChain4j**: AI integration framework
- **Ollama**: Local LLM hosting
- **Jackson**: JSON processing
- **Maven Assembly Plugin**: Creates executable JAR with dependencies

## Building Your Own MCP Client

### 💡 Exercise: Create Your Own MCP Client

Now that you understand how the existing client works, here are some ideas for building your own MCP client using **GitHub Copilot**:

#### 1. Web-based MCP Client
Create a Spring Boot web application that:
- Provides a web UI for chatting with AI + MCP tools
- Displays available tools in a dashboard
- Shows conversation history
- Supports multiple MCP servers

**GitHub Copilot Prompt**:
```
Create a Spring Boot web application with Thymeleaf that integrates Spring AI with Ollama and MCP servers. Include a chat interface, tools dashboard, and MCP server configuration management.
```

#### 2. Desktop GUI MCP Client
Develop a JavaFX application that:
- Provides a rich desktop interface for MCP interactions
- Shows tool results in formatted tables/charts
- Supports drag-and-drop for file-based tools
- Includes a conversation history viewer

**GitHub Copilot Prompt**:
```
Create a JavaFX desktop application that integrates with MCP servers. Include a chat interface, tools panel, results visualization, and conversation history. Use LangChain4j for AI integration.
```

### 🚀 GitHub Copilot Tips for MCP Development

When building your own MCP client, provide GitHub Copilot with these context instructions:

```markdown
# MCP Client Development Guidelines

## Core Dependencies
- dev.langchain4j:langchain4j-mcp:1.1.0-beta7
- dev.langchain4j:langchain4j-ollama:1.1.0-rc1
- com.fasterxml.jackson.core:jackson-databind (for JSON)

## Key Classes to Use
- DefaultMcpClient: Main MCP client implementation
- HttpMcpTransport: For HTTP SSE transport
- McpToolProvider: Integrates MCP tools with LangChain4j
- OllamaChatModel: For local AI chat

## Configuration Pattern
Always read MCP server configuration from JSON:
```json
{
  "servers": {
    "server_name": {
      "type": "sse",
      "url": "http://localhost:port/mcp/sse"
    }
  }
}
```

## Error Handling
- Handle connection timeouts gracefully
- Provide fallback when MCP servers are unavailable
- Log errors but continue operation when possible
- Validate JSON configuration before use

## Best Practices
- Use connection pooling for multiple MCP servers
- Implement proper resource cleanup with try-with-resources
- Cache tool specifications to reduce server calls
- Use async operations for better user experience
```

## Troubleshooting

### Common Issues

1. **"Connection refused"**: Ensure MCP server is running on `http://localhost:8080`
2. **"Model not found"**: Run `ollama pull llama3.2` to download the model
3. **"No tools available"**: Check that `mcp.json` file exists and has correct server URLs
4. **"JSON parsing errors"**: Verify the MCP server returns valid JSON responses

### Debugging Tips

- Use VS Code's Java debugger with breakpoints in `ChatService` and `ToolsService`
- Check server logs in the `monkey-mcp-server` terminal
- Test MCP server directly: `curl -X GET http://localhost:8080/mcp/sse`
- Verify Ollama is running: `ollama list` and `ollama serve`
- Enable debug logging by modifying `logging.properties`

## Conclusion

You've successfully:
- ✅ **Used** the pre-built MCP client to interact with your monkey species server
- ✅ **Understood** the architecture and implementation patterns
- ✅ **Learned** how LangChain4j integrates with MCP and Ollama
- ✅ **Gained** ideas for building your own MCP client applications

### Key Takeaways

1. **MCP Integration**: The client uses LangChain4j's MCP support to dynamically register tools
2. **AI Chat**: Ollama provides local AI capabilities with automatic tool integration
3. **Configuration**: JSON-based configuration makes it easy to add new MCP servers
4. **CLI Design**: PicoCLI provides a clean command-line interface structure
5. **Error Handling**: Proper error handling ensures graceful degradation

### 🎉 Tutorial Complete!

You've successfully completed the Monkey MCP Java tutorial series:
- ✅ **Part 1**: Set up the project and understand MCP concepts
- ✅ **Part 2**: Built a Quarkus-based MCP server with HTTP SSE transport
- ✅ **Part 3**: Used and understood the MCP client implementation

### Next Steps

- **Extend the Server**: Add more monkey-related tools (habitat search, conservation status, etc.)
- **Build Custom Clients**: Use the ideas above to create your own MCP client applications
- **Explore Security**: Add authentication and authorization to your MCP servers
- **Deploy to Production**: Containerize and deploy your applications to the cloud
- **Contribute**: Share your MCP implementations with the community

---

> **Congratulations!** You've mastered building and using MCP applications with Java!
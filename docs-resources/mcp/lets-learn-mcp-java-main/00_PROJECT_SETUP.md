# Part 1: Prerequisites and Setup

> **Navigation**: [← Back to Overview](README.md) | [Next: Part 2 - MCP Server →](01_MCP_SERVER.md)

## ⏱️ Time Estimate
- **Setup time**: 10-30 minutes
- **Tutorial completion**: 60-75 minutes

## What You'll Need
Before diving into MCP development with Java and Quarkus, ensure you have the following tools installed:

### 1. Visual Studio Code
- Download and install [VS Code](https://code.visualstudio.com/)
- Essential for MCP development and integration

### 2. Java 21
- Install [Microsoft Build of OpenJDK 21](https://microsoft.com/openjdk/) or a Java 21 compatible JDK
- **Minimum version**: Java 21.0.0
- Verify installation: `java --version`
- Ensure JAVA_HOME environment variable is set correctly

### 3. Extension Pack for Java
- Install the [Extension Pack for Java](https://marketplace.visualstudio.com/items?itemName=vscjava.vscode-java-pack) extension
- Provides comprehensive Java development support
- Includes intelligent auto complete, debugging, Maven/Gradle support, and more

### 4. Quarkus CLI
- Install the [Quarkus CLI](https://quarkus.io/guides/cli-tooling)
- Enables quick project creation and development commands
- Verify installation: `quarkus --version`

### 5. Ollama LLM Locally
- Install [Ollama](https://ollama.com/) to run LLM models locally
- Pull the `llama3.2` model for MCP tooling support
```bash
ollama pull llama3.2
```
- Start the Ollama server: `ollama serve`

## Environment Verification
- [ ] VS Code installed and running
- [ ] Java 21 installed and JAVA_HOME configured
- [ ] Extension Pack for Java active in VS Code
- [ ] Quarkus CLI installed
- [ ] Ollama installed with llama3.2 model
- [ ] Basic understanding of MCP concepts

## Common Setup Issues

### Java Issues
- **JAVA_HOME not set**: Add `export JAVA_HOME=/path/to/java` to your shell profile (.bashrc, .zshrc)
- **Wrong Java version**: Use `java --version` to verify you have Java 21+
- **Multiple Java versions**: Use `update-alternatives` (Linux) or `jenv` (macOS) to manage versions

### Quarkus CLI Issues
- **Command not found**: Ensure Quarkus CLI is in your PATH
- **Version mismatch**: Update with `quarkus --version` and reinstall if needed

### Ollama Issues
- **Model not found**: Run `ollama pull llama3.2` to download the model
- **Connection refused**: Ensure Ollama is running with `ollama serve`

## What is Model Context Protocol (MCP)?

The Model Context Protocol (MCP) is an open standard that enables AI assistants to securely access and interact with external tools, data sources, and services. Think of it as a bridge that allows AI models like GitHub Copilot, ChatGPT, or Claude to:

- **Access Real-time Data**: Connect to databases, APIs, and live data sources
- **Execute Actions**: Perform operations like creating files, sending emails, or managing systems
- **Extend Capabilities**: Add custom functionality specific to your needs
- **Maintain Security**: Control what the AI can and cannot access

### Key Benefits for Java Developers

1. **Familiar Technology Stack**: Use your existing Java skills and rich ecosystem
2. **Quarkus Performance**: Optimized for fast startup and low memory usage
3. **Enterprise Ready**: Built-in support for dependency injection, configuration, and async patterns
4. **Type Safety**: Strong typing with compile-time validation
5. **Rich Tooling**: Leverage VS Code Java extensions and Quarkus dev tools
6. **HTTP SSE Protocol**: Efficient real-time communication via Server-Sent Events

### Architecture Overview

```
┌─────────────────┐    MCP Protocol    ┌──────────────────┐
│   AI Assistant  │ ◄─────────────────►│   MCP Server     │
│ (VS Code, etc.) │    (HTTP SSE)      │ (Java/Quarkus)   │
└─────────────────┘                    └──────────────────┘
                                              │
                                              ▼
                                       ┌──────────────────┐
                                       │  Monkey Services │
                                       │ (Business Logic) │
                                       └──────────────────┘
```

### Use Cases

- **Monkey Species Management**: Provide AI assistants with access to monkey species data
- **Conservation Data**: Connect AI to wildlife conservation databases and statistics
- **Educational Content**: Generate and update educational content about primates
- **Research Assistance**: Help researchers with monkey-related queries and data analysis
- **Interactive Learning**: Create engaging educational experiences about monkey species

### Project Structure

This tutorial will guide you through building:

- **MCP Server**: Quarkus-based HTTP SSE server with monkey species tools
- **MCP Client**: Interactive CLI client using LangChain4j and Ollama
- **Integration**: Connect both components for a complete MCP ecosystem

---

> **Next Step**: Now that you understand MCP and have your Java/Quarkus environment set up, let's build your MCP server for monkey species management.

**Continue to**: [Part 2 - Building MCP Server →](01_MCP_SERVER.md)

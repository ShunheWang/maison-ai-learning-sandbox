# Learn MCP Java Tutorial

A comprehensive Java tutorial demonstrating Model Context Protocol (MCP) implementation with Quarkus server and LangChain4j client, featuring a monkey species dataset for hands-on learning.

## 📚 Tutorial Overview

This project showcases a complete MCP ecosystem built in Java, including:

- **MCP Server**: Quarkus-based HTTP SSE server with monkey species data tools
- **MCP Client**: Interactive CLI client using LangChain4j and Ollama integration
- **Step-by-step Documentation**: Complete guides for building MCP applications with GitHub Copilot

## 🚀 Quick Start

### Prerequisites
- Java 21+
- Maven 3.8+
- VS Code with Java Extension Pack
- Ollama (for LLM integration)

### Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/brunoborges/monkey-mcp-java.git
   cd monkey-mcp-java
   ```

2. **Start the MCP Server**
   ```bash
   cd monkey-mcp-server
   ./mvnw quarkus:dev
   ```

3. **Run the MCP Client**
   ```bash
   cd monkey-mcp-client
   ./mvnw package
   java -jar target/monkey-mcp-client.jar
   ```

## 📖 Tutorial Structure

This tutorial is organized into sequential parts:

| Part | Title | Description |
|------|-------|-------------|
| **[Part 1: Prerequisites and Setup](00_PROJECT_SETUP.md)** | Project Setup | Install tools, understand MCP, and prepare your environment |
| **[Part 2: Building the MCP Server](01_MCP_SERVER.md)** | MCP Server | Build a Quarkus-based MCP server with monkey species tools |
| **[Part 3: Building the MCP Client](02_MCP_CLIENT.md)** | MCP Client | Create an interactive CLI client using LangChain4j |

## 🏗️ Architecture

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

## 🐒 Featured Tools

The MCP server provides these monkey species tools:

- **List Species**: Get all available monkey species
- **Species Details**: Retrieve detailed information about specific species
- **Random Species**: Get a random monkey species
- **Statistics**: View dataset statistics and access counts

## 🛠️ Technology Stack

- **Java 21**: Modern Java features and performance
- **Quarkus**: Supersonic Subatomic Java Framework
- **LangChain4j**: Java framework for building LLM applications
- **Ollama**: Local LLM runtime
- **Maven**: Build and dependency management
- **PicoCLI**: Command-line interface framework

## 🎯 Learning Objectives

By completing this tutorial, you will:

- Understand MCP protocol and its benefits
- Build production-ready MCP servers with Quarkus
- Create MCP clients using LangChain4j
- Integrate with local LLMs using Ollama
- Apply AI-assisted development with GitHub Copilot

## 📝 Project Structure

```
monkey-mcp-java/
├── 00_PROJECT_SETUP.md       # Prerequisites and environment setup
├── 01_MCP_SERVER.md          # MCP Server implementation guide
├── 02_MCP_CLIENT.md          # MCP Client implementation guide
├── monkey-mcp-server/        # Quarkus MCP server project
│   ├── src/main/java/        # Java source code
│   └── pom.xml              # Maven dependencies
└── monkey-mcp-client/        # LangChain4j MCP client project
    ├── src/main/java/        # Java source code
    └── pom.xml              # Maven dependencies
```

## 🤝 Contributing

This is an educational project designed to teach MCP implementation in Java. Contributions, suggestions, and improvements are welcome!

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Useful Links

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Quarkus Framework](https://quarkus.io/)
- [LangChain4j Documentation](https://docs.langchain4j.dev/)
- [Ollama](https://ollama.com/)

---

**Start your MCP journey**: [Part 1 - Prerequisites and Setup →](00_PROJECT_SETUP.md)

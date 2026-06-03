# Part 2: Building your first Java-based MCP Server using GitHub Copilot

> **Navigation**: [← Back to Prerequisites](00_PROJECT_SETUP.md) | [Next: Part 3 - MCP Client →](02_MCP_CLIENT.md)

## Overview

In this section, you'll learn how to build an MCP server with a fun monkey-themed use case.
This hands-on tutorial will teach you how MCP servers are implemented using Java and Quarkus.

## 🎯 What You'll Learn
- How to create a Quarkus MCP server with HTTP SSE transport
- How to implement MCP tools with proper annotations
- How to test your server with MCP Inspector
- How to integrate with GitHub Copilot for enhanced development
- How to structure a production-ready MCP server

## Step-by-Step Walkthrough

### Create a new Java and Quarkus project

Create a new Quarkus project named **monkey-app**. 
For that, run the following Quarkus CLI command in your terminal in your workspace folder where you host your projects:

```bash
quarkus create app --no-code -x rest-client-jackson,qute,mcp-server-sse monkey-mcp-server
```
If the Quarkus CLI is not installed, you can follow the instructions on the [Quarkus website](https://quarkus.io/guides/cli-tooling) to set it up.

### Push to GitHub

- Create a new GitHub repository
- Connect your local project
- Make your first commit
- This can be done through the VS Code Source Control panel

### Open the project in VS Code

- Open the newly created project in Visual Studio Code

You can do this by running the following command in your terminal:

```bash
code monkey-mcp-server
```

- Ensure the Java Extension Pack is installed and active
- Verify that the project builds successfully with `./mvnw verify`

### ✅ Validation Checkpoint
- [ ] Project builds successfully with `./mvnw verify`
- [ ] No compilation errors in VS Code
- [ ] Quarkus extensions are properly loaded

### Build the MCP Server using GitHub Copilot
Now that your project is set up, let's use GitHub Copilot to help us implement the MCP Server application.

#### Provide GitHub Copilot Instructions for better context

Visual Studio Code [has a feature](https://code.visualstudio.com/docs/copilot/copilot-customization#_use-instructionsmd-files) that allows you to provide instructions to GitHub Copilot to help it perform tasks in a particular way. 
Here we will give it instructions to build an MCP server using Java and Quarkus.

Create the folder `.github` and add a file named `quarkus-mcp-server.instructions.md` with the following content:

```markdown
    # Quarkus MCP Server

    Build MCP servers with Java 21, Quarkus, and HTTP SSE transport.

    ## Stack
    - Java 21 with Quarkus Framework
    - MCP Server Extension: `mcp-server-sse`
    - CDI for dependency injection
    - MCP Endpoint: `http://localhost:8080/mcp/sse`

    ## Quick Start
    ```bash
    quarkus create app --no-code -x rest-client-jackson,qute,mcp-server-sse your-domain-mcp-server
    ```

    ## Structure
    - Use standard Java naming conventions (PascalCase classes, camelCase methods)
    - Organize in packages: `model`, `repository`, `service`, `mcp`
    - Use Record types for immutable data models
    - State management for immutable data must be managed by repository layer
    - Add Javadoc for public methods

    ## MCP Tools
    - Must be public methods in `@ApplicationScoped` CDI beans
    - Use `@Tool(name="tool_name", description="clear description")`
    - Never return `null` - return error messages instead
    - Always validate parameters and handle errors gracefully

    ## Architecture
    - Separate concerns: MCP tools → Service layer → Repository
    - Use `@Inject` for dependency injection
    - Make data operations thread-safe
    - Use `Optional<T>` to avoid null pointer exceptions

    ## Common Issues
    - Don't put business logic in MCP tools (use service layer)
    - Don't throw exceptions from tools (return error strings)
    - Don't forget to validate input parameters
    - Test with edge cases (null, empty inputs)
```

Now, you can ask GitHub Copilot to help you implement the MCP server by providing it with the following prompt:

```plaintext
    Implement an MCP server with HTTP SSE protocol, using Quarkus, that will have the following capabilities (tools):

    - **list_monkey_species**: Returns all available monkey species
    - **get_monkey_details**: Takes species name as parameter, returns detailed information
    - **get_random_monkey**: Returns a random monkey species
    - **get_monkey_statistics**: Returns dataset statistics (total count, most accessed, etc.)
    
    A monkey species has the following data, as example:

    - Species Name: Proboscis Monkey
    - Location: Borneo
    - Details: The proboscis monkey or long-nosed monkey, known as the bekantan in Malay, is a reddish-brown arboreal Old World monkey that is endemic to the south-east Asian island of Borneo.
    - Population: 15000
    - Lat/Lon: 0.961883, 114.55485
    - Accessed: 1 times

    Include a data set of monkey species in the code. 
    Add a few fictional species with different attributes.
```

### Expected Server Output
When the server starts with `./mvnw quarkus:dev`, you should see:
```
__  ____  __  _____   ___  __ ____  ______
 --/ __ \/ / / / _ | / _ \/ //_/ / / / __/
 -/ /_/ / /_/ / __ |/ , _/ ,< / /_/ /\ \
--\___\_\____/_/ |_/_/|_/_/|_|\____/___/
INFO  [io.quarkus] (Quarkus Main Thread) monkey-mcp-server 1.0.0-SNAPSHOT on JVM started in 2.345s
INFO  [io.quarkus] (Quarkus Main Thread) Profile dev activated. Live Coding activated.
INFO  [io.quarkus] (Quarkus Main Thread) Installed features: [mcp-server-sse, rest-client-jackson, qute]
```

### Testing the MCP Server with MCP Inspector

To test your MCP server, you can use the [MCP Inspector](https://github.com/modelcontextprotocol/inspector).

```bash
npx @modelcontextprotocol/inspector
```

Point the MCP Inspector to your server URL:

```
http://localhost:8080/mcp/sse
```

### ✅ Final Validation
- [ ] MCP server starts on port 8080
- [ ] MCP Inspector can connect to `http://localhost:8080/mcp/sse`
- [ ] All 4 monkey tools are available and functional
- [ ] GitHub Copilot can access monkey species data

Next, configure the Monkey MCP Server in your Visual Studio Code environment by creating a `.vscode/mcp.json` file with the following content:

```json
{
    "inputs": [],
    "servers": {
        "monkeymcp": {
            "type": "sse",
            "url": "http://localhost:8080/mcp/sse"
        }
    }
}
```

Now, go back to GitHub Copilot and ask it if it knows about monkey species.

```plaintext
do you know of any monkey species?
```

Hopefully the MCP Server will be accessed by GitHub Copilot and it will return a list of monkey species!

## Conclusion
Congratulations! You've successfully built your first Java-based MCP server using Quarkus and GitHub Copilot.
This hands-on experience has given you a solid understanding of how to implement MCP servers, leverage AI assistants, and create useful tools for managing monkey species data.

---

> **Next Step**: Let's implement an MCP Client application, using GitHub Copilot, that talks to the MCP Server that we just built.

**Continue to**: [Part 3 - Building Your Own MCP Client →](02_MCP_CLIENT.md)
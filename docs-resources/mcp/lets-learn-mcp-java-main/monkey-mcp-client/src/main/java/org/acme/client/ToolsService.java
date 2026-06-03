package org.acme.client;

import static java.lang.System.err;
import static java.lang.System.out;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import dev.langchain4j.agent.tool.ToolSpecification;
import dev.langchain4j.mcp.McpToolProvider;
import dev.langchain4j.mcp.client.DefaultMcpClient;
import dev.langchain4j.mcp.client.McpClient;
import dev.langchain4j.mcp.client.transport.http.HttpMcpTransport;

public class ToolsService {

    private final List<McpClient> mcpClients = new ArrayList<>();
    private McpToolProvider toolProvider;

    public ToolsService() {
        out.println("→ Initializing MCP tools...");
        try {
            registerMCPServers();
            initializeToolProvider();
            out.println("✓ MCP tools initialized successfully");
        } catch (Exception e) {
            err.printf("✗ Failed to initialize MCP tools: %s%n", e.getMessage());
        }
    }

    private void registerMCPServers() {
        var inputStream = getConfigurationFile();

        if (inputStream == null) {
            out.println("⚠ mcp.json configuration file not found in working directory or resources");
            return;
        }

        ObjectMapper objectMapper = new ObjectMapper();
        try (var is = inputStream) {
            var config = objectMapper.readTree(is);
            var servers = config.get("servers");

            if (servers == null || !servers.isObject()) {
                out.println("⚠ No servers configuration found in mcp.json");
                return;
            }

            servers.fieldNames().forEachRemaining(serverName -> {
                registerServer(serverName, servers.get(serverName));
            });

            out.printf("✓ MCP server registration completed. %d server(s) registered%n",
                    mcpClients.size());
        } catch (IOException e) {
            err.printf("✗ Failed to read mcp.json configuration: %s%n", e.getMessage());
        }
    }

    private InputStream getConfigurationFile() {
        var workingDirConfig = Paths.get("mcp.json");
        if (Files.exists(workingDirConfig)) {
            try {
                out.printf("→ Loading mcp.json from working directory: %s%n", workingDirConfig.toAbsolutePath());
                return Files.newInputStream(workingDirConfig);
            } catch (IOException e) {
                err.printf("✗ Failed to read mcp.json from working directory, falling back to bundled resource: %s%n",
                        e.getMessage());
            }
        }

        var resourceStream = getClass().getClassLoader().getResourceAsStream("mcp.json");
        if (resourceStream != null) {
            out.println("→ Loading mcp.json from bundled resource");
        }
        return resourceStream;
    }

    private void registerServer(String serverName, JsonNode serverConfig) {
        out.printf("→ Processing server registration: %s%n", serverName);

        try {
            var url = serverConfig.get("url").asText();
            var type = serverConfig.get("type").asText();

            out.printf("  URL: %s, Type: %s%n", url, type);

            if (!"sse".equals(type)) {
                err.printf("✗ Unsupported transport type '%s' for server: %s%n", type, serverName);
                return;
            }

            out.printf("→ Registering MCP server: %s with URL: %s%n", serverName, url);

            // Configure SSE transport with longer timeouts to prevent connection issues
            var mcpTransport = new HttpMcpTransport.Builder()
                    .sseUrl(url)
                    .timeout(Duration.ofSeconds(60)) // Increased timeout for SSE connections
                    .logRequests(false)
                    .logResponses(false)
                    .build();

            var mcpClient = new DefaultMcpClient.Builder()
                    .key(serverName)
                    .transport(mcpTransport)
                    .build();

            mcpClients.add(mcpClient);
            out.printf("✓ Successfully registered MCP server: %s%n", serverName);
        } catch (RuntimeException e) {
            err.printf("✗ Failed to register MCP server: %s - %s%n", serverName, e.getMessage());
        }
    }

    private void initializeToolProvider() {
        if (mcpClients.isEmpty()) {
            out.println("⚠ No MCP clients registered, tool provider will be empty");
            return;
        }

        toolProvider = McpToolProvider.builder()
                .mcpClients(mcpClients.toArray(new McpClient[mcpClients.size()]))
                .build();

        out.printf("✓ Tool provider initialized with %d MCP client(s)%n",
                mcpClients.size());
    }

    public List<ToolSpecification> getAvailableTools() {
        var allTools = new ArrayList<ToolSpecification>();

        for (var client : mcpClients) {
            try {
                out.printf("→ Retrieving tools from MCP server: %s%n", client.key());
                var clientTools = client.listTools();
                allTools.addAll(clientTools);
                out.printf("✓ Retrieved %d tool(s) from MCP server: %s%n",
                        clientTools.size(), client.key());
            } catch (Exception e) {
                err.printf("⚠ Failed to get tools from MCP server: %s - %s%n", client.key(), e.getMessage());
                // Don't print full stack trace for common connection issues
                if (!(e.getCause() instanceof java.net.SocketTimeoutException)) {
                    err.printf("  Full error details: %s%n", e.toString());
                }
            }
        }

        out.printf("→ Retrieved %d total tool(s) from %d MCP server(s)%n",
                allTools.size(), mcpClients.size());
        return allTools;
    }

    public McpToolProvider getToolProvider() {
        return toolProvider;
    }

    public void shutdown() {
        out.println("→ Shutting down MCP tools service...");
        mcpClients.forEach(t -> {
            try {
                t.close();
            } catch (Exception e) {
                err.printf("✗ Failed to close MCP client %s: %s%n", t.key(), e.getMessage());
            } finally {
                out.printf("✓ MCP client %s closed%n", t.key());
            }
        });
        out.println("✓ All MCP clients closed");
    }

}

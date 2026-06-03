package org.acme;

import java.io.InputStream;
import java.util.logging.LogManager;

import org.acme.command.ChatCommand;
import org.acme.command.ToolsCommand;

import picocli.CommandLine;
import picocli.CommandLine.Command;

@Command(name = "mcp-client", 
         mixinStandardHelpOptions = true, 
         version = "1.0.0", 
         description = "Java based console app to chat with AI+MCP servers using Ollama Local llama3.2 model", 
         subcommands = {ChatCommand.class, ToolsCommand.class })
public class McpClientApplication {

    public static void main(String[] args) {
        // Configure logging from properties file
        configureLogging();
        
        int exitCode = new CommandLine(new McpClientApplication()).execute(args);
        System.exit(exitCode);
    }

    private static void configureLogging() {
        try (InputStream stream = McpClientApplication.class.getClassLoader()
                .getResourceAsStream("logging.properties")) {
            if (stream != null) {
                LogManager.getLogManager().readConfiguration(stream);
            }
        } catch (Exception e) {
            // Fallback to default logging if properties file fails to load
            System.err.println("Warning: Could not load logging configuration: " + e.getMessage());
        }
    }

}

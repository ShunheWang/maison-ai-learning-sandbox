package org.acme.command;

import static java.lang.System.out;

import java.util.function.Consumer;

import org.acme.client.ToolsService;

import dev.langchain4j.agent.tool.ToolSpecification;
import picocli.CommandLine.Command;

@Command(name = "tools", description = "List available MCP tools from registered servers")
public class ToolsCommand implements Runnable {

    ToolsService toolsService = new ToolsService();

    @Override
    public void run() {

        var tools = toolsService.getAvailableTools();

        out.println();
        out.println("═════ MCP Tools ═════");
        out.println();

        if (tools.isEmpty()) {
            out.println("   → No tools available from registered MCP servers.");
            out.println("   → Please ensure MCP servers are running and properly configured.");
            out.println();
            return;
        }

        Consumer<ToolSpecification> printFunction = (ts) -> {
            out.println("Tool: " + ts.name());
            if (ts.description() != null && !ts.description().isEmpty()) {
                out.println("  Description: " + ts.description());
            }
            if (ts.parameters() != null) {
                out.println("  Parameters: " + ts.parameters().toString());
            }
            out.println();
        };

        tools.stream().forEach(printFunction);
        out.println("───────────────────────────────────");
        out.println("Total: " + tools.size() + " tool" + (tools.size() == 1 ? "" : "s") + " available");

        toolsService.shutdown();
    }

}

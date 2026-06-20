from langgraph.graph import StateGraph, END
from state import NewsletterState
from agents import orchestrator, researcher, writer, critic, editor, sender

# Create workflow StateGraph
workflow = StateGraph(NewsletterState)

# Add all 6 nodes
workflow.add_node("orchestrator", orchestrator)
workflow.add_node("researcher", researcher)
workflow.add_node("writer", writer)
workflow.add_node("critic", critic)
workflow.add_node("editor", editor)
workflow.add_node("sender", sender)

# Set Entry Point
workflow.set_entry_point("orchestrator")

# Fixed Edges
workflow.add_edge("orchestrator", "researcher")
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", "critic")
workflow.add_edge("editor", "sender")
workflow.add_edge("sender", END)

# Conditional Edge after critic
def _should_rewrite(state: NewsletterState) -> str:
    if state.get("approved", False):
        return "editor"
    else:
        return "writer"

workflow.add_conditional_edges(
    "critic",
    _should_rewrite,
    {
        "editor": "editor",
        "writer": "writer"
    }
)

# Compile the graph
newsletter_graph = workflow.compile()

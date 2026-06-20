import os
import sys
from graph import newsletter_graph

def main():
    # Validate environment variables
    required_vars = ["GEMINI_API_KEY", "TAVILY_API_KEY", "RESEND_API_KEY", "TO_EMAIL", "FROM_EMAIL"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set them before running the script.")
        sys.exit(1)
        
    print("All environment variables validated. Invoking Vahaz Daily OS Newsletter Graph...")
    
    try:
        # Invoke newsletter_graph with empty initial state
        initial_state = {}
        final_state = newsletter_graph.invoke(initial_state)
        
        print("\n=== Pipeline Execution Summary ===")
        print(f"Date:          {final_state.get('date')}")
        print(f"Final Score:   {final_state.get('score')}/10")
        print(f"Rewrite Count: {final_state.get('rewrite_count')}")
        print(f"Sent Status:   {final_state.get('sent')}")
        
        if final_state.get("error"):
            print(f"Error: {final_state.get('error')}")
            sys.exit(1)
            
        print("Newsletter generated and sent successfully!")
        
    except Exception as e:
        print(f"Error invoking newsletter graph: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

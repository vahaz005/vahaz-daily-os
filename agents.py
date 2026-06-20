import os
import re
import json
import datetime
import markdown
from google import genai
from google.genai import types
from state import NewsletterState
from tools import web_search, fetch_arxiv
from memory import load_recent_memory, save_to_memory

HAIKU  = "gemini-2.5-flash"   # planning, scoring — cheap
SONNET = "gemini-2.5-flash"   # writing — quality matters (using flash for free tier compatibility)

def _call(model: str, system: str, user: str, max_tokens: int = 1000) -> str:
    """
    Central function to make calls to Google's Gemini API.
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set.")
    
    client = genai.Client(api_key=api_key)
    
    config = types.GenerateContentConfig(
        system_instruction=system,
        max_output_tokens=max_tokens,
    )
    
    response = client.models.generate_content(
        model=model,
        contents=user,
        config=config
    )
    return response.text

def _fallback_topics() -> list:
    return [
        "TSMC 2nm N2 GAA process node schedule and yield challenges",
        "NVIDIA Blackwell B200 NVLink architecture and cooling specifications",
        "Apple M4 packaging and Neural Engine core architectures",
        "vLLM PagedAttention throughput optimizations and memory management",
        "LangGraph multi-agent persistence and message state migration patterns",
        "Semiconductor tech stock SOXX performance and interest rate impact",
        "Clock domain crossing CDC synchronization strategies in Verilog RTL",
        "High-contrast black and white photography street composition guide"
    ]

def orchestrator(state: NewsletterState) -> NewsletterState:
    """
    Node 1: orchestrator
    Generates 8 specific search queries for today, avoiding recent memory.
    """
    # Seeds/handles date
    date = state.get("date")
    if not date:
        date = datetime.date.today().isoformat()
        
    recent_memory = load_recent_memory(7)
    
    system_prompt = (
        "You are the Planning and Query Orchestrator agent for the Vahaz Daily OS newsletter.\n"
        "Your task is to generate a JSON array containing exactly 8 specific search queries for today's edition.\n\n"
        "Your response MUST be a valid JSON array of 8 strings and nothing else. Do not include introductory text, "
        "do not include markdown code block formatting (like ```json), just return the raw JSON array. "
        "Example output:\n"
        '["query 1", "query 2", "query 3", "query 4", "query 5", "query 6", "query 7", "query 8"]'
    )
    
    user_prompt = (
        f"Today's date: {date}.\n\n"
        f"Here are the topics/headings covered in the last 7 days (to avoid redundancy):\n"
        f"{recent_memory}\n\n"
        "Please generate exactly 8 search queries. They must mix the following categories:\n"
        "- Exactly 3 queries on semiconductor architecture, packaging, process nodes, or specific hardware makers.\n"
        "- Exactly 2 queries on AI agents, LLM serving/inference infrastructure, or multi-agent coordination frameworks.\n"
        "- Exactly 1 query on technology stocks, tech macroeconomics, or general finance investing concepts.\n"
        "- Exactly 1 query on a digital design/RTL/Verilog/FPGA engineering concept.\n"
        "- Exactly 1 wildcard query (e.g. systems thinking, photography, Urdu poetry, or creative engineering).\n\n"
        "Create specific, search-engine-ready queries that will fetch high-quality, deep technical information."
    )
    
    response_text = _call(HAIKU, system_prompt, user_prompt, max_tokens=600)
    
    topics = []
    try:
        clean_text = response_text.strip()
        # Regex check to strip markdown block wrappers
        if "```json" in clean_text:
            match = re.search(r"```json\s*(.*?)\s*```", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(1)
        elif "```" in clean_text:
            match = re.search(r"```\s*(.*?)\s*```", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(1)
                
        # Locate the bounds of the JSON array
        start = clean_text.find("[")
        end = clean_text.rfind("]")
        if start != -1 and end != -1:
            clean_text = clean_text[start:end+1]
            
        topics = json.loads(clean_text)
        if not isinstance(topics, list) or len(topics) != 8:
            raise ValueError("Parsed object is not a list of length 8")
    except Exception:
        topics = _fallback_topics()
        
    return {
        "date": date,
        "topics": topics,
        "raw_research": "",
        "draft": "",
        "rewrite_count": 0,
        "score": 0,
        "critique": "",
        "approved": False,
        "final_html": "",
        "sent": False,
        "error": None
    }

def researcher(state: NewsletterState) -> NewsletterState:
    """
    Node 2: researcher
    Gathers info on the chosen topics and LLM accelerator hardware.
    """
    topics = state.get("topics", [])
    research_results = []
    
    for topic in topics:
        res = web_search(topic)
        research_results.append(f"### Topic Search: {topic}\n{res}")
        
    arxiv_res = fetch_arxiv("LLM inference optimization hardware accelerator")
    research_results.append(f"### arXiv Research: LLM inference optimization hardware accelerator\n{arxiv_res}")
    
    state["raw_research"] = "\n\n".join(research_results)
    return state

def writer(state: NewsletterState) -> NewsletterState:
    """
    Node 3: writer
    Drafts the newsletter using Sonnet, incorporating critique if retrying.
    """
    raw_research = state.get("raw_research", "")
    rewrite_count = state.get("rewrite_count", 0)
    prev_critique = state.get("critique", "")
    
    system_prompt = (
        "You are an expert technical newsletter writer for Vahaz, a final-year electronics engineer "
        "at BITS Pilani and currently interning at Skyworks. You write the 'The Vahaz Daily OS' newsletter.\n"
        "Your writing style is engineering-deep, specific, authoritative, but engaging. You use systems thinking, "
        "clear metrics, and occasionally weave in Urdu poetry, photography, or finance. You must speak as Vahaz.\n\n"
        "You must structure the newsletter into EXACTLY the following markdown sections, with the specified headers:\n"
        "## § Semiconductor Industry\n"
        "(200+ words; must detail specific companies, process nodes like TSMC GAA/FinFET, and numeric metrics like yield, cost, thermal limits)\n\n"
        "## § AI Hardware\n"
        "(150+ words; focus on inference economics, compute/memory bounds, FLOPs utilization, bandwidth, etc.)\n\n"
        "## § Digital Design Concept\n"
        "(150+ words; cover what existed before -> the engineering problem -> the solution -> Verilog/RTL design implications)\n\n"
        "## § Systems Thinking\n"
        "(120+ words; explain one systems thinking concept or mental model and apply it directly to Vahaz's daily internship/academic work)\n\n"
        "## § Finance Pulse\n"
        "(100+ words; analyze recent stocks, macroeconomic indicators, and introduce one specific investing concept)\n\n"
        "## § Quote of the Day\n"
        "(Include a curated inspiring quote followed by EXACTLY two sentences explanation of why it was chosen today)\n\n"
        "Ensure all word counts are strictly respected. Provide rigorous technical explanations rather than hand-wavy summaries."
    )
    
    user_prompt = ""
    if rewrite_count > 0 and prev_critique:
        user_prompt += (
            f"=== PREVIOUS CRITIQUE FOR IMPROVEMENT ===\n"
            f"Your previous attempt was rejected with the following comments. You must address them in your new draft:\n"
            f"{prev_critique}\n"
            f"=========================================\n\n"
        )
        
    user_prompt += (
        f"Here is the raw research data compiled for today's newsletter:\n\n"
        f"{raw_research}\n\n"
        f"Please write today's newsletter draft. Remember to format it with the exact headings starting with '## § '."
    )
    
    draft = _call(SONNET, system_prompt, user_prompt, max_tokens=3500)
    
    state["draft"] = draft
    state["rewrite_count"] = rewrite_count + 1
    return state

def critic(state: NewsletterState) -> NewsletterState:
    """
    Node 4: critic
    Grades the draft using Haiku. Approves if score >= 7. Forces approval if rewrite_count >= 2.
    """
    draft = state.get("draft", "")
    rewrite_count = state.get("rewrite_count", 0)
    
    system_prompt = (
        "You are the Editorial Critic for the Vahaz Daily OS newsletter.\n"
        "You review the newsletter draft and score it according to the following strict grading rubric:\n"
        "- Depth & engineering insight (up to 4 points)\n"
        "- Specificity, companies, nodes, and metrics (up to 3 points)\n"
        "- Relevance to Vahaz's interests (semiconductor, AI hw, digital design, Urdu, photography) (up to 2 points)\n"
        "- Writing quality, tone, and formatting (up to 1 point)\n\n"
        "For approval, the draft must score 7 points or higher.\n\n"
        "Your response MUST match this format exactly, with no preamble, no markdown, and no extra text:\n"
        "SCORE: <integer between 0 and 10>\n"
        "APPROVED: <yes or no>\n"
        "CRITIQUE: <one paragraph explaining your score and what improvements are needed>"
    )
    
    user_prompt = (
        f"Here is the draft for review:\n\n"
        f"{draft}"
    )
    
    response = _call(HAIKU, system_prompt, user_prompt, max_tokens=300)
    
    # Parse the response
    score = 0
    approved = False
    critique = response.strip()
    
    score_match = re.search(r"SCORE:\s*(\d+)", response, re.IGNORECASE)
    approved_match = re.search(r"APPROVED:\s*(yes|no)", response, re.IGNORECASE)
    critique_match = re.search(r"CRITIQUE:\s*(.*)", response, re.IGNORECASE | re.DOTALL)
    
    if score_match:
        score = int(score_match.group(1))
    if approved_match:
        approved = approved_match.group(1).strip().lower() == "yes"
    if critique_match:
        critique = critique_match.group(1).strip()
        
    # Rubric check
    if score >= 7:
        approved = True
        
    # Safety fallback: force approval after 2 iterations of drafting (meaning writer ran at least twice)
    if rewrite_count >= 2:
        approved = True
        
    state["score"] = score
    state["approved"] = approved
    state["critique"] = critique
    return state

def editor(state: NewsletterState) -> NewsletterState:
    """
    Node 5: editor
    Converts markdown draft to HTML and fits it inside template.html.
    """
    draft = state.get("draft", "")
    date = state.get("date", "")
    
    content_html = markdown.markdown(
        draft, 
        extensions=["fenced_code", "tables", "nl2br"]
    )
    
    template_path = os.path.join(os.path.dirname(__file__), "editions", "template.html")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception:
        # Simple inline template fallback if template.html load fails
        template = "<html><body><h1>The Vahaz Daily OS ({{DATE}})</h1>{{CONTENT}}</body></html>"
        
    final_html = template.replace("{{DATE}}", date).replace("{{CONTENT}}", content_html)
    state["final_html"] = final_html
    return state

def sender(state: NewsletterState) -> NewsletterState:
    """
    Node 6: sender
    Sends the newsletter via Resend. Saves state to memory.json and saves the HTML file.
    """
    import resend
    
    resend.api_key = os.environ.get("RESEND_API_KEY")
    to_email = os.environ.get("TO_EMAIL")
    from_email = os.environ.get("FROM_EMAIL")
    
    # Try sending email
    try:
        if not resend.api_key:
            raise ValueError("RESEND_API_KEY is not set.")
        if not to_email:
            raise ValueError("TO_EMAIL is not set.")
        if not from_email:
            raise ValueError("FROM_EMAIL is not set.")
            
        params = {
            "from": from_email,
            "to": [to_email],
            "subject": f"The Vahaz Daily OS — {state['date']}",
            "html": state["final_html"]
        }
        
        resend.Emails.send(params)
        state["sent"] = True
        
        # Save success to memory
        save_to_memory(state)
        
        # Save HTML file to editions/{date}.html
        edition_filename = os.path.join("editions", f"{state['date']}.html")
        os.makedirs("editions", exist_ok=True)
        with open(edition_filename, "w", encoding="utf-8") as f:
            f.write(state["final_html"])
            
    except Exception as e:
        state["sent"] = False
        state["error"] = str(e)
        
    return state

import os, json
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from typing import TypedDict
from scrapegraphai.graphs import SmartScraperGraph
from utils import create_llm, get_today_str
from pydantic import BaseModel, Field

llm = create_llm()
graph_config = {
    "llm": {
        "model_instance": llm,
        "model_tokens": 1000000,
    },
}

class ChangeAnalysis(BaseModel):
    is_change: bool = Field(..., description="True if a meaningful change is detected, False otherwise")
    summary: str = Field(..., description="A short human-friendly explanation of what changed between snapshots")

SNAPSHOT_FILE = "snapshots.json"

def save_snapshot(url, data):
    if os.path.exists(SNAPSHOT_FILE):
        with open(SNAPSHOT_FILE, "r") as f:
            snapshots = json.load(f)
    else:
        snapshots = {}
    snapshots[url] = {
        "data": data,
        "date": get_today_str()
    }
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(snapshots, f)

def load_snapshot(url):
    if not os.path.exists(SNAPSHOT_FILE):
        return None
    with open(SNAPSHOT_FILE, "r") as f:
        snapshots = json.load(f)
    snapshot = snapshots.get(url)
    if snapshot and isinstance(snapshot, dict) and "data" in snapshot:
        return snapshot["data"]  # Return just the data for backward compatibility
    return snapshot  # Handle old format or direct data

class AlertState(TypedDict):
    url: str
    prompt: str
    mode: str   # "add" or "check"
    last_content: dict
    last_date: str
    new_content: dict
    is_change: bool
    changes: str
    alert: str

def scraper_agent(state: AlertState) -> AlertState:
    smart_scraper = SmartScraperGraph(
        prompt=state["prompt"],
        source=state["url"],
        config=graph_config,
    )
    result = smart_scraper.run()
    state['new_content'] = result['content']
    return state

def save_snapshot_agent(state: AlertState) -> AlertState:
    save_snapshot(state["url"], state["new_content"])
    return {"alert": f"Baseline saved for {state['url']}"}

def load_snapshot_agent(state: AlertState) -> AlertState:
    if not os.path.exists(SNAPSHOT_FILE):
        state['last_content'] = None
        return state
    
    with open(SNAPSHOT_FILE, "r") as f:
        snapshots = json.load(f)
    snapshot = snapshots.get(state["url"])
    
    if snapshot and isinstance(snapshot, dict) and "data" in snapshot:
        state['last_content'] = snapshot["data"]
        state['last_date'] = snapshot.get("date", "Unknown")
    else:
        state['last_content'] = snapshot
        state['last_date'] = "Unknown"
    
    return state

def analyze_changes_agent(state: AlertState) -> AlertState:
    old = f'{state.get("last_content")},Date: {state.get("last_date")}'
    new = f'{state.get("new_content")}, Date: {get_today_str()}'

    if not old:
        empty_analysis = ChangeAnalysis(
            is_change=False,
            summary="No baseline available"
        )
        return Command(goto=END, update={"is_change": False, "alert": empty_analysis.summary})

    structured_llm = llm.with_structured_output(ChangeAnalysis)

    prompt = """
        You are a web change detection assistant. Compare old vs new scraped data for MEANINGFUL changes only.
        
        Compare these two snapshots:

        OLD:
        {old}

        NEW:
        {new}

        IMPORTANT: Only detect changes in actual VALUES/CONTENT, not formatting, phrasing, or structural differences.
        
        Guidelines for comparison:
        - Focus on factual data: numbers, quantities, statuses, dates, availability
        - Ignore formatting differences (JSON vs text, different wording for same info)
        - Ignore additional context or explanatory text that doesn't change core meaning
        - Consider the semantic meaning, not literal text matching
        
        Examples of NO CHANGE:
        - "Price: $100" vs "$100.00" = NO CHANGE (same value, different format)
        - "Available" vs "Available (Yes)" = NO CHANGE (same status, extra context)
        - "In stock: 5" vs "{{quantity: 5}}" = NO CHANGE (same data, different structure)
        - "Updated today" vs "Last updated: today" = NO CHANGE (same information)
        
        Examples of CHANGE:
        - "$100" vs "$120" = CHANGE (value increased)
        - "Available" vs "Out of stock" = CHANGE (status changed)
        - "5 items" vs "3 items" = CHANGE (quantity decreased)
        - "Open Mon-Fri" vs "Open Mon-Sun" = CHANGE (schedule expanded)

        Return:
        - is_change: true ONLY if core factual information changed
        - summary: explain what factual information changed (be specific about the change)
    """

    analysis: ChangeAnalysis = structured_llm.invoke(prompt.format(old=old, new=new))

    return {"is_change": analysis.is_change, "alert": analysis.summary}

def notifier_agent(state: AlertState) -> AlertState:
    print("ALERT:", state["alert"])  # swap with email/Slack in future
    return state

workflow = StateGraph(AlertState)
workflow.add_node("scraper", scraper_agent)
workflow.add_node("save_snapshot", save_snapshot_agent)
workflow.add_node("load_snapshot", load_snapshot_agent)
workflow.add_node("notifier", notifier_agent)

workflow.set_entry_point("scraper")

workflow.add_conditional_edges(
    "scraper",
    lambda state: state["mode"],
    {"add": "save_snapshot", "check": "load_snapshot"},
)

workflow.add_edge("save_snapshot", END)
workflow.add_node("analyze_changes", analyze_changes_agent)
workflow.add_edge("load_snapshot", "analyze_changes")
workflow.add_edge("analyze_changes", "notifier")
workflow.add_edge("notifier", END)

track_agent = workflow.compile()

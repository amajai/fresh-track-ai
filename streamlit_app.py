import streamlit as st
import json
import os
from agent import track_agent
from utils import get_today_str

# Page config
st.set_page_config(
    page_title="FreshTrack AI",
    page_icon="🔔",
    layout="wide"
)

st.markdown("""
<div style='
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
'>
    <h3 style='color: white; margin: 0; font-size: 3rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.3);'>
        🔔 FreshTrack AI
    </h3>
    <h5 style='color: #f0f0f0; margin: 0.5rem 0 0 0; font-style: italic; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);'>
        Intelligent web monitoring powered by AI Agent
    </h5>
</div>
""", unsafe_allow_html=True)

# Sidebar for history
with st.sidebar:
    st.header("📊 Snapshot History")
    
    # Load and display snapshots
    snapshot_file = "snapshots.json"
    if os.path.exists(snapshot_file):
        try:
            with open(snapshot_file, "r") as f:
                snapshots = json.load(f)
            
            if snapshots:
                st.write(f"**Total snapshots:** {len(snapshots)}")
                
                for url_key, snapshot_data in snapshots.items():
                    with st.expander(f"🌐 {url_key[:30]}..."):
                        if isinstance(snapshot_data, dict) and "date" in snapshot_data:
                            st.write(f"**Date:** {snapshot_data['date']}")
                            if isinstance(snapshot_data['data'], str):
                                st.text_area("Data", snapshot_data['data'][:100] + "...", height=40, disabled=True, key=f"snapshot_{hash(url_key)}")
                            else:
                                st.json(snapshot_data['data'])
                        else:
                            st.text("Legacy snapshot format")
            else:
                st.info("No snapshots yet")
        except Exception as e:
            st.error(f"Error loading snapshots: {e}")
    else:
        st.info("No snapshots file found")
    
    if os.path.exists(snapshot_file):
        try:
            with open(snapshot_file, "r") as f:
                snapshots = json.load(f)
            st.metric("Monitored Sites", len(snapshots))
        except:
            st.metric("Monitored Sites", "Error")
    else:
        st.metric("Monitored Sites", 0)

# Main content - full width
with st.container():
    st.header("🌐 Website Monitor")
    
    # Input form
    with st.form("monitoring_form"):
        url = st.text_input(
            "Website URL", 
            help="Enter the URL you want to monitor"
        )
        
        prompt = st.text_area(
            "Scraping Instructions", 
            height=80,
            help="Describe what information you want to extract from the website"
        )
        
        mode = st.radio(
            "Operation Mode",
            options=["add", "check"],
            format_func=lambda x: "🆕 Add Baseline" if x == "add" else "🔍 Check Changes",
            help="Add: Save current state as baseline. Check: Compare with existing baseline"
        )
        
        submitted = st.form_submit_button("🚀 Run Monitor", use_container_width=True)

    # Results section
    if submitted:
        if not url.strip():
            st.error("Please enter a valid URL")
        elif not prompt.strip():
            st.error("Please enter scraping instructions")
        else:
            with st.spinner("🤖 Agent is working..."):
                try:
                    # Create proper state format
                    test_state = {
                        "url": url.strip(),
                        "prompt": prompt.strip(),
                        "mode": mode
                    }
                    
                    result = track_agent.invoke(test_state)
                    
                    # Display results
                    st.success("✅ Monitoring completed!")
                    
                    # Alert section
                    if result.get("alert"):
                        if result.get("is_change", False):
                            st.error(f"🚨 **Change Detected!** {result['alert']}")
                        else:
                            st.info(f"ℹ️ **Status:** {result['alert']}")
                    
                    # Content display
                    if result.get("new_content"):
                        st.subheader("📄 Scraped Content")
                        if isinstance(result["new_content"], str):
                            st.text_area("Content", result["new_content"], height=150, disabled=True)
                        else:
                            st.json(result["new_content"])
                    
                    # Additional info
                    with st.expander("🔍 Detailed Results"):
                        st.json(result)
                        
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    st.exception(e)

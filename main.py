from agent import track_agent

def main():
    test_state = {
        "url": "https://www.jumia.com.ng/ecoflow-delta-2-220w-solar-panel-solar-g-enerator-bundle-with-1-3kwh-expandable-capacity-410273316.html",
        "prompt": "Extract the current price and name of item",
        "mode": "check",
    }
    
    print("Starting agent test run...")
    result = track_agent.invoke(test_state)
    print("Agent completed successfully!")
    print(f"Final state: {result}")
    
    # Show key results
    if "new_content" in result and result["new_content"]:
        print(f"\nScraped content: {result['new_content']}")
    if "alert" in result and result["alert"]:
        print(f"\nAlert generated: {result['alert']}")


if __name__ == '__main__':
    main()
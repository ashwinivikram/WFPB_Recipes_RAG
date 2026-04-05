import time
import requests
import argparse

def measure_request(url, query, session_id="test_session"):
    print(f"\n--- Query: '{query}' ---")
    start = time.time()
    payload = {"query": query, "session_id": session_id}
    try:
        resp = requests.post(f"{url}/query", json=payload)
        resp.raise_for_status()
        data = resp.json()
        duration = time.time() - start
        
        print(f"Time: {duration:.3f}s")
        print(f"Source: {data.get('source')}")
        print(f"Type: {data.get('query_type')}")
        print(f"Rewritten: {data.get('rewritten_query')}")
        print(f"Answer snippet: {data.get('answer', '')[:100]}...\n")
        return data
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the RAG application")
    args = parser.parse_args()

    print(f"Testing against {args.url}")
    print("Waiting for server to be healthy...")
    
    retries = 0
    while retries < 15:
        try:
            r = requests.get(f"{args.url}/health")
            if r.status_code == 200:
                print("Server is healthy!\n")
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(2)
        retries += 1
    else:
        print("Could not connect to server.")
        return

    # 1. Routing & Initial query
    print("Test 1: Routing & Base Query (HOW_TO)")
    measure_request(args.url, "How do I make the Ezekiel Sandwich?", session_id="session1")

    # 2. Caching check
    print("Test 2: Semantic Caching Hit")
    measure_request(args.url, "How do I make the Ezekiel Sandwich?", session_id="session1")

    # 3. Conversation memory check
    print("Test 3: Conversation Memory (Follow-up)")
    measure_request(args.url, "What about using gluten-free bread for it?", session_id="session1")

    # 4. Another query type
    print("Test 4: Routing (PLAN)")
    measure_request(args.url, "Plan a 2-day lunch meal plan for me.", session_id="session2")

if __name__ == "__main__":
    main()

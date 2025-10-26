from langchain_google_genai import ChatGoogleGenerativeAI
import os

# Define agent personalities and ideas
agents = [
    {
        "name": f"Agent {i + 1}",
        "personality": f"Personality {i + 1}",
        "idea": f"Idea {i + 1}",
    }
    for i in range(16)
]

# Create LLM class
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=1.0,
    max_retries=2,
    google_api_key=os.environ.get("GOOGLE_API_KEY"),
)

# Bind tools to the model
model = llm.bind_tools([])


# Simulate hackathon conversations
def simulate_hackathon(agents, turns=5):
    token_usage = 0
    conversation_log = []

    for turn in range(1, turns + 1):
        print(f"--- Turn {turn} ---")
        turn_log = {"turn": turn, "interactions": []}
        for agent in agents:
            prompt = (
                f"{agent['name']} with {agent['personality']} says: "
                f"My idea is {agent['idea']}. What do you think?"
            )
            response = model.invoke(prompt)
            print(f"{agent['name']} received response: {response}")
            token_usage += len(prompt.split()) + response.additional_kwargs.get(
                "usage_metadata", {}
            ).get("total_tokens", 0)
            turn_log["interactions"].append(
                {"agent": agent["name"], "prompt": prompt, "response": response}
            )
        conversation_log.append(turn_log)
        print("\n")

    # Summarize results
    print("--- Simulation Summary ---")
    for turn_log in conversation_log:
        print(f"Turn {turn_log['turn']}:")
        for interaction in turn_log["interactions"]:
            print(f"{interaction['agent']} -> {interaction['response']}")
    print(f"Total token usage: {token_usage}")


# Run the simulation
simulate_hackathon(agents, turns=5)

import sys
from flow import create_agent_flow

def main():
   
    
    default_question = "Who won the Nobel Prize in Physics 2024?"
    
   
    question = default_question
    for arg in sys.argv[1:]:
        if arg.startswith("--"):
            question = arg[2:]
            break
    
   
    agent_flow = create_agent_flow()
    
   
    shared = {"question": question}
    print(f"🤔 Processing question: {question}")
    agent_flow.run(shared)
    print("\n🎯 Final Answer:")
    print(shared.get("answer", "No answer found"))

if __name__ == "__main__":
    main()
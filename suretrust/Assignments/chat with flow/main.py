from pocketflow import Node, Flow
from utils import call_llm

class ChatNode(Node):
    def prep(self, shared):
      
        if "messages" not in shared:
            shared["messages"] = []
            print("Welcome to the chat! Type 'exit' to end the conversation.")
        
     
        user_input = input("\nYou: ")
        
      
        if user_input.lower() == 'exit':
            return None
        
       
        shared["messages"].append({"role": "user", "content": user_input})
        
      
        return shared["messages"]

    def exec(self, messages):
        if messages is None:
            return None
        

        response = call_llm(messages)
        return response

    def post(self, shared, prep_res, exec_res):
        if prep_res is None or exec_res is None:
            print("\nGoodbye!")
            return None  
        
        
        print(f"\nAssistant: {exec_res}")
        
      
        shared["messages"].append({"role": "assistant", "content": exec_res})
        
        
        return "continue"


chat_node = ChatNode()
chat_node - "continue" >> chat_node 

flow = Flow(start=chat_node)


if __name__ == "__main__":
    shared = {}
    flow.run(shared)
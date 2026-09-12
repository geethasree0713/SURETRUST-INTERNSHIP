from pocketflow import Node
from utils import call_llm, search_web_duckduckgo
import yaml
import re

class DecideAction(Node):
    def prep(self, shared):
        
        context = shared.get("context", "No previous search")
       
        question = shared["question"]
       
        return question, context
        
    def exec(self, inputs):
        
        question, context = inputs
        
        print(f"🤔 Agent deciding what to do next...")
        
       
        prompt = f"""
### CONTEXT
You are a research assistant that can search the web.
Question: {question}
Previous Research: {context}

### ACTION SPACE
[1] search
  Description: Look up more information on the web
  Parameters:
    - query (str): What to search for

[2] answer
  Description: Answer the question with current knowledge
  Parameters:
    - answer (str): Final answer to the question

## NEXT ACTION
Decide the next action based on the context and available actions.
Return your response in this format:

```yaml
thinking: |
    <your step-by-step reasoning process>
action: search OR answer
reason: |
    <why you chose this action - always use block scalar>
answer: |
    <if action is answer - always use block scalar, leave empty if searching>
search_query: <specific search query if action is search (plain string)>
```
IMPORTANT: Make sure to:
1. ALWAYS use the | block scalar for thinking, reason and answer so colons or quotes inside the text do not break YAML.
2. Use proper indentation (4 spaces) for all multi-line fields under |.
3. Keep search_query as a single line string without the | character.
"""
        
        
        response = call_llm(prompt)
        
       
        def extract_yaml_block(text):
           
            match = re.search(r"```yaml(.*?)```", text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
            return text.strip()

        def parse_yaml_safely(block):
           
            try:
                return yaml.safe_load(block)
            except yaml.YAMLError:
                fixed_lines = []
                for line in block.splitlines():
                    if re.match(r"^(thinking|reason|answer|search_query):", line) and "|" not in line:
                        key, _, val = line.partition(":")
                        fixed_lines.append(f"{key}: |")
                        val = val.strip()
                        if val:
                            fixed_lines.append(f"  {val}")
                    else:
                        fixed_lines.append(line)
                fixed_block = "\n".join(fixed_lines)
                try:
                    return yaml.safe_load(fixed_block)
                except yaml.YAMLError as exc:
                    raise ValueError(f"Unable to parse LLM YAML response:\n{block}") from exc

        yaml_str = extract_yaml_block(response)
        decision = parse_yaml_safely(yaml_str)
        
        return decision
    
    def post(self, shared, prep_res, exec_res):
       
        if exec_res["action"] == "search":
            shared["search_query"] = exec_res["search_query"]
            print(f"🔍 Agent decided to search for: {exec_res['search_query']}")
        else:
            print(f"💡 Agent decided to answer the question")
        
    
        return exec_res["action"]

class SearchWeb(Node):
    def prep(self, shared):
        """Get the search query from the shared store."""
        return shared["search_query"]
        
    def exec(self, search_query):
      
        print(f"🌐 Searching the web for: {search_query}")
        results = search_web_duckduckgo(search_query)
        return results
    
    def post(self, shared, prep_res, exec_res):
       
        
        previous = shared.get("context", "")
        shared["context"] = previous + "\n\nSEARCH: " + shared["search_query"] + "\nRESULTS: " + exec_res
        
        print(f"📚 Found information, analyzing results...")
        
        
        return "decide"

class AnswerQuestion(Node):
    def prep(self, shared):
       
        return shared["question"], shared.get("context", "")
        
    def exec(self, inputs):
       
        question, context = inputs
        
        print(f"✍️ Crafting final answer...")
       
        prompt = f"""
### CONTEXT
Based on the following information, answer the question.
Question: {question}
Research: {context}

## YOUR ANSWER:
Provide a comprehensive answer using the research results.
"""
       
        answer = call_llm(prompt)
        return answer
    
    def post(self, shared, prep_res, exec_res):
        
        shared["answer"] = exec_res
        
        print(f"✅ Answer generated successfully")
        
      
        return "done" 
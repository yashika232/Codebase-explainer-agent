import os
import json
import re
import asyncio
from typing import Dict, Any, List
from anthropic import Anthropic
from repo_explainer.evaluator import evaluate_agent
from repo_explainer.agent import DEFAULT_SYSTEM_PROMPT

class PromptOptimizer:
    """
    Implements a prompt optimization loop (meta-prompting).
    It runs evaluations, parses feedback, and prompts a Meta-LLM (Claude Haiku)
    to write a better system prompt, showing before/after score improvements.
    """
    def __init__(self, api_key: str, model: str = "claude-3-5-haiku-20241022"):
        self.api_key = api_key
        self.model = model
        if api_key != "mock":
            self.client = Anthropic(api_key=api_key)

    def generate_optimized_prompt(
        self,
        current_prompt: str,
        eval_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Uses Claude Haiku to analyze evaluation failure logs and output a refined system prompt.
        Or returns mock prompts if in mock mode.
        """
        if self.api_key == "mock":
            return {
                "analysis": "Mock analysis: The agent is missing exact file paths and internal functions in its explanation. Rewriting prompt to force checking codebase file paths systematically and calling Glob and Grep before forming responses.",
                "new_system_prompt": """You are a highly capable Repo Explainer Agent.
Instructions for systematic codebase mapping:
1. Always use Glob and Grep to identify target files (e.g. hashing.py, middleware.py).
2. Use Read tool to study their implementation in detail.
3. In your explanation, highlight exact functions, structures, and parameters."""
            }

        # Formulate logs for the Meta-LLM
        logs = []
        for res in eval_results["detailed_results"]:
            logs.append(f"""--- Test Case: {res['test_case']} ---
Scores:
- Completeness: {res['completeness']:.2f}
- Accuracy: {res['accuracy']:.2f}
- Conciseness: {res['conciseness']:.2f}
Grader Feedback:
{res['feedback']}
Agent Output:
{res['agent_output']}
""")
        
        formatted_logs = "\n".join(logs)
        
        prompt = f"""You are a Meta-LLM Prompt Optimizer.
Your job is to analyze the performance of a Repository Explainer Agent and optimize its system prompt to achieve a higher score.

Current System Prompt:
```markdown
{current_prompt}
```

Evaluation Results Summary:
- Global Score (average of completeness, accuracy, conciseness): {eval_results['global_score']:.2f}
- Completeness Score: {eval_results['metrics']['completeness']:.2f}
- Accuracy Score: {eval_results['metrics']['accuracy']:.2f}
- Conciseness Score: {eval_results['metrics']['conciseness']:.2f}

Detailed Logs & Feedback:
{formatted_logs}

Analyze what instructions in the current system prompt are lacking. Then, rewrite the system prompt to:
1. Address the grader's feedback (e.g. if the agent is missing key details or failing to locate files properly).
2. Explicitly guide the agent on how to use Read, Grep, and Glob tools systematically to discover components.
3. Keep the output clean, structured, and accurate.

Provide your output as a valid JSON object. Do not wrap the JSON block in extra explanations or text.

Format:
{{
  "analysis": "<short assessment of failure reasons and optimization ideas>",
  "new_system_prompt": "<the updated full system prompt for the agent>"
}}
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.4,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip()
            
            # Extract JSON block using regex if any text wrapping exists
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                return {
                    "analysis": parsed.get("analysis", ""),
                    "new_system_prompt": parsed.get("new_system_prompt", current_prompt)
                }
            else:
                return {"error": "Failed to parse prompt optimization output", "raw": text}
        except Exception as e:
            return {"error": str(e)}


async def run_optimizer(
    iterations: int = 2,
    verbose: bool = True,
    model: str = "claude-3-5-haiku-20241022",
    mock: bool = False
) -> Dict[str, Any]:
    """
    Executes the optimization loop:
    1. Evaluates baseline prompt.
    2. Runs optimizer iteration: Meta-LLM writes new prompt -> evaluates it.
    3. Keeps new prompt if it scores higher.
    4. Repeats for requested iterations.
    """
    api_key = "mock" if mock else os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
        
    optimizer = PromptOptimizer(api_key=api_key, model=model)
    
    current_prompt = DEFAULT_SYSTEM_PROMPT
    if verbose:
        print("=== Iteration 0 (Baseline Evaluation) ===")
        
    best_results = await evaluate_agent(current_prompt, verbose=verbose, model=model, mock=mock)
    best_score = best_results["global_score"]
    best_prompt = current_prompt
    
    history = [{
        "iteration": 0,
        "prompt": current_prompt,
        "score": best_score,
        "metrics": best_results["metrics"]
    }]
    
    if verbose:
        print(f"Baseline Global Score: {best_score:.4f}")
        print(f"Metrics: {best_results['metrics']}")
        
    for it in range(1, iterations + 1):
        if verbose:
            print(f"\n=== Iteration {it} (Optimizing Prompt) ===")
            print("Invoking Meta-Optimizer LLM...")
            
        opt_res = optimizer.generate_optimized_prompt(current_prompt, best_results)
        
        if "error" in opt_res:
            if verbose:
                print(f"Optimization generation error: {opt_res['error']}")
            break
            
        new_prompt = opt_res["new_system_prompt"]
        analysis = opt_res["analysis"]
        
        if verbose:
            print(f"Meta-LLM Analysis:\n{analysis}\n")
            print("Evaluating new prompt...")
            
        new_results = await evaluate_agent(new_prompt, verbose=verbose, model=model, mock=mock)
        new_score = new_results["global_score"]
        
        if verbose:
            print(f"Iteration {it} Score: {new_score:.4f} (vs Best: {best_score:.4f})")
            print(f"Metrics: {new_results['metrics']}")
            
        history.append({
            "iteration": it,
            "prompt": new_prompt,
            "score": new_score,
            "metrics": new_results["metrics"],
            "analysis": analysis
        })
        
        if new_score > best_score:
            if verbose:
                print(f"Score improved! Adopting new system prompt.")
            best_score = new_score
            best_prompt = new_prompt
            best_results = new_results
        else:
            if verbose:
                print(f"Score did not improve. Keeping previous best system prompt.")
                
        current_prompt = new_prompt  # Iterate on the latest prompt regardless of strict improvement
        
    return {
        "best_prompt": best_prompt,
        "best_score": best_score,
        "baseline_score": history[0]["score"],
        "history": history
    }


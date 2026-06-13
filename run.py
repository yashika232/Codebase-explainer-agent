import os
import sys
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add current directory to path so imports work out-of-the-box
sys.path.append(str(Path(__file__).parent.absolute()))

from repo_explainer.agent import run_explainer, explain_repo_text, DEFAULT_SYSTEM_PROMPT
from repo_explainer.evaluator import evaluate_agent
from repo_explainer.optimizer import run_optimizer
from repo_explainer.utils import get_repo_structure

# Load environment variables from .env file if present
load_dotenv()

def check_api_key():
    """Checks if the Anthropic API key is present."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n[Error] ANTHROPIC_API_KEY environment variable is not set.", file=sys.stderr)
        print("Please set it in your environment or create a '.env' file in this directory.", file=sys.stderr)
        print("Example: ANTHROPIC_API_KEY=your-api-key-here\n", file=sys.stderr)
        sys.exit(1)

def print_message_stream(msg):
    """
    Prints streaming assistant blocks and tool usage status.
    """
    msg_type = type(msg).__name__
    if msg_type == "AssistantMessage":
        for block in getattr(msg, "content", []):
            block_type = type(block).__name__
            if block_type == "TextBlock":
                print(getattr(block, "text", ""), end="", flush=True)
            elif block_type == "ThinkingBlock":
                # Print thinking in gray or bracketed format
                thinking_text = getattr(block, "thinking", "") or getattr(block, "text", "")
                if thinking_text:
                    print(f"\n[Thinking: {thinking_text.strip()}]\n", end="", flush=True)
            elif block_type == "ToolUseBlock":
                name = getattr(block, "name", "unknown")
                args = getattr(block, "input", {})
                print(f"\n[Agent Tool Call: {name} with args={args}]\n", end="", flush=True)
    elif msg_type == "ToolResultMessage":
        # Can print tool results if verbose, but let's keep it clean
        pass

async def handle_explain(args):
    check_api_key()
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        print(f"[Error] Repository path '{args.repo_path}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)
        
    print(f"=== Mapping codebase: {repo_path.name} ===")
    structure = get_repo_structure(repo_path)
    print("Codebase Directory Tree:")
    print(structure)
    print("-" * 50)
    print(f"Question: {args.question}")
    print("Streaming Agent Response:")
    print("-" * 50)
    
    system_prompt = DEFAULT_SYSTEM_PROMPT
    if args.prompt_file:
        prompt_path = Path(args.prompt_file).resolve()
        if not prompt_path.exists():
            print(f"[Error] Prompt file '{args.prompt_file}' not found.", file=sys.stderr)
            sys.exit(1)
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
            
    try:
        async for msg in run_explainer(
            repo_path=str(repo_path),
            question=args.question,
            system_prompt=system_prompt,
            model=args.model,
            max_turns=args.max_turns
        ):
            print_message_stream(msg)
        print("\n" + "=" * 50)
    except Exception as e:
        print(f"\n[Agent Execution Error] {e}", file=sys.stderr)
        sys.exit(1)

async def handle_evaluate(args):
    if not args.mock:
        check_api_key()
    print("=== Running Evaluation Harness ===")
    if args.mock:
        print("[Running in Mock Mode - No API calls made]")
    system_prompt = DEFAULT_SYSTEM_PROMPT
    if args.prompt_file:
        prompt_path = Path(args.prompt_file).resolve()
        if not prompt_path.exists():
            print(f"[Error] Prompt file '{args.prompt_file}' not found.", file=sys.stderr)
            sys.exit(1)
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
            
    results = await evaluate_agent(
        system_prompt=system_prompt,
        verbose=True,
        model=args.model,
        mock=args.mock
    )
    
    print("\n" + "=" * 50)
    print("EVALUATION COMPLETED SUCCESSFULLY")
    print("=" * 50)
    print(f"Global Score: {results['global_score']:.4f}")
    print(f"Metrics: {results['metrics']}")
    print("-" * 50)
    for i, res in enumerate(results["detailed_results"]):
        print(f"Test Case {i+1}: {res['test_case']}")
        print(f"  Scores -> Completeness: {res['completeness']:.2f}, Accuracy: {res['accuracy']:.2f}, Conciseness: {res['conciseness']:.2f}")
        print(f"  Feedback: {res['feedback']}")
        print("-" * 50)

async def handle_optimize(args):
    if not args.mock:
        check_api_key()
    print("=== Running Prompt Optimizer Loop ===")
    if args.mock:
        print("[Running in Mock Mode - No API calls made]")
    print(f"Iterations: {args.iterations}")
    print(f"Model: {args.model}")
    print("-" * 50)
    
    res = await run_optimizer(
        iterations=args.iterations,
        verbose=True,
        model=args.model,
        mock=args.mock
    )
    
    print("\n" + "=" * 50)
    print("OPTIMIZATION COMPLETED SUCCESSFULLY")
    print("=" * 50)
    print(f"Baseline Global Score: {res['baseline_score']:.4f}")
    print(f"Optimized Global Score: {res['best_score']:.4f}")
    print(f"Score Improvement: {res['best_score'] - res['baseline_score']:.4f}")
    print("-" * 50)
    print("Best Optimized Prompt:")
    print("-" * 50)
    print(res["best_prompt"])
    print("-" * 50)
    
    # Save optimized prompt to file
    out_path = Path(args.output_file).resolve()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(res["best_prompt"])
    print(f"Saved optimized system prompt to: {out_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Proptimise AI - Repo Explainer Agent CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Command: explain
    explain_parser = subparsers.add_parser("explain", help="Run the Repo Explainer Agent on a local codebase")
    explain_parser.add_argument("repo_path", help="Path to local repository to explain")
    explain_parser.add_argument("question", help="Question to ask the agent about the repo")
    explain_parser.add_argument("--prompt-file", help="Path to text file containing a custom system prompt")
    explain_parser.add_argument("--model", default="claude-3-5-haiku-20241022", help="Anthropic Claude model to use")
    explain_parser.add_argument("--max-turns", type=int, default=15, help="Maximum agent turns")
    
    # Command: evaluate
    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate the agent against the mock codebase evaluation suite")
    evaluate_parser.add_argument("--prompt-file", help="Path to custom system prompt file to evaluate")
    evaluate_parser.add_argument("--model", default="claude-3-5-haiku-20241022", help="Anthropic Claude model to use")
    evaluate_parser.add_argument("--mock", action="store_true", help="Run evaluation using mock grader/agent simulation")
    
    # Command: optimize
    optimize_parser = subparsers.add_parser("optimize", help="Iteratively optimize the agent's system prompt using evaluations")
    optimize_parser.add_argument("--iterations", type=int, default=2, help="Number of optimization loop rounds")
    optimize_parser.add_argument("--model", default="claude-3-5-haiku-20241022", help="Anthropic Claude model to use")
    optimize_parser.add_argument("--output-file", default="optimized_prompt.txt", help="Output file to save the optimized system prompt")
    optimize_parser.add_argument("--mock", action="store_true", help="Run optimizer using mock grader/agent simulation")
    
    args = parser.parse_args()
    
    # Run async commands
    if args.command == "explain":
        asyncio.run(handle_explain(args))
    elif args.command == "evaluate":
        asyncio.run(handle_evaluate(args))
    elif args.command == "optimize":
        asyncio.run(handle_optimize(args))

if __name__ == "__main__":
    main()


import os
import shutil
import tempfile
import json
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Tuple
from anthropic import Anthropic
from repo_explainer.agent import explain_repo_text

# Define Mock Repositories
def setup_auth_repo(base_path: Path):
    """
    Creates a mock Flask Authentication repository.
    """
    (base_path / "src" / "auth").mkdir(parents=True, exist_ok=True)
    (base_path / "src" / "app").mkdir(parents=True, exist_ok=True)
    (base_path / "config").mkdir(parents=True, exist_ok=True)
    
    # 1. config/settings.py
    with open(base_path / "config" / "settings.py", "w", encoding="utf-8") as f:
        f.write('''# App Settings
JWT_SECRET_KEY = "super-secret-key-do-not-share"
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRATION_HOURS = 24
BCRYPT_ROUNDS = 12
''')

    # 2. src/auth/hashing.py
    with open(base_path / "src" / "auth" / "hashing.py", "w", encoding="utf-8") as f:
        f.write('''# Password Hashing Utilities
import bcrypt

def hash_password(password: str) -> str:
    """Hashes a plain text password using bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verifies a plain text password against the stored bcrypt hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
''')

    # 3. src/auth/middleware.py
    with open(base_path / "src" / "auth" / "middleware.py", "w", encoding="utf-8") as f:
        f.write('''# Auth Middleware
import jwt
from datetime import datetime
from config.settings import JWT_SECRET_KEY, JWT_ALGORITHM

def decode_token(token: str) -> dict:
    """Decodes JWT token. Returns user payload or raises error."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token signature has expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid JWT token")

def require_auth(request_headers: dict) -> dict:
    """Checks for Authorization header and validates JWT."""
    auth_header = request_headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise PermissionError("Authorization header is missing or malformed")
    
    token = auth_header.split(" ")[1]
    return decode_token(token)
''')

    # 4. src/app/main.py
    with open(base_path / "src" / "app" / "main.py", "w", encoding="utf-8") as f:
        f.write('''# Flask Authentication Routes Entrypoint
from flask import Flask, request, jsonify
from src.auth.hashing import hash_password, verify_password
from src.auth.middleware import require_auth

app = Flask(__name__)

# Mock database
USERS_DB = {}

@app.route("/register", methods=["POST"])
def register():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return jsonify({"error": "Missing credentials"}), 400
    
    USERS_DB[username] = hash_password(password)
    return jsonify({"message": f"User {username} registered successfully"}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    
    hashed = USERS_DB.get(username)
    if not hashed or not verify_password(password, hashed):
        return jsonify({"error": "Unauthorized"}), 401
        
    return jsonify({"token": f"mocked-jwt-token-for-{username}"}), 200

@app.route("/dashboard", methods=["GET"])
def dashboard():
    try:
        user_info = require_auth(request.headers)
        return jsonify({"message": f"Welcome to dashboard, {user_info.get('username')}"}), 200
    except (PermissionError, ValueError) as e:
        return jsonify({"error": str(e)}), 403
''')


def setup_math_repo(base_path: Path):
    """
    Creates a mock Math CLI Tool repository.
    """
    (base_path / "src" / "core").mkdir(parents=True, exist_ok=True)
    (base_path / "src" / "cli").mkdir(parents=True, exist_ok=True)
    
    # 1. src/core/calculator.py
    with open(base_path / "src" / "core" / "calculator.py", "w", encoding="utf-8") as f:
        f.write('''# Standard mathematical operations
def add(a: float, b: float) -> float:
    return a + b

def subtract(a: float, b: float) -> float:
    return a - b

def multiply(a: float, b: float) -> float:
    return a * b

def divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
''')

    # 2. src/core/fibonacci.py
    with open(base_path / "src" / "core" / "fibonacci.py", "w", encoding="utf-8") as f:
        f.write('''# Fibonacci Sequence calculation with optimization
_FIB_CACHE = {0: 0, 1: 1}

def get_fibonacci(n: int) -> int:
    """
    Calculates the nth Fibonacci number using a global cache to optimize execution.
    Raises ValueError for negative inputs.
    """
    if n < 0:
        raise ValueError("Fibonacci is undefined for negative numbers.")
    if n in _FIB_CACHE:
        return _FIB_CACHE[n]
        
    # Recursive calculation with memoization cache fill
    result = get_fibonacci(n - 1) + get_fibonacci(n - 2)
    _FIB_CACHE[n] = result
    return result

def clear_fib_cache():
    """Clears the global cache (resets to base cases)."""
    global _FIB_CACHE
    _FIB_CACHE = {0: 0, 1: 1}
''')

    # 3. src/cli/parser.py
    with open(base_path / "src" / "cli" / "parser.py", "w", encoding="utf-8") as f:
        f.write('''# CLI parsing config
import argparse

def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Math CLI tool")
    parser.add_argument("operation", choices=["add", "sub", "mul", "div", "fib"])
    parser.add_argument("--args", nargs="+", type=float, help="Arguments for math operation")
    parser.add_argument("--fib-n", type=int, help="N parameter for Fibonacci calculation")
    return parser
''')

    # 4. src/main.py
    with open(base_path / "src" / "main.py", "w", encoding="utf-8") as f:
        f.write('''# CLI Entrypoint
import sys
from src.cli.parser import create_parser
from src.core.calculator import add, subtract, multiply, divide
from src.core.fibonacci import get_fibonacci

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    if args.operation == "fib":
        if args.fib_n is None:
            print("Error: --fib-n required for fib operation", file=sys.stderr)
            sys.exit(1)
        res = get_fibonacci(args.fib_n)
        print(f"Fibonacci({args.fib_n}) = {res}")
    else:
        if not args.args or len(args.args) != 2:
            print("Error: operation requires exactly two numerical arguments passed to --args", file=sys.stderr)
            sys.exit(1)
        a, b = args.args[0], args.args[1]
        if args.operation == "add":
            print(f"Result = {add(a, b)}")
        elif args.operation == "sub":
            print(f"Result = {subtract(a, b)}")
        elif args.operation == "mul":
            print(f"Result = {multiply(a, b)}")
        elif args.operation == "div":
            try:
                print(f"Result = {divide(a, b)}")
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)

if __name__ == "__main__":
    main()
''')


# Evaluator harness representation
TEST_CASES = [
    {
        "id": "flask_auth",
        "name": "Flask Auth Explanation",
        "setup_func": setup_auth_repo,
        "query": "Explain how authentication works in this repository. Specifically answer: (1) what encryption is used for storing passwords and which file handles this? (2) where is the middleware logic verifying incoming request tokens and which file? (3) how does the dashboard route use auth verification?",
        "reference_answer": """
1. Passwords are encrypted using the bcrypt algorithm with salt. This logic is handled in `src/auth/hashing.py` (functions `hash_password` and `verify_password`).
2. Incoming request tokens are verified by decoding the JWT Token against a signature. The authorization checks the 'Authorization' header for a 'Bearer ' schema. This middleware logic resides in `src/auth/middleware.py` (specifically functions `decode_token` and `require_auth`).
3. The dashboard route in `src/app/main.py` uses auth verification by invoking the `require_auth` function, passing `request.headers` to it, and catching potential validation errors (`PermissionError` or `ValueError`) returning 403 if validation fails.
"""
    },
    {
        "id": "math_cli",
        "name": "Math CLI explanation",
        "setup_func": setup_math_repo,
        "query": "Answer: (1) What math operations are supported, and which file defines them? (2) Explain the Fibonacci implementation. Is there an optimization used and what file handles it? (3) What arguments are required to run the fibonacci operation via CLI?",
        "reference_answer": """
1. The supported math operations are add, subtract, multiply, and divide (raising ValueError for division by zero). These functions are defined in `src/core/calculator.py`.
2. The Fibonacci implementation calculates numbers using a recursive method. It utilizes a global dictionary `_FIB_CACHE` to memoize previously computed results to optimize performance (caching). This is implemented in `src/core/fibonacci.py`.
3. To run the fibonacci operation via CLI, you must provide the 'fib' operation argument and the '--fib-n' flag with an integer value (defined in `src/cli/parser.py` and run in `src/main.py`).
"""
    }
]


class LLMGrader:
    """
    Grades the agent explanation output using Claude Haiku against reference answers.
    Supports mock grading when api_key is 'mock'.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        if api_key != "mock":
            self.client = Anthropic(api_key=api_key)

    def grade(self, query_text: str, agent_output: str, reference_answer: str) -> Dict[str, Any]:
        """
        Invokes Claude Haiku to compare agent explanation with reference and grade it.
        Or returns mock scores if in mock mode.
        """
        if self.api_key == "mock":
            # Determine score based on if the answer is optimized (longer/contains details)
            is_optimized = "hashing.py" in agent_output and "middleware.py" in agent_output or "fibonacci.py" in agent_output and "_FIB_CACHE" in agent_output
            if is_optimized:
                return {
                    "completeness": 0.95,
                    "accuracy": 0.96,
                    "conciseness": 0.92,
                    "feedback": "Mock evaluation: Excellent coverage, identified all file paths, functions, and key caching mechanisms correctly."
                }
            else:
                return {
                    "completeness": 0.68,
                    "accuracy": 0.72,
                    "conciseness": 0.78,
                    "feedback": "Mock evaluation: Covered general flow but missed specific file mappings (e.g. hashing.py, middleware.py) and detailed cache structures."
                }

        prompt = f"""You are an expert evaluator assessing the performance of a Repository Explainer Agent.
Your job is to compare the agent's explanation output against the reference answer and assign scoring metrics.

User Query:
{query_text}

Agent's Generated Output:
{agent_output}

Reference Answer (Expected):
{reference_answer}

Evaluate the Agent's output across these three metrics:
1. completeness_score (0-100): Did the agent successfully cover all answers and mention the specific files, structures, and functions listed in the reference?
2. accuracy_score (0-100): Are the technical facts explained in the agent output correct and match the reference?
3. conciseness_score (0-100): Is the answer clear, readable, and structured without excessive filler, repetition, or irrelevant context?

Output your evaluation as a valid JSON object. Do not include any other markdown text, chat wrappers, or formatting outside the JSON codeblock.

Format:
{{
  "completeness_score": <int>,
  "accuracy_score": <int>,
  "conciseness_score": <int>,
  "feedback": "<detailed feedback describing what was missing or correct>"
}}
"""
        try:
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
                temperature=0.0,
                messages=[{"role": "user", "content": prompt}]
            )
            text = response.content[0].text.strip()
            
            # Extract JSON block using regex if any text wrapping exists
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                return {
                    "completeness": float(parsed.get("completeness_score", 0)) / 100.0,
                    "accuracy": float(parsed.get("accuracy_score", 0)) / 100.0,
                    "conciseness": float(parsed.get("conciseness_score", 0)) / 100.0,
                    "feedback": parsed.get("feedback", "No feedback provided.")
                }
            else:
                return {"error": "Failed to parse model JSON output", "raw": text}
        except Exception as e:
            return {"error": str(e)}


async def evaluate_agent(
    system_prompt: str,
    verbose: bool = True,
    model: str = "claude-3-5-haiku-20241022",
    mock: bool = False
) -> Dict[str, Any]:
    """
    Runs the full evaluation suite by generating mock codebases,
    executing the agent on them, grading output using LLM, and cleaning up.
    Supports mock mode when mock=True.
    """
    api_key = "mock" if mock else os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set.")
        
    grader = LLMGrader(api_key=api_key)
    results = []
    
    temp_dir = tempfile.mkdtemp(prefix="repo_explainer_eval_")
    temp_path = Path(temp_dir)
    
    if verbose:
        print(f"Creating evaluation sandbox at: {temp_dir}")
        
    try:
        for tc in TEST_CASES:
            case_id = tc["id"]
            case_name = tc["name"]
            setup_func = tc["setup_func"]
            query_text = tc["query"]
            ref_ans = tc["reference_answer"]
            
            # Prepare mock repo
            repo_path = temp_path / case_id
            repo_path.mkdir(parents=True, exist_ok=True)
            setup_func(repo_path)
            
            if verbose:
                print(f"\n--- Running Test Case: {case_name} ---")
                print(f"Query: {query_text}")
                
            # Run the agent (or return simulated outputs in mock mode)
            if mock:
                # Artificial delay to simulate thinking
                await asyncio.sleep(0.5)
                # Check if prompt looks optimized
                is_opt = "systematic" in system_prompt.lower()
                if case_id == "flask_auth":
                    if is_opt:
                        agent_output = "The repository implements bcrypt hashing for password storage in `src/auth/hashing.py`. The JWT authentication middleware logic is in `src/auth/middleware.py` which decodes token signature. The dashboard route in `src/app/main.py` calls `require_auth` with request headers and catches ValueError/PermissionError, returning a 403 status code if validation fails."
                    else:
                        agent_output = "This repository uses bcrypt for hashing passwords. The middleware token validation is in auth.py. The dashboard route checks require_auth."
                else:  # math_cli
                    if is_opt:
                        agent_output = "Supports add, sub, mul, div operations defined in `src/core/calculator.py` raising ValueError for zero division. Fibonacci sequence is recursively calculated in `src/core/fibonacci.py` with caching memoization in `_FIB_CACHE`. Run operations via CLI by passing the operation name (like fib) and the required arguments or --fib-n flag."
                    else:
                        agent_output = "Supports math operations. Fibonacci is in core. calculator.py has add/sub/mul/div. run it with operation and args."
            else:
                try:
                    # Limit turns to speed up evaluations
                    agent_output = await explain_repo_text(
                        repo_path=str(repo_path),
                        question=query_text,
                        system_prompt=system_prompt,
                        model=model,
                        max_turns=10
                    )
                except Exception as err:
                    agent_output = f"[Agent Execution Failed: {err}]"
                
            if verbose:
                print(f"Agent Output:\n{agent_output}\n")
                print("Grading agent output...")
                
            # Grade output
            grades = grader.grade(query_text, agent_output, ref_ans)
            
            if "error" in grades:
                print(f"Grader error: {grades['error']}")
                grades = {"completeness": 0.0, "accuracy": 0.0, "conciseness": 0.0, "feedback": f"Grader failed: {grades['error']}"}
                
            grades["test_case"] = case_name
            grades["agent_output"] = agent_output
            results.append(grades)
            
            if verbose:
                print(f"Scores -> Completeness: {grades['completeness']:.2f}, Accuracy: {grades['accuracy']:.2f}, Conciseness: {grades['conciseness']:.2f}")
                print(f"Feedback: {grades['feedback']}")
                
    finally:
        # Cleanup mock repositories
        if verbose:
            print(f"\nCleaning up evaluation sandbox...")
        shutil.rmtree(temp_dir)
        
    # Calculate aggregate scores
    count = len(results)
    avg_completeness = sum(r["completeness"] for r in results) / count if count > 0 else 0
    avg_accuracy = sum(r["accuracy"] for r in results) / count if count > 0 else 0
    avg_conciseness = sum(r["conciseness"] for r in results) / count if count > 0 else 0
    
    # Global score is the average of completeness and accuracy, penalizing lack of structure
    global_score = (avg_completeness + avg_accuracy + avg_conciseness) / 3.0
    
    summary = {
        "global_score": global_score,
        "metrics": {
            "completeness": avg_completeness,
            "accuracy": avg_accuracy,
            "conciseness": avg_conciseness
        },
        "detailed_results": results
    }
    
    return summary


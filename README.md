# Repo Explainer Agent & Optimizer Harness

This repository implements a production-grade **Repo Explainer Agent** built on **Anthropic's official Claude Agent SDK** for Python. It is designed to map codebase structures and answer complex architectural questions, backed by a robust **evaluation harness** and an **automated prompt optimizer harness**.

---

## 🏗️ Architecture & Three Pillars

<img width="1536" height="1024" alt="ChatGPT Image Jun 14, 2026, 01_22_54 AM" src="https://github.com/user-attachments/assets/c016bd4a-d265-4db2-a272-ae241cbd4e84" />
                                       Architecture diagram and overall flow 


                                       
This codebase is structured around the three pillars requested in the Proptimise AI challenge, designed to run locally with strict security boundaries.

### 🤖 1. The Working Agent (`repo_explainer/agent.py`)
The Repo Explainer Agent uses the `claude-agent-sdk` library to autonomously explore local codebases.
- **Stateful Navigation**: Leverages Claude's native agent loop (think, act, observe) to find relevant files instead of parsing the whole repo at once, saving massive context window tokens.
- **Built-in Security boundaries**: Disables write-actions and command execution (`Write`, `Edit`, `Bash` tools) to ensure it acts as a **strictly read-only analysis agent**. Only `Read`, `Grep`, and `Glob` tools are allowed.

### 📊 2. The Evaluation Harness (`repo_explainer/evaluator.py`)
To systematically measure explanation quality, we implement an automated evaluation suite:
- **Sandbox Codebase Generator**: Programmatically spins up isolated directories containing mock codebases representing different design patterns:
  - **`flask_auth`**: A Flask app with JWT token decoding middleware, token authentication validation, and bcrypt password hashing utilities.
  - **`math_cli`**: A command-line tool with core calculation functions and a recursive Fibonacci sequence implementation optimized with a global memoization cache.
- **LLM-Based Grader**: Evaluates the agent's generated answers against human-crafted reference ground-truths across three metrics (scored 0.0 to 1.0):
  - **Completeness**: Did the agent locate the exact files, functions, and algorithms mentioned in the reference?
  - **Accuracy**: Is the technical detail accurate relative to the code?
  - **Conciseness**: Is the explanation clean and readable without filler?

### ⚡ 3. The Optimizer Harness (`repo_explainer/optimizer.py`)
To move the needle and improve agent performance, we implement a **Meta-Prompting Optimizer**:
1. **Baseline Run**: Measures agent scores on the test suite using a default system prompt.
2. **Analysis Phase**: Feeds the current prompt, agent answers, scores, and grader feedback into a **Meta-Optimizer LLM** (Claude Haiku).
3. **Refinement Phase**: The Meta-LLM analyzes the agent's gaps, refines the system prompt to explicitly guide agent tool usage, and outputs the new system prompt.
4. **Re-Evaluation**: Evaluates the agent again on the new system prompt. If the average score improves, it adopts the new prompt.
5. **Report**: Compiles and outputs before/after metrics showing the exact gain.

---

## 🔒 Security Precautions & Edge Case Handling

1. **Strict Read-Only Sandboxing**: The agent is restricted to `Read`, `Grep`, and `Glob`. It **cannot execute shell commands** or modify files on your machine.
2. **Directory Jail (CWD Boundaries)**: By setting the `cwd` field in `ClaudeAgentOptions`, the SDK confines file actions relative to the target repository root, protecting system files.
3. **API Key Security**: The API key is loaded securely via `dotenv` and never logged or printed to stdout.
4. **Binary & Massive File Guard**: Uses exclusion filters (e.g. ignoring `.git`, `node_modules`, images, zips, compile artifacts) and truncates file reads at 50,000 characters to prevent token overflow.
5. **Path Normalization**: Validates repository paths and normalizes symlinks to prevent directory traversal attacks or infinite recursion loops.

---

## 🚀 Setup & Execution Guide

### 📋 Prerequisites
- **Python 3.10+** (Python 3.14 recommended/tested)
- **Anthropic API Key**

### 🔧 Installation
1. Clone the repository and navigate to the directory:
   ```bash
   cd repo_eval
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows (PowerShell):
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set your Anthropic API Key in the environment or create a `.env` file in the root directory:
   ```bash
   # In terminal:
   $env:ANTHROPIC_API_KEY="your-api-key-here"  # Windows PowerShell
   export ANTHROPIC_API_KEY="your-api-key-here" # Linux/macOS
   
   # Or create .env:
   echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
   ```

---

## 💻 CLI Commands

Run the main project entry point using the virtual environment's python.

### 1. Explain a local repository
Point the agent at any local folder and ask a question.
```bash
python run.py explain "path/to/local/codebase" "Explain the main entrypoint and how it coordinates components."
```

### 2. Run the Evaluation Suite
Evaluates the agent against the mock codebases using the default system prompt.
```bash
python run.py evaluate
```
*You can also evaluate a custom system prompt file:*
```bash
python run.py evaluate --prompt-file "optimized_prompt.txt"
```

### 3. Run the System Prompt Optimizer
Runs the prompt optimizer loop to improve agent performance using evaluations.
```bash
python run.py optimize --iterations 2 --output-file "optimized_prompt.txt"
```
Once completed, it will save the best system prompt to `optimized_prompt.txt`.

---

## 🧪 Unit Tests
Run standard pytest tests to verify local utilities, safe readers, and mock repo generation:
```bash
python -m pytest
```

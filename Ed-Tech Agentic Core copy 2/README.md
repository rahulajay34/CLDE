# Ed-Tech Agentic Core

This is the core implementation of an Agentic Workflow for Educational Content Generation. It utilizes a multi-agent system orchestrator (Creator, Auditor, Pedagogue, Editor) to generate high-quality lecture notes and assignments.

## Features

- **Multi-Agent Orchestration**: Sequential and parallel execution of specialized agents (Creator, Auditor, Pedagogue, Editor).
- **Asynchronous Architecture**: Fully async core using `asyncio` and `AnthropicAsync` client for high performance and responsiveness.
- **Real-Time Streaming**: Live content generation feedback with typewriter effects.
- **RAG Integration**: Retrieval Augmented Generation for grounding content in source transcripts.
- **Multi-Tenancy**: Session-based state management ensuring data isolation.
- **Security**: XSS protection and secure file handling.

## Prerequisites

- Python 3.9+
- Anthropic API Key (`ANTHROPIC_API_KEY`)

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   (Ensure `streamlit`, `anthropic`, `instructor`, `pandas`, `pydantic` are installed)

## Running the Application

1. Set your API key:
   ```bash
   export ANTHROPIC_API_KEY="your-api-key"
   ```
2. Run the Streamlit app:
   ```bash
   streamlit run app.py
   ```

## Architecture

- **`app.py`**: Entry point. Handles RAG initialization and main UI routing.
- **`core/orchestrator.py`**: The brain of the system. Manages the state machine and agent execution loop.
  - Now uses `async for` generators to stream events.
  - Supports parallel execution of critique agents.
- **`core/client.py`**: Asynchronous wrapper for Anthropic API with retry logic and streaming support.
- **`ui/`**: Clean separation of UI components (`components.py`) and views (`views.py`).
- **`storage/`**: Local persistence layer. JSON sessions and Markdown outputs.

## Usage

1. **Dashboard**: View recent projects.
2. **Editor**: Enter a topic, upload a transcript (optional), and click "Generate Draft".
3. **Refinement**: Agents will iteratively critique and improve the draft.
4. **Finalization**: The final output is saved to `storage/Lecture-Notes` or `storage/Assignments`.

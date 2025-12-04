# Multi-Agent Orchestration

> **Status**: WIP - Planning Phase

## Vision

Enable multiple AI backends (Claude, GPT, Gemini, Ollama, etc.) to work together on complex tasks. Each agent has a role and can orchestrate or be orchestrated by other agents.

Example workflow:
```
User Request: "Review this PR and suggest improvements"
    │
    ▼
┌─────────────┐
│   Claude    │  (Orchestrator - breaks down task)
│   Leader    │
└──────┬──────┘
       │
       ├──────────────────┐
       ▼                  ▼
┌─────────────┐    ┌─────────────┐
│   ChatGPT   │    │   Gemini    │
│   Coder     │    │  Reviewer   │
└──────┬──────┘    └──────┬──────┘
       │                  │
       ▼                  ▼
   Code fixes      Review notes
       │                  │
       └────────┬─────────┘
                ▼
┌─────────────────────────┐
│   Claude (Aggregator)   │
│   Synthesizes results   │
└─────────────────────────┘
                │
                ▼
          Final Response
```

---

## Architecture

### 1. Provider Layer

Abstract interface for AI backends:

```python
# app/providers/base.py
class BaseProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = None) -> str: ...

    @abstractmethod
    async def generate_stream(self, prompt: str, system_prompt: str = None) -> AsyncGenerator[str, None]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
```

**Providers to implement:**

| Provider | API | Priority |
|----------|-----|----------|
| `OllamaProvider` | Local/Self-hosted | ✅ Done |
| `AnthropicProvider` | Claude API | High |
| `OpenAIProvider` | GPT-4, GPT-3.5 | High |
| `GeminiProvider` | Google AI | Medium |
| `OpenRouterProvider` | Multi-model gateway | Medium |
| `GroqProvider` | Fast inference | Low |

### 2. Agent Registry

Store and manage configured agents:

```python
# Database model
class Agent(Base):
    id: UUID
    app_id: UUID  # belongs to an app
    name: str  # "claude-reviewer"
    provider_type: str  # "anthropic", "openai", etc.
    api_key_encrypted: str
    model: str  # "claude-3-opus", "gpt-4", etc.
    role: str  # "leader", "coder", "reviewer", "researcher"
    system_prompt: str
    config: JSON  # temperature, max_tokens, etc.
    is_active: bool
```

### 3. Workflow Engine

Define how agents collaborate:

```python
# Workflow definition
class Workflow(Base):
    id: UUID
    app_id: UUID
    name: str
    trigger: str  # "chat", "pr_review", "code_gen"
    steps: JSON  # DAG of agent tasks

# Step definition
{
    "id": "step_1",
    "agent": "claude-leader",
    "action": "analyze",
    "prompt_template": "Break down this task: {{input}}",
    "parallel": ["step_2a", "step_2b"],  # fan-out
    "then": "step_3"  # join
}
```

### 4. Orchestration Engine

```python
class Orchestrator:
    async def execute_workflow(
        self,
        workflow: Workflow,
        input: str,
        context: dict
    ) -> WorkflowResult:
        """Execute a multi-agent workflow"""

    async def execute_parallel(
        self,
        agents: list[Agent],
        prompts: list[str]
    ) -> list[str]:
        """Run multiple agents in parallel"""

    async def chain(
        self,
        steps: list[tuple[Agent, str]]
    ) -> str:
        """Run agents sequentially, passing output as input"""
```

---

## API Design

### Agent Management

```http
# Create agent
POST /api/v1/agents
{
    "name": "claude-reviewer",
    "provider": "anthropic",
    "api_key": "sk-ant-...",
    "model": "claude-3-opus-20240229",
    "role": "reviewer",
    "system_prompt": "You are a code reviewer..."
}

# List agents
GET /api/v1/agents

# Test agent
POST /api/v1/agents/{id}/test
{"prompt": "Hello, are you working?"}
```

### Workflow Execution

```http
# Simple multi-agent chat
POST /api/v1/chat/multi
{
    "message": "Review this code...",
    "agents": ["claude-leader", "gpt-coder", "gemini-reviewer"],
    "mode": "parallel"  # or "sequential", "orchestrated"
}

# Execute workflow
POST /api/v1/workflows/{id}/execute
{
    "input": "...",
    "context": {...}
}
```

---

## Implementation Phases

### Phase 1: Provider Abstraction
- [ ] Refactor OllamaProvider to match new interface
- [ ] Add AnthropicProvider (Claude)
- [ ] Add OpenAIProvider (GPT)
- [ ] Add provider factory

### Phase 2: Agent Registry
- [ ] Agent database model
- [ ] CRUD API endpoints
- [ ] API key encryption
- [ ] Agent health monitoring

### Phase 3: Simple Orchestration
- [ ] Parallel execution (fan-out)
- [ ] Sequential chaining
- [ ] Result aggregation

### Phase 4: Workflow Engine
- [ ] Workflow database model
- [ ] DAG execution engine
- [ ] Conditional branching
- [ ] Error handling & retries

### Phase 5: Advanced Features
- [ ] Agent-to-agent communication
- [ ] Streaming for multi-agent
- [ ] Cost tracking per agent
- [ ] Token usage analytics

---

## Example Use Cases

### 1. PR Review Pipeline
```yaml
workflow: pr_review
steps:
  - agent: claude-leader
    action: analyze_pr
    output: analysis

  - parallel:
      - agent: gpt-coder
        action: suggest_fixes
        input: "{{analysis}}"

      - agent: gemini-security
        action: security_review
        input: "{{analysis}}"

  - agent: claude-leader
    action: synthesize
    input: "{{fixes}} {{security}}"
```

### 2. Research Task
```yaml
workflow: research
steps:
  - agent: claude-researcher
    action: search_and_analyze
    parallel_count: 3  # spawn 3 instances

  - agent: claude-synthesizer
    action: combine_findings
```

### 3. Code Generation with Review
```yaml
workflow: code_with_review
steps:
  - agent: gpt-coder
    action: write_code

  - agent: claude-reviewer
    action: review_code

  - agent: gpt-coder
    action: apply_feedback
    condition: "{{review.needs_changes}}"
```

---

## Security Considerations

1. **API Key Storage**: Encrypt all API keys at rest
2. **Key Rotation**: Support key rotation without downtime
3. **Rate Limiting**: Per-agent rate limits
4. **Cost Controls**: Set spending limits per agent/workflow
5. **Audit Logging**: Track all agent invocations

---

## Open Questions

1. **Streaming multi-agent**: How to stream when multiple agents respond?
2. **Context sharing**: How much context to share between agents?
3. **Error recovery**: What happens when one agent in a parallel step fails?
4. **Cost allocation**: How to track/attribute costs to users?

---

## Next Steps

1. Start with Phase 1 - get Claude and OpenAI providers working
2. Build simple `/chat/multi` endpoint for parallel agent queries
3. Iterate from there based on what works

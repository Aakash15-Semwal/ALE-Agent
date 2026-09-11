from dataclasses import dataclass
from typing import Dict, List
from rich.table import Table
from src.config import settings

# Rates per 1,000,000 tokens (USD)
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    # Gemini
    "gemini-3.6-flash": {"prompt": 0.075, "completion": 0.30},
    "gemini-1.5-flash": {"prompt": 0.075, "completion": 0.30},
    "gemini-1.5-pro": {"prompt": 1.25, "completion": 5.00},
    "gemini-2.0-flash": {"prompt": 0.10, "completion": 0.40},
    # OpenAI
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "gpt-4o": {"prompt": 2.50, "completion": 10.00},
    # Groq
    "llama-3.3-70b-versatile": {"prompt": 0.59, "completion": 0.79},
    "llama-3.1-8b-instant": {"prompt": 0.05, "completion": 0.08},
}


def calculate_cost(prompt_tokens: int, completion_tokens: int, model_name: str) -> float:
    rates = MODEL_PRICING.get(model_name) or {"prompt": 0.15, "completion": 0.60}
    prompt_cost = (prompt_tokens / 1_000_000.0) * rates["prompt"]
    completion_cost = (completion_tokens / 1_000_000.0) * rates["completion"]
    return round(prompt_cost + completion_cost, 6)


@dataclass
class DomainUsageRecord:
    domain: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float


class TokenCostTracker:
    def __init__(self):
        self.records: List[DomainUsageRecord] = []

    def record_usage(
        self,
        domain: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        if not settings.enable_cost_tracking:
            return 0.0

        total_tokens = prompt_tokens + completion_tokens
        cost = calculate_cost(prompt_tokens, completion_tokens, model_name)

        record = DomainUsageRecord(
            domain=domain,
            model=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost
        )
        self.records.append(record)
        return cost

    @property
    def total_prompt_tokens(self) -> int:
        return sum(r.prompt_tokens for r in self.records)

    @property
    def total_completion_tokens(self) -> int:
        return sum(r.completion_tokens for r in self.records)

    @property
    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.records)

    @property
    def total_cost_usd(self) -> float:
        return round(sum(r.cost_usd for r in self.records), 6)

    def create_summary_table(self) -> Table:
        table = Table(title="LLM Token & Cost Accounting Summary", show_header=True, header_style="bold magenta")
        table.add_column("Domain", style="cyan", no_wrap=True)
        table.add_column("Model", style="blue")
        table.add_column("Prompt Tokens", justify="right")
        table.add_column("Comp. Tokens", justify="right")
        table.add_column("Total Tokens", justify="right", style="bold")
        table.add_column("Cost (USD)", justify="right", style="green")

        for r in self.records:
            table.add_row(
                r.domain,
                r.model,
                f"{r.prompt_tokens:,}",
                f"{r.completion_tokens:,}",
                f"{r.total_tokens:,}",
                f"${r.cost_usd:.6f}"
            )

        table.add_section()
        table.add_row(
            "TOTAL",
            "-",
            f"{self.total_prompt_tokens:,}",
            f"{self.total_completion_tokens:,}",
            f"{self.total_tokens:,}",
            f"${self.total_cost_usd:.6f}",
            style="bold yellow"
        )
        return table


cost_tracker = TokenCostTracker()

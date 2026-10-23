"""One function per prompt variant. Each takes the ticket text and returns the full prompt string."""

from pathlib import Path

LABELS = ["billing", "bug", "feature", "account"]
TASK = "Classify a customer support ticket into exactly one label: " + ", ".join(LABELS) + "."
ANSWER_RULE = "Reply with only the label, in lowercase, and nothing else."

# Kept out of tickets.csv on purpose, so no variant sees a test ticket.
EXAMPLES = [
    ("I was charged twice for my subscription this month.", "billing"),
    ("The app crashes every time I try to open it.", "bug"),
    ("Can you add a dark mode to the app?", "feature"),
    ("I need to update my email address on my account.", "account"),
]

SEED_PATH = Path(__file__).parent / "seed_prompt.txt"

SEED_META_PROMPT = (
    "Write a prompt that another language model will use to classify customer support tickets "
    "into exactly one of these labels: " + ", ".join(LABELS) + ". "
    "Put the placeholder {ticket} where the ticket text goes. "
    "The prompt must make the model reply with only the label, in lowercase. "
    "Output only the prompt, with no commentary."
)

def zero_shot(text: str) -> str:
    """Return a zero-shot prompt for the given ticket text."""
    return f"{TASK}\n{ANSWER_RULE}\n\nTicket: {text}\nLabel:"

def single_shot(text: str) -> str:
    """Return a single-shot prompt for the given ticket text."""
    examples_str = "\n".join(f"Ticket: {ticket}\nLabel: {label}" for ticket, label in EXAMPLES)
    return f"{TASK}\n{ANSWER_RULE}\n\n{examples_str}\n\nTicket: {text}\nLabel:"

def few_shot(text: str, n: int = 2) -> str:
    """Return a few-shot prompt for the given ticket text, using n examples."""
    examples_str = "\n".join(f"Ticket: {ticket}\nLabel: {label}" for ticket, label in EXAMPLES[:n])
    return f"{TASK}\n{ANSWER_RULE}\n\n{examples_str}\n\nTicket: {text}\nLabel:" 

def few_shot_xml(text: str, n: int = 2) -> str:
    """Return a few-shot prompt for the given ticket text, using n examples, in XML format."""
    examples_str = "\n".join(f"<ticket><text>{ticket}</text><label>{label}</label></ticket>" for ticket, label in EXAMPLES[:n])
    return f"{TASK}\n{ANSWER_RULE}\n\n<examples>\n{examples_str}\n</examples>\n\n<ticket><text>{text}</text><label></label></ticket>"   

def seed_crystal(text: str) -> str:
    """Return a prompt for the given ticket text, using the seed prompt from seed_prompt.txt."""
    with open(SEED_PATH, "r") as f:
        seed_prompt = f.read()
    return seed_prompt.format(ticket=text)

VARIANTS = {
    "zero_shot": zero_shot,
    "single_shot": single_shot,
    "few_shot": few_shot,
    "few_shot_xml": few_shot_xml,
    "seed_crystal": seed_crystal
}
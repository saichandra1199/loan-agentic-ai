from crewai.tools import tool

@tool("Human Input Tool")
def ask_human(question: str) -> str:
    """
    Ask the human operator for clarification when critical information
    is missing or unclear in the documents.
    Use this when you cannot extract key data like income, loan amount,
    property value, or applicant details.
    """
    print(f"\n{'='*60}")
    print(f"🤖 Agent needs your input:")
    print(f"{'='*60}")
    print(f"❓ {question}")
    print(f"{'='*60}")
    answer = input("Your answer: ").strip()
    return answer if answer else "No answer provided."
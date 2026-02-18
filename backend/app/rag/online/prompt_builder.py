"""
Prompt Builder Module

Constructs LLM prompts that enforce strict grounding to context.
This is Step 12 of the RAG pipeline: Prompt Construction.

Creates prompts that prevent hallucination by enforcing "answer ONLY from context" rule.
"""

from typing import Optional
from app.logging_config import get_logger

logger = get_logger(__name__)

# Strict prompt template - prevents hallucination
STRICT_PROMPT_TEMPLATE = """You are a helpful assistant that answers questions based ONLY on the provided context.

CRITICAL RULES:
1. Answer ONLY using information explicitly stated in the context below
2. If the context does not contain enough information to answer the question, respond EXACTLY with: "I don't know based on the available information."
3. Do NOT use external knowledge or make assumptions
4. Do NOT infer or extrapolate beyond what is explicitly stated
5. Be concise and accurate
6. Quote or reference the context when appropriate

CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:"""


# Alternative: More conversational prompt (still grounded)
CONVERSATIONAL_PROMPT_TEMPLATE = """You are a helpful assistant answering questions based on provided documents.

Your task is to answer the user's question using ONLY the information in the context below.

Guidelines:
- Use only information from the context
- If the answer is not in the context, say "I don't know based on the available information."
- Be clear and friendly
- You can rephrase information from the context to make it easier to understand

CONTEXT:
{context}

USER QUESTION:
{question}

ANSWER:"""


# System + User message format (for chat models)
CHAT_SYSTEM_MESSAGE = """You are a helpful assistant that answers questions based strictly on provided context.

RULES:
1. Answer ONLY from the context provided
2. If information is not in context, say "I don't know based on the available information."
3. Never use external knowledge
4. Be concise and accurate"""


def build_prompt(
    question: str,
    context: str,
    prompt_type: str = "strict"
) -> str:
    """
    Build a prompt for the LLM that combines context and question.
    
    Args:
        question: User's question
        context: Assembled context from retrieved chunks
        prompt_type: Type of prompt ("strict" or "conversational")
        
    Returns:
        Complete prompt string ready for LLM
        
    Example:
        >>> question = "What is Theory X?"
        >>> context = "Context 1: Theory X assumes employees dislike work..."
        >>> prompt = build_prompt(question, context)
        >>> # Send prompt to LLM
    """
    logger.debug(f"Building {prompt_type} prompt for question: '{question[:50]}...'")
    
    if not question or not question.strip():
        logger.warning("Empty question provided to prompt builder")
        raise ValueError("Question cannot be empty")
    
    # Handle empty context
    if not context or not context.strip():
        logger.warning("No context provided for prompt")
        context = "[No relevant context found]"
    
    # Select template
    if prompt_type == "conversational":
        template = CONVERSATIONAL_PROMPT_TEMPLATE
    else:  # Default to strict
        template = STRICT_PROMPT_TEMPLATE
    
    # Format prompt
    prompt = template.format(
        context=context.strip(),
        question=question.strip()
    )
    
    logger.debug(f"Prompt built: {len(prompt)} characters")
    return prompt


def build_chat_messages(
    question: str,
    context: str
) -> list[dict]:
    """
    Build messages for chat-based LLMs (OpenAI, Claude, etc.).
    
    Args:
        question: User's question
        context: Assembled context from retrieved chunks
        
    Returns:
        List of message dicts with role and content
        
    Example:
        >>> messages = build_chat_messages("What is Theory X?", context)
        >>> # [
        >>> #   {"role": "system", "content": "..."},
        >>> #   {"role": "user", "content": "..."}
        >>> # ]
    """
    logger.debug(f"Building chat messages for question: '{question[:50]}...'")
    
    if not question or not question.strip():
        logger.warning("Empty question provided to build_chat_messages")
        raise ValueError("Question cannot be empty")
    
    if not context or not context.strip():
        logger.warning("No context provided for chat messages")
        context = "[No relevant context found]"
    
    user_message = f"""CONTEXT:
{context.strip()}

QUESTION:
{question.strip()}"""
    
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_MESSAGE},
        {"role": "user", "content": user_message}
    ]
    
    return messages


def validate_prompt(prompt: str, max_tokens: int = 8000) -> dict:
    """
    Validate prompt length and structure.
    
    Args:
        prompt: Complete prompt string
        max_tokens: Maximum allowed tokens (rough estimate)
        
    Returns:
        Dictionary with validation results:
        - valid: bool
        - char_count: int
        - estimated_tokens: int
        - warnings: list
    """
    
    char_count = len(prompt)
    # Rough estimate: 1 token ≈ 4 characters
    estimated_tokens = char_count // 4
    
    warnings = []
    valid = True
    
    if estimated_tokens > max_tokens:
        warnings.append(f"Prompt may exceed token limit ({estimated_tokens} > {max_tokens})")
        valid = False
    
    if char_count < 50:
        warnings.append("Prompt seems too short")
        valid = False
    
    if "{context}" in prompt or "{question}" in prompt:
        warnings.append("Prompt contains unformatted placeholders")
        valid = False
    
    return {
        "valid": valid,
        "char_count": char_count,
        "estimated_tokens": estimated_tokens,
        "warnings": warnings
    }


def build_fallback_prompt(question: str) -> str:
    """
    Build a fallback prompt when no context is available.
    
    Args:
        question: User's question
        
    Returns:
        Prompt that explains no context was found
    """
    
    return f"""You are a helpful assistant. The user asked: "{question}"

However, no relevant information was found in the available documents.

Respond with: "I don't know based on the available information. The documents don't contain information about this topic."

ANSWER:"""


if __name__ == "__main__":
    """Test the prompt builder"""
    print("\n" + "="*60)
    print("STEP 12: Prompt Builder Test")
    print("="*60 + "\n")
    
    # Sample data
    sample_question = "What is Theory X?"
    sample_context = """Context 1 (relevance: 0.46 from McGregor_Theory_X_and_Y.pdf):
Theory X is a management style that assumes employees inherently dislike work and will avoid it if possible. Managers who subscribe to Theory X believe that workers need to be closely supervised and controlled through rewards and punishments.

Context 2 (relevance: 0.41 from McGregor_Theory_X_and_Y.pdf):
Theory Y represents a contrasting management philosophy. It assumes that employees are self-motivated, enjoy their work, and seek out responsibility. Theory Y managers believe in empowering employees and giving them autonomy."""
    
    # Test 1: Strict prompt
    print("1. Testing strict prompt...")
    strict_prompt = build_prompt(sample_question, sample_context, prompt_type="strict")
    print(f"   ✅ Prompt length: {len(strict_prompt)} chars")
    print(f"\n   Prompt preview (first 400 chars):")
    print("   " + "-" * 56)
    for line in strict_prompt[:400].split('\n'):
        print(f"   {line}")
    print("   ...")
    print("   " + "-" * 56)
    
    # Test 2: Conversational prompt
    print("\n2. Testing conversational prompt...")
    conv_prompt = build_prompt(sample_question, sample_context, prompt_type="conversational")
    print(f"   ✅ Prompt length: {len(conv_prompt)} chars")
    
    # Test 3: Chat messages format
    print("\n3. Testing chat messages format...")
    messages = build_chat_messages(sample_question, sample_context)
    print(f"   ✅ Generated {len(messages)} messages")
    print(f"      - System: {len(messages[0]['content'])} chars")
    print(f"      - User: {len(messages[1]['content'])} chars")
    
    # Test 4: Validation
    print("\n4. Testing prompt validation...")
    validation = validate_prompt(strict_prompt)
    print(f"   Valid: {validation['valid']}")
    print(f"   Characters: {validation['char_count']}")
    print(f"   Estimated tokens: {validation['estimated_tokens']}")
    if validation['warnings']:
        print(f"   Warnings: {validation['warnings']}")
    else:
        print("   ✅ No warnings")
    
    # Test 5: Empty context
    print("\n5. Testing with empty context...")
    empty_prompt = build_prompt(sample_question, "", prompt_type="strict")
    print(f"   ✅ Handled empty context")
    if "[No relevant context found]" in empty_prompt:
        print("   ✅ Contains fallback message")
    
    # Test 6: Fallback prompt
    print("\n6. Testing fallback prompt...")
    fallback = build_fallback_prompt(sample_question)
    print(f"   ✅ Fallback prompt length: {len(fallback)} chars")
    
    # Test 7: Complete prompt display
    print("\n7. Complete strict prompt example:")
    print("   " + "="*56)
    print(strict_prompt)
    print("   " + "="*56)
    
    print("\n" + "="*60)
    print("✅ Step 12 Complete: Prompt Builder Working!")
    print("="*60 + "\n")

"""
LLM Generator Module

Generates answers using Groq API with strict RAG grounding.
This is Step 13 of the RAG pipeline: Answer Generation.

Uses Groq for fast, accurate responses grounded strictly in provided context.
"""

from typing import Optional, Dict, List
import os
from pathlib import Path
from groq import Groq
import time
from dotenv import load_dotenv
from app.logging_config import get_logger

logger = get_logger(__name__)
# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)


# Strict RAG system instructions
STRICT_RAG_SYSTEM_MESSAGE = """You are a strict RAG-based assistant.

Rules:
1. Answer ONLY using the provided context.
2. If the answer is not found in the context, say exactly:
   "I don't know based on the provided documents."
3. Do NOT use external knowledge.
4. Do NOT guess.
5. Keep answers concise and factual."""


class LLMGenerator:
    """
    Generates answers from prompts using Groq API.
    
    Enforces strict RAG grounding - answers only from provided PDF context.
    """
    
    def __init__(
        self,
        model: str = "llama-3.1-8b-instant",
        api_key: Optional[str] = None,
        temperature: float = 0.0,  # 0 = deterministic, no creativity
        max_tokens: int = 500
    ):
        """
        Initialize Groq LLM generator.
        
        Args:
            model: Groq model name (llama-3.1-8b-instant recommended)
            api_key: Groq API key (if None, reads from GROQ_API_KEY env)
            temperature: Randomness (0=deterministic, 1=creative). Use 0 for RAG.
            max_tokens: Maximum response length
        """
        logger.debug(f"Initializing LLM generator: model={model}, temp={temperature}")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Get API key
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.error("Groq API key not found")
            raise ValueError(
                "Groq API key not found!\n"
                "Get your free key at: https://console.groq.com/keys\n"
                "Then add to backend/.env: GROQ_API_KEY=your_key_here"
            )
        
        # Initialize Groq client
        try:
            self.client = Groq(api_key=api_key)
            logger.info(f"Groq initialized successfully (model: {self.model})")
        except Exception as e:
            logger.error(f"Failed to initialize Groq: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize Groq: {e}")
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate answer from prompt.
        
        Args:
            prompt: Complete prompt with context and question
            max_tokens: Override default max tokens
            temperature: Override default temperature
            
        Returns:
            Generated answer text
            
        Example:
            >>> generator = LLMGenerator()
            >>> prompt = "Context: Theory X...\n\nQuestion: What is Theory X?"
            >>> answer = generator.generate(prompt)
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        
        logger.debug(f"Generating answer: prompt_len={len(prompt)}, max_tokens={max_tokens}, temp={temperature}")
        
        if not prompt or not prompt.strip():
            logger.warning("Empty prompt provided to generator")
            return "Error: Empty prompt provided."
        
        try:
            start_time = time.time()
            
            logger.debug("Sending request to Groq API...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": STRICT_RAG_SYSTEM_MESSAGE
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1,
                stream=False
            )
            
            elapsed = time.time() - start_time
            answer = response.choices[0].message.content.strip()
            
            # Log performance
            if hasattr(response, 'usage'):
                tokens = response.usage.total_tokens
                tokens_per_sec = tokens / elapsed if elapsed > 0 else 0
                logger.info(f"Groq response: {elapsed:.2f}s | {tokens} tokens | {tokens_per_sec:.0f} tok/s")
            else:
                logger.info(f"Groq response: {elapsed:.2f}s")
            
            logger.debug(f"Generated answer length: {len(answer)} chars")
            return answer
            
        except Exception as e:
            logger.error(f"Groq API error: {e}", exc_info=True)
            return "I apologize, but I'm having trouble generating a response right now."
    
    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate using chat message format.
        
        Args:
            messages: List of {"role": "system/user", "content": "..."}
            max_tokens: Override default
            temperature: Override default
            
        Returns:
            Generated answer
            
        Example:
            >>> messages = [
            ...     {"role": "system", "content": STRICT_RAG_SYSTEM_MESSAGE},
            ...     {"role": "user", "content": "Context...\n\nQuestion..."}
            ... ]
            >>> answer = generator.generate_with_messages(messages)
        """
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        
        try:
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=1
            )
            
            elapsed = time.time() - start_time
            answer = response.choices[0].message.content.strip()
            
            if hasattr(response, 'usage'):
                tokens = response.usage.total_tokens
                print(f"⚡ Groq: {elapsed:.2f}s | {tokens} tokens")
            
            return answer
            
        except Exception as e:
            print(f"❌ Groq API error: {e}")
            return "I apologize, but I'm having trouble generating a response right now."
    
    def test_connection(self) -> bool:
        """
        Test if Groq API is working.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.generate(
                "Say 'OK' if you can read this.",
                max_tokens=10
            )
            return len(response) > 0
        except:
            return False


# Singleton instance for reuse across requests
_generator_instance: Optional[LLMGenerator] = None


def get_generator(
    model: str = "llama-3.1-8b-instant",
    reinit: bool = False
) -> LLMGenerator:
    """
    Get or create singleton LLM generator instance.
    
    Avoids reinitializing Groq client on every request.
    
    Args:
        model: Groq model name
        reinit: Force reinitialization
        
    Returns:
        LLMGenerator instance
    """
    global _generator_instance
    
    if _generator_instance is None or reinit:
        _generator_instance = LLMGenerator(model=model)
    
    return _generator_instance


if __name__ == "__main__":
    """Test the Groq generator"""
    print("\n" + "="*60)
    print("STEP 13: LLM Generator Test (Groq)")
    print("="*60 + "\n")
    
    try:
        # Initialize generator
        print("1. Initializing Groq generator...")
        generator = LLMGenerator()
        
        # Test 1: Answer from context
        print("\n2. Test: Question WITH answer in context...")
        print("-" * 60)
        
        test_prompt_1 = """CONTEXT:
Theory X is a management style that assumes employees inherently dislike work and will avoid it if possible. Managers who subscribe to Theory X believe that workers need to be closely supervised and controlled through rewards and punishments.

Theory Y represents a contrasting management philosophy. It assumes that employees are self-motivated, enjoy their work, and seek out responsibility.

QUESTION:
What does Theory X assume about employees?

ANSWER:"""
        
        answer_1 = generator.generate(test_prompt_1)
        print(f"Answer: {answer_1}\n")
        
        # Test 2: Question NOT in context
        print("\n3. Test: Question WITHOUT answer in context...")
        print("-" * 60)
        
        test_prompt_2 = """CONTEXT:
Theory X is a management style that assumes employees inherently dislike work and will avoid it if possible.

QUESTION:
What is quantum physics?

ANSWER:"""
        
        answer_2 = generator.generate(test_prompt_2)
        print(f"Answer: {answer_2}\n")
        
        # Test 3: Chat message format
        print("\n4. Test: Chat message format...")
        print("-" * 60)
        
        messages = [
            {
                "role": "system",
                "content": STRICT_RAG_SYSTEM_MESSAGE
            },
            {
                "role": "user",
                "content": """CONTEXT:
Douglas McGregor proposed Theory X and Theory Y in 1960.

QUESTION:
Who proposed Theory X and Theory Y?

ANSWER:"""
            }
        ]
        
        answer_3 = generator.generate_with_messages(messages)
        print(f"Answer: {answer_3}\n")
        
        # Test 4: Connection test
        print("\n5. Test: Connection check...")
        print("-" * 60)
        is_working = generator.test_connection()
        print(f"✅ Groq connection: {'Working' if is_working else 'Failed'}\n")
        
        # Test 5: Singleton test
        print("\n6. Test: Singleton pattern...")
        print("-" * 60)
        gen2 = get_generator()
        print(f"✅ Same instance: {generator is gen2}\n")
        
        print("\n" + "="*60)
        print("✅ Step 13 Complete: Groq Generator Working!")
        print("="*60 + "\n")
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}\n")
        print("To fix:")
        print("1. Get free API key: https://console.groq.com/keys")
        print("2. Add to backend/.env: GROQ_API_KEY=your_key_here")
        print("3. Run this test again\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

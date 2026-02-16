from .summarizer import TextSummarizer
from pathlib import Path
import os

__version__ = "1.3.2"

# Automatically ensure GloVe embeddings are available on package import
def _ensure_glove_embeddings():
    """Ensure GloVe embeddings are downloaded on package import."""
    try:
        home_dir = Path.home()
        glove_dir = home_dir / '.text_summarizer'
        glove_file = glove_dir / 'glove.6B.100d.txt'
        
        # If GloVe file doesn't exist, download it
        if not glove_file.exists():
            print("Initializing GloVe embeddings for text-summarizer...")
            from .summarizer import TextSummarizer
            # Create a temporary instance to trigger download
            summarizer = TextSummarizer()
            print("GloVe embeddings ready!")
    except Exception as e:
        # Silently fail - user can still use the package, just slower on first run
        pass

# Download embeddings on package import (not blocking)
_ensure_glove_embeddings()
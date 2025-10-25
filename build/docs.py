# Import parent dir to access options_schema
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from optionsconfig import EnvBuilder, ReadmeBuilder

def build_docs() -> None:
    """Build documentation files like .env.example and README.md based on the options schema."""
    EnvBuilder().build()
    ReadmeBuilder().build()
    
if __name__ == "__main__":
    build_docs()
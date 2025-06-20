print("🧪 Testing if all packages are installed...")

try:
    import pandas as pd
    print("✅ pandas OK")
except ImportError:
    print("❌ pandas missing")

try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
    print("✅ spaCy + English model OK")
except Exception as e:
    print(f"❌ spaCy issue: {e}")

try:
    import sentence_transformers
    print("✅ sentence-transformers OK")
except ImportError:
    print("❌ sentence-transformers missing")

try:
    from flask import Flask
    print("✅ Flask OK")
except ImportError:
    print("❌ Flask missing")

try:
    from matching_system import FreeCandidateMatchingSystem
    print("✅ Our matching system imports OK")
except Exception as e:
    print(f"❌ Matching system issue: {e}")

print("🎯 Test complete!")
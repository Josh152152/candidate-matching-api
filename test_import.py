try:
    from matching_system import FreeCandidateMatchingSystem
    print("✅ Import successful!")
    print("✅ Class found:", FreeCandidateMatchingSystem)
except ImportError as e:
    print(f"❌ Import failed: {e}")
except Exception as e:
    print(f"❌ Other error: {e}")
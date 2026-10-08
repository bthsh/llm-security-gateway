import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.config import settings
from app.guard_a.classifier import classifier


def download_all():
    print(f"Pre-downloading classifier model '{settings.CLASSIFIER_MODEL}'...")
    try:
        classifier.warmup()
        print("Classifier model ready.")
    except Exception as e:
        print(f"Classifier download failed: {e}")

    try:
        import spacy
        print("Loading spaCy en_core_web_sm model...")
        nlp = spacy.load("en_core_web_sm")
        print("spaCy model ready.")
    except Exception as e:
        print(f"spaCy model loading failed: {e}")


if __name__ == "__main__":
    download_all()

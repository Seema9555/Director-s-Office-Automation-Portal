import os
from better_profanity import profanity

SWEAR_WORDS_DIR = r"C:\Users\Dell\OneDrive\Desktop\anti\finalbpt - Copy - Copy\Director_Portal\swear-words-master\swear-words-master"
_profanity_initialized = False

def initialize_profanity():
    """
    Loads custom swear words from the dictionary and initializes better_profanity.
    It automatically handles leetspeak, spaces, and other bypasses.
    """
    global _profanity_initialized
    if _profanity_initialized:
        return

    custom_swear_words = set()
    
    # Load default english words as a base
    profanity.load_censor_words()
    
    if os.path.exists(SWEAR_WORDS_DIR):
        for filename in os.listdir(SWEAR_WORDS_DIR):
            if '.' not in filename or filename == 'en':
                filepath = os.path.join(SWEAR_WORDS_DIR, filename)
                if os.path.isfile(filepath):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            for line in f:
                                word = line.strip().lower()
                                if word and len(word) > 1:
                                    custom_swear_words.add(word)
                    except Exception:
                        pass
                        
    if custom_swear_words:
        # better_profanity allows adding custom words to the existing loaded set
        profanity.add_censor_words(list(custom_swear_words))
        
    _profanity_initialized = True

def censor_text(text):
    """
    Replaces swear words (and their leetspeak variations) in the text with asterisks.
    """
    if not text:
        return text
        
    initialize_profanity()
    return profanity.censor(text)

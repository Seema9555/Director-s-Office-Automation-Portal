import re
import logging
from textblob import TextBlob

# Configure Logger (Production mein ye zaroori hai taaki false rejects track kar saken)
logger = logging.getLogger(__name__)

class SpamDetector:
    """
    Production-grade Spam Detection Service using NLP heuristics and Scoring.
    """
    
    # --- CONFIGURATION (Easily changeable) ---
    MIN_LENGTH = 20
    MIN_VOWEL_RATIO = 0.2  # Kam se kam 20% vowels hone chahiye (English words structure)
    SPAM_THRESHOLD_SCORE = 50  # 50 se kam score hua to Reject
    
    # Keywords with Weightage (Kuch words ki value zyada hai)
    HIGH_VALUE_KEYWORDS = [
        'visa', 'passport', 'immigration', 'embassy', 'consulate',
        'placement', 'tcs', 'infosys', 'wipro', 'capgemini', 'google', 'microsoft',
        'gate', 'cat', 'gre', 'toefl', 'ielts', 'upsc',
        'joining', 'onboarding', 'hr', 'offer letter'
    ]
    
    MEDIUM_VALUE_KEYWORDS = [
        'job', 'internship', 'higher studies', 'college', 'university',
        'exam', 'loan', 'bank', 'scholarship', 'document', 'apply',
        'verification', 'urgent', 'deadline'
    ]

    def __init__(self, text):
        self.raw_text = text
        self.clean_text = text.lower().strip()
        self.blob = TextBlob(self.clean_text)
        self.score = 0
        self.rejection_reason = None

    def validate(self):
        """
        Main pipeline to validate text.
        Returns: (is_valid: bool, message: str)
        """
        # 1. Sanity Check (Empty or Too Short)
        if not self._check_length():
            return False, f"Description too short. Please write at least {self.MIN_LENGTH} characters explaining why you need this."

        # 2. Gibberish/Keyboard Smash Check
        if not self._check_structure():
            return False, "Input looks like random typing. Please use proper sentences."

        # 3. Profanity & Aggression Check
        if not self._check_sentiment():
            return False, "Inappropriate or aggressive language detected. Please be professional."

        # 4. Contextual Scoring (The Brain)
        self._calculate_context_score()
        
        # Final Decision
        if self.score < self.SPAM_THRESHOLD_SCORE:
            logger.warning(f"SPAM REJECTED | Score: {self.score} | Text: {self.raw_text}")
            return False, "Reason seems vague. Please specify the Company Name, Exam Name, or Authority you are submitting to."

        # Success
        logger.info(f"VALID REQUEST | Score: {self.score} | Text: {self.raw_text}")
        return True, "Valid"

    # --- INTERNAL HELPER METHODS ---

    def _check_length(self):
        return len(self.clean_text) >= self.MIN_LENGTH

    def _check_structure(self):
        # Rule A: Check Vowel Ratio (Random typing like 'thsjhgkl' has low vowels)
        vowels = len(re.findall(r'[aeiou]', self.clean_text))
        total_chars = len(re.sub(r'[^a-z]', '', self.clean_text)) # Only count letters
        
        if total_chars > 0:
            ratio = vowels / total_chars
            if ratio < self.MIN_VOWEL_RATIO:
                return False
        
        # Rule B: Repeating Characters (e.g., 'pleaaaaaase')
        if re.search(r'(.)\1{3,}', self.clean_text):
            return False
            
        return True

    def _check_sentiment(self):
        # Polarity < -0.6 means highly negative/abusive
        if self.blob.sentiment.polarity < -0.6:
            return False
        return True

    def _calculate_context_score(self):
        # Base Score starts at 10
        current_score = 10
        
        # Check High Value Keywords (+30 points)
        for word in self.HIGH_VALUE_KEYWORDS:
            if word in self.clean_text:
                current_score += 30
                break # Ek bhi mil gaya to kaafi hai
        
        # Check Medium Value Keywords (+15 points)
        for word in self.MEDIUM_VALUE_KEYWORDS:
            if word in self.clean_text:
                current_score += 15
        
        # Length Bonus: Agar student ne detail mein likha hai (>50 chars)
        if len(self.clean_text) > 50:
            current_score += 10
            
        # Noun Phrase Bonus: Agar "Tata Consultancy Services" jaisa proper noun hai
        if len(self.blob.noun_phrases) > 0:
            current_score += 10

        self.score = current_score
        
        
import cv2
import numpy as np

class DocumentQualityChecker:
    """
    Computer Vision Service to check Image Quality (Blur & Brightness).
    Uses OpenCV (cv2).
    """

    # --- CONFIGURATION ---
    BLUR_THRESHOLD = 100       # Isse kam score = Blurry
    BRIGHTNESS_THRESHOLD = 60  # Isse kam score = Too Dark (0-255 scale)

    def __init__(self, file_obj):
        self.file_obj = file_obj
        self.image = None
        self.error_msg = None

    def _load_image(self):
        """
        Convert Django UploadedFile to OpenCV Image (Numpy Array).
        """
        try:
            # Check if file is image (Skip PDFs)
            if not self.file_obj.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                return False # Not an image, skip check

            # Read file details
            file_data = self.file_obj.read()
            
            # Convert string data to numpy array
            np_arr = np.frombuffer(file_data, np.uint8)
            
            # Decode image
            self.image = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            # Reset file pointer (Important! Warna Django save nahi kar payega)
            self.file_obj.seek(0)
            
            return True
        except Exception as e:
            logger.error(f"Image Load Error: {e}")
            return False

    def validate(self):
        """
        Main pipeline. Returns (is_valid: bool, reason: str)
        """
        # 1. Load Image
        if not self._load_image():
            # Agar PDF hai ya load nahi hua, toh pass kar do (Sirf Images check karenge)
            return True, "Skipped (Not an image)"

        # 2. Check Blur (Laplacian Variance Method)
        # Convert to Grayscale (Blur check works best on B&W)
        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        logger.info(f"Blur Score: {blur_score}")

        if blur_score < self.BLUR_THRESHOLD:
            return False, f"Image is too blurry (Score: {int(blur_score)}). Please upload a clear scan."

        # 3. Check Brightness (Average Pixel Intensity)
        # Calculate average brightness
        avg_brightness = np.mean(gray)
        
        logger.info(f"Brightness Score: {avg_brightness}")
        
        if avg_brightness < self.BRIGHTNESS_THRESHOLD:
            return False, "Image is too dark / low light. Please click a photo in good lighting."

        return True, "Quality Good"
    
    
class UrgencyAnalyzer:
    """
    Analyzes the 'Purpose' text to detect urgency.
    """
    # Keywords jo urgency dikhate hain
    URGENT_KEYWORDS = [
        'urgent', 'deadline', 'immediately', 'asap', 'visa', 'passport',
        'job offer', 'interview', 'joining date', 'revoked', 'foreign',
        'consulate', 'embassy', 'tcs', 'infosys', 'wipro', 'capgemini', # Job companies
        'tomorrow', 'today', 'expire', 'last date'
    ]

    def __init__(self, text):
        self.text = text.lower()

    def get_priority(self):
        # Check agar koi bhi keyword text mein maujood hai
        for word in self.URGENT_KEYWORDS:
            if word in self.text:
                return 'High'
        return 'Normal' 
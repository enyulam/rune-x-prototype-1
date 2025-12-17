"""
Sentence-level translation functionality using MarianMT with enhanced error handling.
Provides neural machine translation for full sentences, complementing dictionary-based character translation.
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)

try:
    from transformers import MarianMTModel, MarianTokenizer
except ImportError:
    MarianMTModel = None
    MarianTokenizer = None


class SentenceTranslator:
    """
    Handles Chinese to English translation using MarianMT.
    
    Provides error handling and logging for translation operations.
    Complements the dictionary-based RuleBasedTranslator for character-level meanings.
    """
    
    def __init__(self, model_name: str = "Helsinki-NLP/opus-mt-zh-en"):
        """
        Initialize MarianMT translator.
        
        Args:
            model_name: HuggingFace model identifier for the translation model
            
        Raises:
            ImportError: If transformers library is not installed
        """
        if MarianMTModel is None or MarianTokenizer is None:
            logger.warning(
                "transformers library is not installed. Sentence translation will be unavailable. "
                "Install it with: pip install transformers torch"
            )
            self.model_name = None
            self.tokenizer = None
            self.model = None
            self._loaded = False
            self._available = False
            return
        
        self.model_name = model_name
        self.tokenizer = None
        self.model = None
        self._loaded = False
        self._available = True
        logger.info(f"SentenceTranslator initialized with model: {model_name}")
    
    def _load_model(self):
        """
        Lazy load the model (only when needed).
        
        Handles model loading errors gracefully.
        """
        if self._loaded or not self._available:
            return
        
        try:
            logger.info(f"Loading translation model: {self.model_name}")
            self.tokenizer = MarianTokenizer.from_pretrained(self.model_name)
            self.model = MarianMTModel.from_pretrained(self.model_name)
            self._loaded = True
            logger.info("Translation model loaded successfully")
        except Exception as e:
            logger.error(f"Could not load translation model: {e}", exc_info=True)
            self._loaded = False
            self._available = False
    
    def translate(self, text: str) -> str:
        """
        Translate Chinese text to English.
        
        Args:
            text: Chinese text to translate
            
        Returns:
            str: English translation, or error message if translation fails
        """
        if not text or not text.strip():
            return ""
        
        if not self._available:
            logger.debug("Sentence translation not available (transformers not installed)")
            return "[Translation unavailable]"
        
        self._load_model()
        
        if not self._loaded or self.model is None or self.tokenizer is None:
            logger.warning("Translation model not loaded")
            return "[Translation unavailable]"
        
        try:
            # Tokenize and translate
            # Limit input length to prevent memory issues
            max_length = 512
            if len(text) > max_length:
                logger.warning(f"Text too long ({len(text)} chars), truncating to {max_length}")
                text = text[:max_length]
            
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
            translated = self.model.generate(**inputs)
            translation = self.tokenizer.decode(translated[0], skip_special_tokens=True)
            logger.debug(f"Translated text: {text[:50]}... -> {translation[:50]}...")
            return translation
        except Exception as e:
            logger.error(f"Translation error: {e}", exc_info=True)
            return "[Translation error]"
    
    def is_available(self) -> bool:
        """
        Check if translation is available.
        
        Returns:
            bool: True if transformers library is available, False otherwise
        """
        return self._available and (MarianMTModel is not None and MarianTokenizer is not None)


def get_sentence_translator() -> Optional[SentenceTranslator]:
    """
    Get or create a singleton SentenceTranslator instance.
    
    Returns:
        SentenceTranslator instance if transformers is available, None otherwise
    """
    try:
        translator = SentenceTranslator()
        if translator.is_available():
            return translator
        return None
    except Exception as e:
        logger.error(f"Failed to initialize sentence translator: {e}")
        return None


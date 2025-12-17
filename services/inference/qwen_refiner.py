"""
Qwen LLM refinement module for improving MarianMT translations.
Refines translations by correcting OCR noise, improving coherence, and enhancing fluency
while preserving meaning and structure.
"""
from typing import Optional, List
import logging
import re

logger = logging.getLogger(__name__)

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
except ImportError:
    AutoModelForCausalLM = None
    AutoTokenizer = None
    torch = None


class QwenRefiner:
    """
    Handles translation refinement using local Qwen LLM.
    
    Takes MarianMT translation and original OCR text, then refines the translation
    to correct OCR noise, improve coherence, and enhance fluency while preserving
    meaning and sentence structure.
    """
    
    def __init__(self, model_name: str = "Qwen/Qwen2.5-1.5B-Instruct"):
        """
        Initialize Qwen refiner.
        
        Args:
            model_name: HuggingFace model identifier for Qwen model
            
        Note:
            Model loads lazily on first use. Requires transformers and torch.
        """
        if AutoModelForCausalLM is None or AutoTokenizer is None or torch is None:
            logger.warning(
                "transformers or torch not available. Qwen refinement will be unavailable. "
                "Install with: pip install transformers torch"
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
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"QwenRefiner initialized with model: {model_name} (device: {self.device})")
    
    def _load_model(self):
        """
        Lazy load the Qwen model (only when needed).
        
        Handles model loading errors gracefully.
        """
        if self._loaded or not self._available:
            return
        
        try:
            logger.info(f"Loading Qwen model: {self.model_name}")
            logger.info("This may take a few minutes on first use (downloading ~3GB model)...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Prepare model loading kwargs
            model_kwargs = {
                "trust_remote_code": True,
                "dtype": torch.float16 if self.device == "cuda" else torch.float32
            }
            
            # Only use device_map if CUDA is available and accelerate is installed
            if self.device == "cuda":
                try:
                    import accelerate
                    model_kwargs["device_map"] = "auto"
                except ImportError:
                    logger.warning("accelerate not installed, loading model without device_map")
                    # Will manually move to device after loading
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **model_kwargs
            )
            
            # Manually move to device if not using device_map
            if "device_map" not in model_kwargs:
                self.model = self.model.to(self.device)
            
            self.model.eval()  # Set to evaluation mode
            self._loaded = True
            logger.info("Qwen model loaded successfully")
        except Exception as e:
            logger.error(f"Could not load Qwen model: {e}", exc_info=True)
            self._loaded = False
            self._available = False
    
    def _detect_sentence_boundaries(self, text: str) -> List[str]:
        """
        Detect sentence boundaries in OCR text.
        
        Splits text on periods, line breaks, and other sentence delimiters.
        Preserves sentence structure for refinement.
        
        Args:
            text: OCR-extracted text
            
        Returns:
            List of sentences (may be single sentence if no boundaries detected)
        """
        if not text or not text.strip():
            return []
        
        # Split on periods, exclamation marks, question marks, line breaks
        # Pattern: period/question/exclamation followed by space or end of string
        # Also split on line breaks
        sentences = re.split(r'([。！？\n]+|\.[\s\n]+|[!?][\s\n]+)', text)
        
        # Filter out empty strings and clean up
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # If no sentence boundaries found, return entire text as single sentence
        if len(sentences) == 0:
            return [text.strip()] if text.strip() else []
        
        # Reconstruct sentences (rejoin delimiters with their sentences)
        result = []
        current_sentence = ""
        for i, part in enumerate(sentences):
            if re.match(r'^[。！？\n\.!?\s]+$', part):
                # This is a delimiter, attach to previous sentence
                if current_sentence:
                    result.append(current_sentence + part)
                    current_sentence = ""
            else:
                current_sentence += part
        
        # Add remaining sentence
        if current_sentence:
            result.append(current_sentence)
        
        # If still no proper sentences, return original text
        if not result:
            return [text.strip()] if text.strip() else []
        
        return result
    
    def _create_refinement_prompt(self, ocr_text: str, nmt_translation: str) -> str:
        """
        Create prompt for Qwen refinement.
        
        Provides clear instructions to refine translation while preserving meaning
        and correcting OCR noise.
        
        Args:
            ocr_text: Original OCR-extracted Chinese text
            nmt_translation: MarianMT translation output
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a translation refinement assistant. Your task is to refine a machine translation by correcting errors caused by OCR noise and improving coherence, while strictly preserving the original meaning.

Original OCR text (may contain noise):
{ocr_text}

Machine translation (MarianMT):
{nmt_translation}

Instructions:
1. Correct any mistranslations caused by OCR errors in the original text
2. Improve contextual coherence and fluency
3. Preserve the exact meaning - do not add, remove, or change information
4. Maintain sentence order and structure
5. Do not invent content or make creative paraphrases
6. Prefer literal accuracy over creative rewriting
7. If the translation is already accurate, make minimal changes

Refined translation:"""
        
        return prompt
    
    def refine_translation_with_qwen(
        self, 
        nmt_translation: str, 
        ocr_text: str
    ) -> Optional[str]:
        """
        Refine MarianMT translation using local Qwen LLM.
        
        Takes both the original OCR text and MarianMT translation, then uses Qwen
        to correct OCR noise, improve coherence, and enhance fluency while preserving
        meaning and sentence structure.
        
        Args:
            nmt_translation: MarianMT translation output
            ocr_text: Original OCR-extracted Chinese text
            
        Returns:
            Refined translation string, or None if refinement fails
        """
        if not nmt_translation or not nmt_translation.strip():
            logger.debug("Empty MarianMT translation, skipping refinement")
            return None
        
        if not ocr_text or not ocr_text.strip():
            logger.debug("Empty OCR text, skipping refinement")
            return None
        
        if not self._available:
            logger.debug("Qwen refiner not available (transformers/torch not installed)")
            return None
        
        self._load_model()
        
        if not self._loaded or self.model is None or self.tokenizer is None:
            logger.warning("Qwen model not loaded, skipping refinement")
            return None
        
        try:
            # Detect sentence boundaries for logging/debugging
            sentences = self._detect_sentence_boundaries(ocr_text)
            if len(sentences) > 1:
                logger.debug(f"Detected {len(sentences)} sentences in OCR text")
            
            # Process full text with sentence awareness
            # Qwen will handle sentence-level refinement based on the prompt instructions
            prompt = self._create_refinement_prompt(ocr_text, nmt_translation)
            
            # Tokenize input
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # Format for Qwen chat template
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            model_inputs = self.tokenizer([text], return_tensors="pt").to(self.device)
            
            # Generate refined translation
            # Limit output length to prevent excessive generation
            max_new_tokens = min(len(nmt_translation.split()) * 2 + 50, 512)
            
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **model_inputs,
                    max_new_tokens=max_new_tokens,
                    temperature=0.3,  # Lower temperature for more deterministic output
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode response
            generated_ids = [
                output_ids[len(input_ids):] for input_ids, output_ids 
                in zip(model_inputs.input_ids, generated_ids)
            ]
            
            response = self.tokenizer.batch_decode(
                generated_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            )[0]
            
            # Clean up response (remove prompt artifacts if any)
            refined_translation = response.strip()
            
            # Basic validation: ensure we got a reasonable output
            if len(refined_translation) < len(nmt_translation) * 0.3:
                logger.warning("Refined translation seems too short, using MarianMT output")
                return None
            
            if len(refined_translation) > len(nmt_translation) * 3:
                logger.warning("Refined translation seems too long, truncating")
                refined_translation = refined_translation[:len(nmt_translation) * 2]
            
            logger.debug(f"Refined translation: {refined_translation[:100]}...")
            return refined_translation
            
        except Exception as e:
            logger.error(f"Qwen refinement error: {e}", exc_info=True)
            return None
    
    def is_available(self) -> bool:
        """
        Check if Qwen refinement is available.
        
        Returns:
            bool: True if transformers/torch available, False otherwise
        """
        return self._available and (
            AutoModelForCausalLM is not None and 
            AutoTokenizer is not None and 
            torch is not None
        )


def get_qwen_refiner() -> Optional[QwenRefiner]:
    """
    Get or create a singleton QwenRefiner instance.
    
    Returns:
        QwenRefiner instance (always returns instance, even if not available)
        Check is_available() to determine if it can be used
    """
    try:
        refiner = QwenRefiner()
        # Always return the refiner instance, even if not available
        # The caller can check is_available() to determine if it can be used
        return refiner
    except Exception as e:
        logger.error(f"Failed to initialize Qwen refiner: {e}")
        return None


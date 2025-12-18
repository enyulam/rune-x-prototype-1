"""
Rune-X Image Preprocessing Module

This module provides production-grade image preprocessing for OCR systems.
It implements a two-tier enhancement strategy:
  - Core enhancements (FATAL): Must succeed or raise exceptions
  - Optional enhancements (OPTIONAL): Fail gracefully with logging
"""

from .image_preprocessing import preprocess_image

__all__ = ['preprocess_image']


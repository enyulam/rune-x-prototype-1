# Platform Improvements Roadmap: Actionable Implementables

**Based on**: Advanced OCR Platform Comparison Analysis  
**Date**: December 2025  
**Status**: Planning Phase (No coding yet)

---

## Quick Reference: Top 3 Priority Improvements

1. **DBNet Text Detection** - +10-15% accuracy for irregular/vertical text
2. **ViT-OCR Recognition** - +10-15% accuracy for stylized/calligraphy text  
3. **Specialized OCR Error Correction** - +5-10% accuracy for character confusion

---

## Tier 1: High Impact, High Feasibility (Implement First)

### **Improvement 1.1: Integrate DBNet for Text Detection**

**What**: Replace or supplement CRAFT-based detection with DBNet (Differentiable Binarization Network)

**Why**: 
- Handles irregular/curved text (calligraphy columns) better than CRAFT
- Better accuracy on blurry/low-contrast handwritten text
- Supports vertical layouts natively

**How**:
- **Option A**: Extract DB detection from PaddleOCR (already uses DB internally)
- **Option B**: Integrate standalone DBNet (MMOCR library or PaddleOCR DB)
- **Option C**: Use PaddleOCR's text detection API separately

**Files to Modify**:
- `services/inference/ocr_fusion.py` - Add DBNet detection stage
- `services/inference/main.py` - Integrate DBNet into OCR pipeline
- `services/inference/requirements.txt` - Add DBNet dependencies

**Integration Points**:
- Current: `run_easyocr()` and `run_paddleocr()` in `ocr_fusion.py`
- New: `run_dbnet_detection()` → separate detection stage
- Fusion: Add DBNet detections to alignment pipeline

**Expected Outcome**:
- Detection accuracy: +10-15% for irregular/vertical text
- Better bounding boxes for curved text regions
- Foundation for modular detection-recognition pipeline

**Dependencies**: None (can coexist with current system)  
**Risk**: Low (can fallback to current detection)  
**Effort**: Medium (2-3 weeks)

---

### **Improvement 1.2: Add Transformer-Based Recognition (ViT-OCR)**

**What**: Add Vision Transformer OCR as third recognition engine for stylized text

**Why**:
- CRNN struggles with stylized text (seal script, cursive, calligraphy)
- Transformer self-attention captures global character patterns
- Better accuracy on non-standard fonts and handwritten variants

**How**:
- Integrate ViT-OCR model (available on HuggingFace)
- Add to fusion pipeline as third engine
- Use confidence-based routing (stylized text → ViT-OCR)

**Files to Create**:
- `services/inference/vit_ocr.py` - ViT-OCR wrapper module

**Files to Modify**:
- `services/inference/ocr_fusion.py` - Add ViT-OCR to fusion pipeline
- `services/inference/main.py` - Initialize ViT-OCR engine
- `services/inference/requirements.txt` - Add ViT-OCR dependencies

**Integration Points**:
- Current: `fuse_character_candidates()` accepts EasyOCR + PaddleOCR
- New: Add ViT-OCR results to fusion pipeline
- Strategy: Use ViT-OCR for low-confidence CRNN results or stylized text detection

**Expected Outcome**:
- Recognition accuracy: +10-15% for stylized/calligraphy text
- Better handling of seal script and cursive variants
- Three-engine fusion (EasyOCR + PaddleOCR + ViT-OCR)

**Dependencies**: Transformers library (already installed)  
**Risk**: Medium (new model adds complexity)  
**Effort**: Medium-High (3-4 weeks)

---

### **Improvement 1.3: Specialized Chinese LLM for OCR Error Correction**

**What**: Replace general-purpose Qwen with specialized Chinese LLM for OCR error correction

**Why**:
- Qwen is general-purpose (not optimized for OCR errors)
- Need specialized handling for similar character confusion (己/已/巳)
- Better semantic context for character replacement

**How**:
- **Option A**: Fine-tune Qwen on OCR error patterns (requires training data)
- **Option B**: Use specialized Chinese LLM (Chinese-BERT, Chinese-GPT, or similar)
- **Option C**: Create prompt-based system with Qwen for OCR error correction (quick win)

**Files to Create**:
- `services/inference/ocr_error_corrector.py` - Specialized OCR error correction module

**Files to Modify**:
- `services/inference/main.py` - Replace Qwen refiner with OCR error corrector
- `services/inference/qwen_refiner.py` - Extend or replace with specialized version

**Integration Points**:
- Current: Qwen refines MarianMT translation (line 744 in `main.py`)
- New: OCR error corrector fixes OCR text before translation
- Strategy: Run error correction after OCR fusion, before translation

**Expected Outcome**:
- Error correction accuracy: +5-10% for character confusion
- Better handling of similar characters (己/已/巳)
- Layout restoration (vertical right-to-left order)

**Dependencies**: Training data (for Option A) or specialized model (for Option B)  
**Risk**: Medium-High (requires validation)  
**Effort**: High (4-6 weeks for Option A/B), Low-Medium (1-2 weeks for Option C)

**Recommendation**: Start with **Option C** (prompt-based) for quick win, then move to Option A/B

---

## Tier 2: High Impact, Medium Feasibility (Implement Second)

### **Improvement 2.1: Fine-Tune Recognition Models on Chinese Calligraphy**

**What**: Fine-tune CRNN/ViT-OCR on Chinese calligraphy dataset

**Why**:
- Current models are general-purpose (not optimized for calligraphy)
- Calligraphy variants (seal script, cursive) need specialized training
- Handwritten samples differ from printed text

**How**:
- Collect Chinese calligraphy dataset (seal script, cursive, traditional)
- Fine-tune CRNN or ViT-OCR on calligraphy samples
- Create calligraphy-specific model variant

**Files to Create**:
- `services/inference/scripts/finetune_calligraphy.py` - Fine-tuning script
- `services/inference/data/calligraphy_dataset/` - Dataset directory

**Files to Modify**:
- `services/inference/ocr_fusion.py` - Add calligraphy model routing
- `services/inference/main.py` - Load calligraphy-specific models

**Expected Outcome**:
- Calligraphy accuracy: +15-20%
- Better handling of traditional characters and variants
- Specialized model for artistic text

**Dependencies**: Calligraphy dataset, GPU resources, fine-tuning pipeline  
**Risk**: Medium (dataset quality critical)  
**Effort**: High (6-8 weeks)

---

### **Improvement 2.2: Modular Detection-Recognition Pipeline**

**What**: Separate detection from recognition for better flexibility

**Why**:
- Current engines combine detection+recognition (not modular)
- Can't optimize each stage independently
- Harder to swap models or add new detection/recognition engines

**How**:
- Refactor OCR engines to separate detection from recognition
- Create modular pipeline: Detection → Recognition → Fusion
- Allow independent model swapping

**Files to Refactor**:
- `services/inference/ocr_fusion.py` - Separate detection/recognition stages
- `services/inference/main.py` - Modular pipeline orchestration

**Files to Create**:
- `services/inference/detection/` - Detection module directory
- `services/inference/recognition/` - Recognition module directory

**Expected Outcome**:
- Better maintainability and flexibility
- Easier to add new models
- +5% accuracy from optimized stages

**Dependencies**: Refactoring OCR fusion module  
**Risk**: Medium (may break existing functionality)  
**Effort**: Medium-High (3-4 weeks)

---

### **Improvement 2.3: Layout Restoration (Vertical Right-to-Left)**

**What**: Detect and restore correct reading order for vertical Chinese text

**Why**:
- Traditional Chinese text is vertical right-to-left
- Current system assumes horizontal left-to-right
- Important for correct translation and user experience

**How**:
- Detect text direction (horizontal vs vertical)
- Detect reading order (left-to-right vs right-to-left)
- Restore correct reading order in post-processing

**Files to Create**:
- `services/inference/layout_detector.py` - Layout detection module

**Files to Modify**:
- `services/inference/ocr_fusion.py` - Add layout detection to fusion
- `services/inference/main.py` - Apply layout restoration

**Expected Outcome**:
- Correct reading order for vertical text
- Better user experience
- Accurate translation order

**Dependencies**: Layout detection model or heuristics  
**Risk**: Low-Medium (can be rule-based initially)  
**Effort**: Medium (2-3 weeks)

---

## Tier 3: Medium Impact, Variable Feasibility (Polish & Optimization)

### **Improvement 3.1: Integrate OCR Error Correction into Recognition Stage**

**What**: Run error correction during recognition (not just post-processing)

**Why**:
- Corrections happen earlier in pipeline
- Better accuracy (corrected text used for fusion)
- More efficient (single pass)

**How**:
- Run Chinese LLM on OCR candidates before fusion
- Use LLM to correct character-level errors
- Integrate corrections into fusion pipeline

**Files to Modify**:
- `services/inference/ocr_fusion.py` - Add error correction to fusion
- `services/inference/ocr_error_corrector.py` - Integrate into recognition

**Expected Outcome**:
- +3-5% accuracy from earlier corrections
- More efficient pipeline

**Dependencies**: Specialized Chinese LLM (from 1.3)  
**Risk**: Medium (adds latency)  
**Effort**: Medium-High (3-4 weeks)

---

### **Improvement 3.2: Multi-Scale Text Detection**

**What**: Detect text at multiple resolutions for varying text sizes

**Why**:
- Text sizes vary in images (small annotations, large headings)
- Single-scale detection misses small or large text
- Multi-scale improves coverage

**How**:
- Use DBNet's multi-scale detection capabilities
- Detect text at multiple resolutions
- Merge multi-scale detections

**Files to Modify**:
- `services/inference/ocr_fusion.py` - Add multi-scale detection
- `services/inference/main.py` - Configure multi-scale parameters

**Expected Outcome**:
- +3-5% accuracy for varying text sizes
- Better coverage of small/large text

**Dependencies**: DBNet integration (from 1.1)  
**Risk**: Low  
**Effort**: Low-Medium (1-2 weeks)

---

### **Improvement 3.3: Confidence-Based Model Routing**

**What**: Route text to appropriate model based on characteristics

**Why**:
- Different models excel at different text types
- Optimize model selection for efficiency and accuracy
- Better resource utilization

**How**:
- Detect text characteristics (stylized, handwritten, printed)
- Route to appropriate model (CRNN for sequences, ViT-OCR for stylized)
- Use confidence scores to select best model

**Files to Create**:
- `services/inference/model_router.py` - Model routing logic

**Files to Modify**:
- `services/inference/ocr_fusion.py` - Add routing to fusion
- `services/inference/main.py` - Configure routing strategy

**Expected Outcome**:
- +2-3% accuracy from optimized routing
- Better efficiency (use best model for each case)

**Dependencies**: Multiple recognition models (from 1.2)  
**Risk**: Low  
**Effort**: Low-Medium (1-2 weeks)

---

## Implementation Priority Matrix

| Improvement | Impact | Feasibility | Priority | Phase |
|------------|--------|-------------|----------|-------|
| 1.1 DBNet Detection | High | High | **1** | Phase 1 |
| 1.2 ViT-OCR Recognition | High | Medium-High | **2** | Phase 1 |
| 1.3 OCR Error Correction | High | Medium | **3** | Phase 1 |
| 2.1 Calligraphy Fine-tuning | High | Medium | **4** | Phase 2 |
| 2.2 Modular Pipeline | Medium | Medium | **5** | Phase 2 |
| 2.3 Layout Restoration | Medium | Medium | **6** | Phase 2 |
| 3.1 Error Correction Integration | Medium | Medium | **7** | Phase 3 |
| 3.2 Multi-Scale Detection | Medium | High | **8** | Phase 3 |
| 3.3 Model Routing | Medium | High | **9** | Phase 3 |

---

## Recommended Implementation Order

### **Phase 1: Quick Wins (1-2 months)**
1. ✅ **1.1 DBNet Detection** - Highest ROI, low risk
2. ✅ **1.2 ViT-OCR Recognition** - High impact, manageable effort
3. ✅ **1.3 OCR Error Correction (Option C)** - Quick win with existing Qwen

### **Phase 2: Specialization (2-3 months)**
4. ✅ **2.1 Calligraphy Fine-tuning** - Requires dataset collection
5. ✅ **2.2 Modular Pipeline** - Foundation for future improvements
6. ✅ **2.3 Layout Restoration** - User experience improvement

### **Phase 3: Advanced Integration (3-4 months)**
7. ✅ **3.1 Error Correction Integration** - Polish and optimization
8. ✅ **3.2 Multi-Scale Detection** - Coverage improvement
9. ✅ **3.3 Model Routing** - Efficiency optimization

---

## Compatibility with Phase 5 (MarianMT Refactoring)

✅ **All improvements are compatible** with Phase 5:

- **DBNet/ViT-OCR**: Improve OCR accuracy → Better input for MarianMT
- **OCR Error Correction**: Happens before MarianMT → Cleaner input
- **Layout Restoration**: Preserves reading order → Better context for MarianMT
- **Modular Pipeline**: Easier to integrate MarianMT constraints

**Recommendation**: Complete Phase 5 first, then implement Tier 1 improvements.

---

## Success Metrics

### **Current Baseline**
- Handwritten Chinese text accuracy: **~70%**
- Calligraphy/stylized text accuracy: **~60%**
- Irregular/vertical text accuracy: **~65%**

### **Target After Phase 1**
- Handwritten Chinese text accuracy: **~80-85%** (+10-15%)
- Calligraphy/stylized text accuracy: **~75-80%** (+15-20%)
- Irregular/vertical text accuracy: **~80-85%** (+15-20%)

### **Target After Phase 2**
- Handwritten Chinese text accuracy: **~85-90%** (+15-20%)
- Calligraphy/stylized text accuracy: **~85-90%** (+25-30%)
- Irregular/vertical text accuracy: **~85-90%** (+20-25%)

### **Target After Phase 3**
- Handwritten Chinese text accuracy: **~90-95%** (+20-25%)
- Calligraphy/stylized text accuracy: **~90-95%** (+30-35%)
- Irregular/vertical text accuracy: **~90-95%** (+25-30%)

---

## Next Steps

1. ✅ **Review and approve** this roadmap
2. ✅ **Prioritize improvements** based on project needs
3. ✅ **Create detailed implementation plans** for Phase 1 improvements
4. ✅ **Set up development environment** for new models
5. ✅ **Begin Phase 1 implementation** (after Phase 5 completion)

---

## Notes

- All improvements can be implemented **incrementally** without breaking existing functionality
- Each improvement includes **fallback mechanisms** to current system
- **Testing and validation** required for each improvement before production
- **Performance monitoring** needed to track accuracy improvements
- **Documentation updates** required for each new feature


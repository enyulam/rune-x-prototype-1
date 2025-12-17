# 🚀 Rune-X

**Interpreting the Past. Empowering the Future.**

An advanced multimodal AI platform for ancient script interpretation, reconstruction, and semantic analysis. Built with Next.js, TypeScript, and modern web technologies.

## 🚧 Current Status

**Hybrid OCR System**: The platform uses a dual-engine OCR approach combining EasyOCR and PaddleOCR for enhanced accuracy and reliability.

**Three-Tier Translation System**: The platform provides character-level dictionary translation, neural sentence translation (MarianMT), and LLM refinement (Qwen) for comprehensive translation coverage.

The platform uses a FastAPI backend service with a **hybrid OCR system** that runs both EasyOCR and PaddleOCR in parallel, then fuses their outputs at the character level. This approach provides:
- **Dual OCR Engines**: EasyOCR (Chinese Simplified + English) and PaddleOCR (Chinese) run simultaneously
- **Character-Level Fusion**: Results from both engines are aligned using IoU-based matching and fused, preserving all character candidates
- **Enhanced Accuracy**: Multiple hypotheses per character position improve recognition of difficult or stylized text
- **Robust Image Preprocessing**: Comprehensive 9-step preprocessing pipeline (format validation, dimension checks, resizing, RGB conversion, upscaling, contrast/sharpness enhancement, adaptive padding) optimizes images for OCR
- **Three-Tier Translation System**: 
  - **Dictionary-Based Translation**: Custom Chinese character dictionary with 276+ entries (character-level meanings)
  - **Neural Sentence Translation**: MarianMT model for context-aware, natural English sentence translation
  - **LLM Refinement**: Qwen2.5-1.5B-Instruct model for refining translations, correcting OCR noise, and improving coherence

**Key Features**:
- Parallel OCR processing for faster results
- Character-level uncertainty preservation (all candidates kept)
- Reading order sorting (top-to-bottom, left-to-right)
- Comprehensive error handling and fallback mechanisms

**Note**: The hybrid system significantly improves accuracy over single-engine approaches. See `QUICK_START_GUIDE.md` for detailed setup instructions.

## ✨ Overview

Rune-X is a production-grade, multimodal artificial intelligence platform designed to automate the interpretation of ancient scripts and inscriptions. It addresses the critical gap between digitised heritage content and the ability to interpret, annotate, and make this content usable.

### Core Architecture

Rune-X integrates three technically robust components:

1. **Glyph Tokenisation Engine (GTE)** - Isolates and represents individual glyphs from irregular or damaged inscriptions
2. **Semantic Transformer Model (STM)** - Infers phonetic, semantic, or structural meaning from visual and contextual cues
3. **Generative Reconstruction Module (GRM)** - Restores damaged glyphs using evidence-driven synthesis techniques

## ✨ Technology Stack

### 🎯 Core Framework
- **⚡ Next.js 15** - The React framework for production with App Router
- **📘 TypeScript 5** - Type-safe JavaScript for better developer experience
- **🎨 Tailwind CSS 4** - Utility-first CSS framework for rapid UI development

### 🧩 UI Components & Styling
- **🧩 shadcn/ui** - High-quality, accessible components built on Radix UI
- **🎯 Lucide React** - Beautiful & consistent icon library
- **🌈 Framer Motion** - Production-ready motion library for React
- **🎨 Next Themes** - Perfect dark mode in 2 lines of code

### 📋 Forms & Validation
- **🎣 React Hook Form** - Performant forms with easy validation
- **✅ Zod** - TypeScript-first schema validation

### 🔄 State Management & Data Fetching
- **🐻 Zustand** - Simple, scalable state management
- **🔄 TanStack Query** - Powerful data synchronization for React
- **🌐 Axios** - Promise-based HTTP client

### 🗄️ Database & Backend
- **🗄️ Prisma** - Next-generation Node.js and TypeScript ORM
- **🔐 NextAuth.js** - Complete open-source authentication solution
- **🐍 FastAPI** - Modern Python web framework for OCR inference service
- **👁️ Hybrid OCR System** - EasyOCR + PaddleOCR running in parallel with character-level fusion
  - **EasyOCR** - Chinese Simplified (`ch_sim`) and English support
  - **PaddleOCR** - Chinese text recognition with advanced models
- **🌐 Neural Translation** - MarianMT (transformers) for sentence-level translation
  - **Model**: Helsinki-NLP/opus-mt-zh-en (Chinese → English)
  - **Lazy Loading**: Model downloads automatically on first use (~300MB)
- **🤖 LLM Refinement** - Qwen2.5-1.5B-Instruct for translation refinement
  - **Purpose**: Corrects OCR noise, improves coherence, enhances fluency
  - **Lazy Loading**: Model downloads automatically on first use (~3GB from HuggingFace)
  - **Dependencies**: transformers, accelerate (for CUDA device mapping)

### 🎨 Advanced UI Features
- **📊 TanStack Table** - Headless UI for building tables and datagrids
- **🖱️ DND Kit** - Modern drag and drop toolkit for React
- **📊 Recharts** - Redefined chart library built with React and D3
- **🖼️ Sharp** - High performance image processing

### 🌍 Internationalization & Utilities
- **🌍 Next Intl** - Internationalization library for Next.js
- **📅 Date-fns** - Modern JavaScript date utility library
- **🪝 ReactUse** - Collection of essential React hooks for modern development

## 🚀 Quick Start

### Prerequisites

- **Node.js 18+** and npm
- **Python 3.8+** and pip
- **SQLite** (included with Node.js)
- **PyTorch** (for EasyOCR, transformers, and Qwen - CPU version is fine, install separately)
- **PaddlePaddle** (for PaddleOCR - CPU version, installed via requirements.txt)
- **Transformers** (for MarianMT sentence translation and Qwen refinement - installed via requirements.txt)
- **Accelerate** (for Qwen CUDA device mapping - installed via requirements.txt)

### Setup

1. **Install frontend dependencies:**
```bash
npm install
```

2. **Install backend dependencies:**
```bash
cd services/inference
pip install -r requirements.txt
cd ../..
```

3. **Set up environment variables:**
Create a `.env` file in the project root:
```env
DATABASE_URL="file:./prisma/db/dev.db"
NEXTAUTH_URL="http://localhost:3001"
NEXTAUTH_SECRET="your-secret-key-here"
INFERENCE_API_URL="http://localhost:8001"
```
Generate a secure `NEXTAUTH_SECRET` with: `openssl rand -base64 32`

4. **Initialize the database:**
```bash
npm run db:generate
npm run db:push
npm run db:seed
```

5. **Start the backend service (in a separate terminal):**
```bash
cd services/inference
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

6. **Start the frontend development server:**
```bash
npm run dev
```

7. **Open your browser:**
Navigate to [http://localhost:3001](http://localhost:3001)

**Note**: Both servers must be running for the platform to function. The frontend runs on port 3001 and the backend OCR service runs on port 8001.

### Demo Account

For testing, you can use the demo account:
- **Email:** demo@projectdecypher.com
- **Password:** demo123

## 🔐 Authentication

The application uses NextAuth.js for authentication with credentials provider:

- **Sign Up:** `/auth/register` - Create a new account
- **Sign In:** `/auth/login` - Sign in to your account
- **Dashboard:** `/dashboard` - View your uploads and statistics
- **Protected Routes:** Upload and translations pages require authentication

## 📁 Project Structure

```
src/
├── app/
│   ├── api/
│   │   ├── auth/          # NextAuth authentication routes
│   │   ├── upload/         # File upload endpoint
│   │   ├── process/        # Text processing endpoint
│   │   ├── translations/   # Translations API
│   │   └── dashboard/      # Dashboard stats API
│   ├── auth/              # Authentication pages (login, register)
│   ├── dashboard/         # User dashboard
│   ├── upload/            # File upload page
│   ├── translations/      # Translations library
│   └── page.tsx           # Homepage
├── components/
│   ├── providers/         # React providers (Session)
│   └── ui/                # shadcn/ui components
├── lib/
│   ├── auth.ts            # NextAuth configuration
│   ├── db.ts              # Prisma client
│   ├── ai-processor.ts    # AI processing service
│   └── get-session.ts     # Server session helper
└── types/
    └── next-auth.d.ts     # NextAuth type definitions
```

## 🗄️ Database

The project uses Prisma ORM with SQLite. Key models:

- **User** - User accounts with authentication
- **Upload** - Uploaded files and their processing status
- **AncientScript** - Supported ancient scripts
- **Glyph** - Individual glyphs/symbols
- **GlyphMatch** - Matched glyphs in uploads
- **Translation** - Translation results
- **Feedback** - User feedback on translations

### Database Commands

```bash
# Push schema changes to database
npm run db:push

# Generate Prisma Client
npm run db:generate

# Run migrations
npm run db:migrate

# Seed database with sample data
npm run db:seed

# Reset database (WARNING: deletes all data)
npm run db:reset
```

## ✨ Features

### Core Functionality

- **🔐 User Authentication** - Secure sign up and login with NextAuth.js
- **📤 File Upload** - Upload images of ancient manuscripts and inscriptions
- **🤖 AI Processing** - Automated glyph recognition and tokenization
- **🔍 Glyph Tokenisation** - Advanced segmentation of irregular glyphs
- **🧠 Semantic Analysis** - Context-aware interpretation of ancient scripts
- **🔧 Generative Reconstruction** - Restoration of damaged or incomplete glyphs
- **📖 Translation** - Three-tier translation system:
  - **Character Meanings**: Dictionary-based per-character translations
  - **Full Sentence Translation**: Neural context-aware translation using MarianMT
  - **Refined Translation**: Qwen LLM refinement for improved coherence and OCR noise correction
- **🎨 Translation UI** - Displays all three translation types in distinct sections:
  - Character Meanings (gray background) - Dictionary-based character-level meanings
  - Full Sentence Translation (blue background) - MarianMT neural translation
  - Refined Translation (green background) - Qwen-refined translation with status indicators
- **📊 Dashboard** - User dashboard with statistics and activity
- **📚 Translation Library** - Browse and search your translations
- **📤 Export Capabilities** - Export in TEI-XML, JSON-LD formats
- **🎨 Modern UI** - Beautiful, responsive interface with dark mode support
- **🧪 Testing** - Pipeline smoke tests for end-to-end verification

### Technical Features

- **Type Safety** - Full TypeScript coverage
- **Form Validation** - Zod schema validation with React Hook Form
- **Protected Routes** - Authentication-based route protection
- **Database ORM** - Prisma for type-safe database access
- **Responsive Design** - Mobile-first design with Tailwind CSS
- **Component Library** - shadcn/ui for consistent UI components
- **Metadata Tracking** - Provenance and version control
- **Batch Processing** - Process multiple files simultaneously

## 🛠️ Development

### Environment Variables

Required (app + DB):
```env
DATABASE_URL="file:./prisma/db/dev.db"
NEXTAUTH_URL="http://localhost:3001"
NEXTAUTH_SECRET="your-secret-key-here"
INFERENCE_API_URL="http://localhost:8001"
```

### Backend OCR Service

The OCR service runs as a separate FastAPI application:

```bash
# Start the OCR inference service
cd services/inference
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

The service uses a **hybrid OCR system** combining EasyOCR and PaddleOCR engines that run in parallel on the same preprocessed image. Results are fused at the character level using IoU-based alignment, preserving all character hypotheses from both engines.

**Key Features:**
- **Dual OCR Engines**: EasyOCR (ch_sim + en) and PaddleOCR (ch) run simultaneously
- **Character-Level Fusion**: Results aligned using bounding box overlap (IoU) and fused with all candidates preserved
- **Parallel Processing**: Both engines process images concurrently for faster results
- **Comprehensive Image Preprocessing**: 9-step pipeline including format validation, dimension checks, resizing, RGB conversion, upscaling, contrast/sharpness enhancement, and adaptive padding for optimal OCR accuracy
- **Three-Tier Translation System**:
  - **Dictionary-Based Translation**: 276+ Chinese character entries with meanings, alternatives, and notes (character-level)
  - **Neural Sentence Translation**: MarianMT model for context-aware, natural English translation (sentence-level)
  - **LLM Refinement**: Qwen2.5-1.5B-Instruct model for refining MarianMT translations, correcting OCR noise, and improving coherence
- **Robust Error Handling**: Graceful fallback if one engine fails, comprehensive error messages
- **Reading Order Preservation**: Characters sorted top-to-bottom, left-to-right

**OCR Engine Details:**
- **EasyOCR**: Chinese Simplified (`ch_sim`) and English (`en`) language support
- **PaddleOCR**: Chinese text recognition with PP-OCRv5 models (detection + recognition)
- **Fusion Algorithm**: IoU-based alignment with configurable threshold (default: 0.3)

### Building for Production

```bash
# Build the application
npm run build

# Start production server
npm start
```

The build output is optimized for standalone deployment.

## 🎯 Supported Scripts

Rune-X is designed to support multiple ancient scripts:

- **Oracle Bone Script** (甲骨文) - Ancient Chinese inscriptions
- **Bronze Script** (金文) - Bronze vessel inscriptions
- **Seal Script** (篆书) - Ancient Chinese seal script
- **Traditional Chinese** - Classical Chinese texts
- **Classical Latin** - Ancient Roman inscriptions
- **Ancient Greek** - Classical Greek texts
- **Cuneiform** - Ancient Mesopotamian writing
- **Hieroglyphs** - Egyptian hieroglyphic systems

## 📝 License

This project is part of the Rune-X initiative by Zhicong Technology.

## 🤝 Contributing

This is a project for ancient language decryption and cultural heritage preservation. Contributions that improve accuracy, add new script support, or enhance the user experience are welcome.

---

**Rune-X** - Interpreting the past. Empowering the future. 🚀

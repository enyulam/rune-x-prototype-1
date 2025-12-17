# GitHub Repository Setup Guide

This guide will help you upload the Rune-X project to GitHub as a new repository.

## Prerequisites

- Git installed on your system
- GitHub account
- GitHub CLI (`gh`) installed (optional, but recommended) OR GitHub web interface access

## Step-by-Step Instructions

### Option 1: Using GitHub CLI (Recommended - Faster)

1. **Install GitHub CLI** (if not already installed):
   ```bash
   # Windows (using winget or chocolatey)
   winget install GitHub.cli
   # OR
   choco install gh
   ```

2. **Login to GitHub**:
   ```bash
   gh auth login
   ```

3. **Initialize Git repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Rune-X Chinese OCR & Translation Platform"
   ```

4. **Create repository on GitHub and push**:
   ```bash
   gh repo create rune-x --public --source=. --remote=origin --push
   ```
   
   Or for a private repository:
   ```bash
   gh repo create rune-x --private --source=. --remote=origin --push
   ```

### Option 2: Using GitHub Web Interface (Manual)

1. **Initialize Git repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Rune-X Chinese OCR & Translation Platform"
   ```

2. **Create repository on GitHub**:
   - Go to https://github.com/new
   - Repository name: `rune-x` (or your preferred name)
   - Description: "Chinese handwriting OCR and translation platform with EasyOCR and dictionary-based translation"
   - Choose Public or Private
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
   - Click "Create repository"

3. **Connect local repository to GitHub**:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/rune-x.git
   git branch -M main
   git push -u origin main
   ```
   
   Replace `YOUR_USERNAME` with your GitHub username.

### Option 3: Using SSH (If you have SSH keys set up)

1. **Initialize Git repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Rune-X Chinese OCR & Translation Platform"
   ```

2. **Create repository on GitHub** (same as Option 2, step 2)

3. **Connect using SSH**:
   ```bash
   git remote add origin git@github.com:YOUR_USERNAME/rune-x.git
   git branch -M main
   git push -u origin main
   ```

## Verification

After pushing, verify your repository:
- Visit `https://github.com/YOUR_USERNAME/rune-x`
- Check that all files are present
- Verify README.md displays correctly

## Important Notes

### Files NOT Uploaded (by .gitignore):
- `node_modules/` - Dependencies (users will run `npm install`)
- `.env` - Environment variables (users create their own)
- `prisma/db/*.db` - Database files (users generate their own)
- `uploads/` - User-uploaded images
- Python cache files (`__pycache__/`)

### Files That ARE Uploaded:
- All source code
- `package.json` and `requirements.txt` (dependency lists)
- `README.md` (updated with current platform status)
- `.gitignore` (comprehensive ignore rules)
- Configuration files
- Documentation files

## Post-Upload Checklist

- [ ] Verify README.md displays correctly on GitHub
- [ ] Add repository description and topics on GitHub
- [ ] Consider adding a LICENSE file (if needed)
- [ ] Update repository settings (enable Issues, Wiki, etc. if desired)
- [ ] Consider adding GitHub Actions for CI/CD (optional)

## Repository Topics (Recommended)

Add these topics to your GitHub repository for better discoverability:
- `ocr`
- `chinese-handwriting`
- `easyocr`
- `nextjs`
- `fastapi`
- `chinese-translation`
- `ancient-scripts`
- `typescript`
- `python`

## Next Steps

After uploading:
1. Share the repository URL with collaborators
2. Consider adding a CONTRIBUTING.md file
3. Set up branch protection rules (if working with a team)
4. Consider adding GitHub Actions for automated testing


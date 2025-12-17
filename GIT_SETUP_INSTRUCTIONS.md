# Git Setup Instructions for Beginners

## Step 1: Configure Git Identity

Git needs to know who you are for commits. Run these commands in your terminal:

### Set Your Name:
```bash
git config --global user.name "Your Name"
```

**Example:**
```bash
git config --global user.name "John Doe"
```
or
```bash
git config --global user.name "enyul"
```

### Set Your Email:
```bash
git config --global user.email "your.email@example.com"
```

**Example:**
```bash
git config --global user.email "john.doe@gmail.com"
```

**Important Notes:**
- Use `--global` to set it for all repositories on your computer
- Use your GitHub email if you have a GitHub account (or plan to create one)
- This email will be visible in commit history
- You can change it later if needed

### Verify Your Configuration:
After setting, verify it worked:
```bash
git config --global user.name
git config --global user.email
```

These commands should show what you just set.

## Step 2: Create Your First Commit

After configuring Git, create your initial commit:

```bash
git commit -m "Initial commit: Rune-X Chinese OCR & Translation Platform"
```

**What this does:**
- `git commit` - Creates a snapshot of your current code
- `-m "message"` - Adds a message describing what this commit contains
- This saves all the files you've staged (which we already did with `git add .`)

## What's Next?

After completing Step 1 and Step 2, you'll be ready to upload to GitHub (Step 3).



# Karma App

## 🔒 Security & Environment Protection

This project has **100% protection** against accidental `.env` file commits:

### 1. Git Hook Protection
- **Pre-commit hook** automatically blocks any commit containing `.env` files
- Hook is located at `.git/hooks/pre-commit`
- Scans for patterns: `.env`, `.env.*`, `frontend/.env`, `backend/.env`

### 2. .gitignore Protection  
- Comprehensive `.env` patterns in `.gitignore`
- Covers all environment file variations

### 3. Template Files
- Use `.env.example` files for sharing configuration templates
- **Never commit actual `.env` files with sensitive data**

### Setup Instructions
1. Copy `.env.example` to `.env`
2. Fill in your actual values
3. The git hook will prevent accidental commits

### If Hook Blocks Your Commit
```bash
# Remove .env files from staging
git reset HEAD .env
git reset HEAD frontend/.env

# Or remove from git entirely
git rm --cached .env
```

## Development Setup

<!-- Rest of README content --> 
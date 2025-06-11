# 🛡️ KARMA APP SECURITY GUIDE

## 🚨 CRITICAL: Never Commit These Files!

### 🔑 Authentication & Keys
- `*.session` - Telegram session files (direct account access!)
- `id_rsa`, `*.pem`, `*.key` - SSH keys and certificates
- `service-account.json` - Cloud service credentials
- `keystore.jks`, `*.p12` - Keystores and certificates

### 💾 Database & Sensitive Data
- `*.sql`, `*.db`, `*.sqlite` - Database dumps with real data
- `backup.sql`, `dump.sql` - Database backups
- `*.log` - Log files with potential tokens/passwords

### ⚙️ Configuration Files
- `.env`, `.env.*` - Environment files with secrets
- `config/production.py` - Production configs with hardcoded secrets
- `docker-compose.override.yml` - Local docker overrides

## 🔒 Security Measures in Place

### 1. Pre-commit Hook Protection
Our enhanced pre-commit hook scans for:
- ✅ All environment files (`.env*`)
- ✅ SSH keys and certificates
- ✅ Database files and dumps
- ✅ Telegram session files
- ✅ Hardcoded secrets in code
- ✅ API keys and tokens
- ✅ URLs with embedded credentials

### 2. Comprehensive .gitignore
Protects against 50+ types of sensitive files

### 3. Template Files
Use these safe templates:
- `.env.example` - Environment variables template
- `docker-compose.example.yml` - Docker configuration template

## 🔧 How to Handle Secrets Safely

### Environment Variables
```bash
# ❌ NEVER do this:
API_KEY = "sk-1234567890abcdef"

# ✅ DO this:
API_KEY = os.getenv('API_KEY')
```

### Database Connections
```bash
# ❌ NEVER do this:
DATABASE_URL = "postgresql://user:password@localhost/db"

# ✅ DO this:
DATABASE_URL = os.getenv('DATABASE_URL')
```

### Docker Compose
```yaml
# ❌ NEVER do this:
environment:
  - POSTGRES_PASSWORD=mysecretpassword

# ✅ DO this:
environment:
  - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
```

## 🚑 Emergency: If Secrets Were Committed

### 1. Immediate Actions
```bash
# Remove from staging immediately
git reset HEAD <sensitive-file>

# If already committed, remove from history
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch <sensitive-file>' \
  --prune-empty --tag-name-filter cat -- --all

# Force push (DANGEROUS - coordinate with team!)
git push origin --force --all
git push origin --force --tags
```

### 2. Rotate All Exposed Secrets
- 🔄 Change all passwords
- 🔄 Regenerate API keys
- 🔄 Revoke access tokens
- 🔄 Update Telegram sessions

### 3. Audit Access Logs
- Check who had access to the repository
- Review recent logins to affected services
- Monitor for suspicious activity

## 📋 Security Checklist

Before each commit:
- [ ] No `.env` files staged
- [ ] No database dumps with real data
- [ ] No hardcoded passwords/keys in code
- [ ] No session files
- [ ] No SSH keys or certificates
- [ ] All configs use environment variables

## 🛠️ Development Best Practices

### Local Development Setup
1. Copy templates: `cp .env.example .env`
2. Fill in your local values
3. Never commit the actual `.env` file

### Production Deployment
1. Use secret management systems (AWS Secrets Manager, etc.)
2. Environment variables injection at runtime
3. Regular secret rotation
4. Audit logs for secret access

### Code Reviews
- Always review for hardcoded secrets
- Check for new sensitive file patterns
- Verify environment variable usage

## 🆘 Getting Help

If you suspect a security issue:
1. **DO NOT** commit or push anything
2. Contact the security team immediately
3. Follow the incident response plan

Remember: **Security is everyone's responsibility!** 
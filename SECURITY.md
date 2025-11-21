# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 5.2.x   | :white_check_mark: |
| 5.1.x   | :white_check_mark: |
| 5.0.x   | :x:                |
| < 5.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please follow these steps:

### 1. Do Not Disclose Publicly

Please do not open a public issue or discuss the vulnerability in public forums until it has been addressed.

### 2. Report Privately

Send a detailed report to: **ayushjaipuriyar21@gmail.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)
- Your contact information

### 3. Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: 1-7 days
  - High: 7-14 days
  - Medium: 14-30 days
  - Low: 30-90 days

### 4. Disclosure Process

1. We will confirm receipt of your report
2. We will investigate and validate the issue
3. We will develop and test a fix
4. We will release a security patch
5. We will publicly disclose the vulnerability after the patch is released

## Security Best Practices

### For Users

1. **Keep Updated**: Always use the latest version
2. **Verify Downloads**: Check package signatures when possible
3. **Use Virtual Environments**: Isolate the application
4. **Review Permissions**: Check file system access
5. **Secure Configuration**: Protect your config files

### For Developers

1. **Input Validation**: Validate all user inputs
2. **Dependency Updates**: Keep dependencies current
3. **Code Review**: Review security-sensitive code
4. **Secrets Management**: Never commit secrets
5. **Least Privilege**: Run with minimum required permissions

## Known Security Considerations

### SSL/TLS

The application includes an `--insecure` flag that disables SSL certificate verification. This should only be used when absolutely necessary and you understand the risks.

**Risks:**
- Man-in-the-middle attacks
- Data interception
- Compromised downloads

**Recommendation:** Only use `--insecure` in controlled environments or when certificate issues are known and acceptable.

### File System Access

The application writes files to disk. Ensure:
- Download directory has appropriate permissions
- Sufficient disk space is available
- Path traversal attacks are prevented (handled by `sanitize_filename`)

### Network Requests

The application makes HTTP requests to external services:
- Uses connection pooling for efficiency
- Implements retry logic with backoff
- Respects rate limits
- Validates URLs before requests

### Dependencies

We regularly update dependencies to patch security vulnerabilities:
- Automated dependency updates via Dependabot
- Security scanning in CI/CD pipeline
- Regular security audits with `safety` and `bandit`

## Security Features

### Implemented Protections

1. **Input Sanitization**: All filenames are sanitized to prevent path traversal
2. **Rate Limiting**: Built-in rate limiting for API calls
3. **Timeout Handling**: Network requests have timeouts
4. **Error Handling**: Graceful error handling prevents information leakage
5. **Logging**: Security-relevant events are logged

### Planned Improvements

- [ ] Add checksum verification for downloads
- [ ] Implement signature verification for updates
- [ ] Add sandboxing options
- [ ] Enhance logging for security events
- [ ] Add security headers for GUI

## Vulnerability Disclosure Policy

### Scope

In scope:
- Remote code execution
- SQL injection (if applicable)
- Cross-site scripting (if applicable)
- Authentication bypass
- Privilege escalation
- Information disclosure
- Denial of service

Out of scope:
- Social engineering attacks
- Physical attacks
- Issues in dependencies (report to upstream)
- Issues requiring physical access

### Recognition

We appreciate security researchers who help keep our project safe:
- Public acknowledgment (if desired)
- Credit in release notes
- Listed in SECURITY.md (with permission)

## Security Tools

We use the following tools to maintain security:

- **Bandit**: Python security linter
- **Safety**: Dependency vulnerability scanner
- **CodeQL**: Semantic code analysis
- **Dependabot**: Automated dependency updates
- **Ruff**: Fast Python linter with security rules

## Contact

For security concerns: ayushjaipuriyar21@gmail.com

For general issues: https://github.com/ayushjaipuriyar/animepahe-dl/issues

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

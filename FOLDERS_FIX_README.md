# Folders Fix Documentation Index

This documentation explains why the folders endpoint fix doesn't survive `azd up` and provides comprehensive solutions.

## Quick Start

**Need a fix NOW?** Go to: [`QUICK_FIX_GUIDE.md`](QUICK_FIX_GUIDE.md)

**Need to understand the problem?** Go to: [`FOLDERS_FIX_SUMMARY.md`](FOLDERS_FIX_SUMMARY.md)

**Ready to implement?** Go to: [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md)

## The Problem in One Sentence

**azd up deploys pre-built container images from Azure Container Registry, not your local source code.**

## Documentation Structure

### 1. Executive Summary
**File**: [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md)
**Audience**: Managers, architects, decision makers
**Reading Time**: 5 minutes
**Contents**: Problem statement, business impact, solution comparison, ROI, recommendation

### 2. Folders Fix Summary
**File**: [`FOLDERS_FIX_SUMMARY.md`](FOLDERS_FIX_SUMMARY.md)
**Audience**: Developers, DevOps engineers
**Reading Time**: 10 minutes
**Contents**: Root cause explained, deployment flow diagrams, three solution options, quick commands

### 3. Quick Fix Guide
**File**: [`QUICK_FIX_GUIDE.md`](QUICK_FIX_GUIDE.md)
**Audience**: Developers needing immediate solution
**Reading Time**: 5 minutes
**Contents**: Three fix options (manual, automated, GitHub Actions), troubleshooting, verification

### 4. Comprehensive Strategy
**File**: [`FOLDERS_FIX_STRATEGY.md`](FOLDERS_FIX_STRATEGY.md)
**Audience**: Technical leads, architects
**Reading Time**: 30 minutes
**Contents**: Complete analysis, all solution approaches, comparison, recommendations, workflows

### 5. Implementation Plan
**File**: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
**Audience**: Implementation team
**Reading Time**: 20 minutes
**Contents**: Step-by-step implementation, phase planning, comparison matrix, enhancements

### 6. Deployment Checklist
**File**: [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md)
**Audience**: Anyone deploying
**Reading Time**: 15 minutes (keep as reference)
**Contents**: Pre-deployment checks, three deployment methods, verification steps, troubleshooting

## Ready-to-Use Files

### Configuration
- **`azure.yaml.new`** - Updated azure.yaml with predeploy hook (ready to use)
- **`azure.yaml`** - Current configuration (backup before replacing)

### Scripts
- **`infra/scripts/build_images.sh`** - Build script for Linux/Mac (ready to use)
- **`infra/scripts/build_images.ps1`** - Build script for Windows (ready to use)

## Quick Decision Tree

```
Do you need to deploy right now?
├─ YES → Use QUICK_FIX_GUIDE.md → Manual build method
└─ NO → Continue below

Do you want a permanent automated solution?
├─ YES → Use DEPLOYMENT_CHECKLIST.md → Method A (Automated)
└─ NO → Continue below

Do you want to understand the problem first?
├─ YES → Read FOLDERS_FIX_SUMMARY.md
└─ NO → Continue below

Are you making the decision to implement?
├─ YES → Read EXECUTIVE_SUMMARY.md
└─ NO → Read FOLDERS_FIX_STRATEGY.md for all options
```

## Implementation Overview

### Recommended Solution: Add Predeploy Hook

**What it does**: Automatically builds container images before every `azd up` deployment

**Implementation steps**:
```bash
# 1. Backup current configuration
cp azure.yaml azure.yaml.backup

# 2. Use the new configuration with predeploy hook
cp azure.yaml.new azure.yaml

# 3. Ensure build scripts are executable
chmod +x infra/scripts/build_images.sh

# 4. Deploy (will automatically build images first)
azd up
```

**Result**: Every `azd up` will use your latest source code

### Alternative Solutions

See [`FOLDERS_FIX_STRATEGY.md`](FOLDERS_FIX_STRATEGY.md) for:
- Manual build before azd up
- Wait for GitHub Actions to build
- Use specific image tags instead of 'latest'
- Conditional builds (only changed services)

## Common Questions

### Q: Why does azd up not build from source?
**A**: azd is designed for infrastructure-as-code, not container builds. It expects images to already exist in a registry. See [`FOLDERS_FIX_SUMMARY.md`](FOLDERS_FIX_SUMMARY.md) for detailed explanation.

### Q: Will this slow down deployments?
**A**: Yes, by ~10-15 minutes (time to build 3 Docker images). However, this ensures you always deploy the correct code. See [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md) for ROI analysis.

### Q: Can I skip building if code hasn't changed?
**A**: Yes, possible with conditional builds. See [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) → Enhancement 4.

### Q: What if I only changed the API code?
**A**: The predeploy hook builds all three services. For development, use the manual build method from [`QUICK_FIX_GUIDE.md`](QUICK_FIX_GUIDE.md) to build only what changed.

### Q: Is this safe for production?
**A**: The predeploy hook is safe but not recommended for production. For production, use GitHub Actions to build images and specific tags (not 'latest'). See [`FOLDERS_FIX_STRATEGY.md`](FOLDERS_FIX_STRATEGY.md) → Production Best Practice.

### Q: Can I revert if something goes wrong?
**A**: Yes, simply restore the backup: `cp azure.yaml.backup azure.yaml`. See [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) → Rollback Plan.

## Verification Commands

After any deployment, verify with these commands:

```bash
# Check deployed image
az containerapp show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --query "properties.template.containers[0].image"

# Test folders endpoint
curl https://ca-stg6fsvw-api.blackplant-3f8c2e39.eastus.azurecontainerapps.io/folders/

# View logs
az containerapp logs show \
  --name ca-stg6fsvw-api \
  --resource-group msazaidocintstg \
  --follow
```

## File Structure

```
/workspaces/content-processing-solution-accelerator/
│
├── FOLDERS_FIX_README.md          ← You are here
├── EXECUTIVE_SUMMARY.md            ← For decision makers
├── FOLDERS_FIX_SUMMARY.md          ← Understand the problem
├── FOLDERS_FIX_STRATEGY.md         ← Complete analysis
├── QUICK_FIX_GUIDE.md              ← Need fix NOW
├── IMPLEMENTATION_PLAN.md          ← How to implement
├── DEPLOYMENT_CHECKLIST.md         ← Deployment steps
│
├── azure.yaml                      ← Current config (backup this!)
├── azure.yaml.new                  ← New config with predeploy hook
│
└── infra/
    └── scripts/
        ├── build_images.sh         ← Build script (Linux/Mac)
        └── build_images.ps1        ← Build script (Windows)
```

## Who Should Read What?

| Role | Start Here | Then Read | Finally |
|------|-----------|-----------|---------|
| Developer (need quick fix) | QUICK_FIX_GUIDE.md | FOLDERS_FIX_SUMMARY.md | DEPLOYMENT_CHECKLIST.md |
| Developer (implementing) | FOLDERS_FIX_SUMMARY.md | IMPLEMENTATION_PLAN.md | DEPLOYMENT_CHECKLIST.md |
| Tech Lead | EXECUTIVE_SUMMARY.md | FOLDERS_FIX_STRATEGY.md | IMPLEMENTATION_PLAN.md |
| DevOps Engineer | DEPLOYMENT_CHECKLIST.md | FOLDERS_FIX_STRATEGY.md | IMPLEMENTATION_PLAN.md |
| Manager/Architect | EXECUTIVE_SUMMARY.md | FOLDERS_FIX_SUMMARY.md | (Done) |

## Success Criteria

You've successfully fixed the problem when:

- ✅ You can run `azd up` and the folders endpoint works
- ✅ Code changes survive the deployment process
- ✅ No manual docker build commands are needed
- ✅ The deployed image timestamp matches your deployment time
- ✅ Logs show no errors when calling the folders endpoint

## Support

If you encounter issues:

1. Check the **Troubleshooting** section in [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md)
2. Review the **Common Pitfalls** in [`FOLDERS_FIX_STRATEGY.md`](FOLDERS_FIX_STRATEGY.md)
3. Verify your environment meets all prerequisites
4. Check Azure service health
5. Review Container App logs for specific errors

## Contributing

Found an issue or have a suggestion? Update this documentation:

1. Make your changes
2. Test thoroughly
3. Update the relevant documentation files
4. Commit with clear description
5. Share with the team

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2025-11-26 | 1.0 | Initial comprehensive documentation suite created |

## Key Takeaways

1. **azd up deploys images, not source code** - This is by design
2. **You must build new images when code changes** - Either manually or with automation
3. **The predeploy hook is the recommended solution** - Fully automated, always works
4. **GitHub Actions is the production solution** - For proper CI/CD workflow
5. **Always verify after deployment** - Check image, test endpoint, review logs

## Next Steps

1. Read [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md) to understand the business case
2. Read [`FOLDERS_FIX_SUMMARY.md`](FOLDERS_FIX_SUMMARY.md) to understand the technical issue
3. Follow [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) to implement the fix
4. Use [`QUICK_FIX_GUIDE.md`](QUICK_FIX_GUIDE.md) for quick reference
5. Refer to [`FOLDERS_FIX_STRATEGY.md`](FOLDERS_FIX_STRATEGY.md) for deep dives

## Questions?

All answers are in these documents. Use the decision tree above to find the right starting point for your needs.

---

**Documentation Generated**: 2025-11-26
**Documentation Version**: 1.0
**Target Audience**: Development Team, DevOps, Technical Leadership

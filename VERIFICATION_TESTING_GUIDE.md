# NPI Verification Testing Guide

This guide provides step-by-step instructions for testing the doctor credential verification feature for NYC TRS Retirement Allowance Verification Forms.

## Overview

The verification feature validates physician credentials (NPI numbers) against the CMS NPI Registry API. It's designed to be:
- **Schema-specific**: Only runs for configured forms
- **Backward compatible**: Disabled by default, doesn't break existing functionality
- **Graceful**: API failures don't stop document processing

## Prerequisites

- Azure resources deployed (Container Apps, Cosmos DB, Blob Storage)
- Access to Azure portal and CLI
- TRS Retirement Allowance Verification Form samples with physician NPI numbers

## Testing Phases

### Phase 1: Verify Backward Compatibility (Verification Disabled)

**Goal**: Ensure existing functionality works unchanged when verification is disabled.

1. **Deploy Code**:
   ```bash
   # Build and push Docker images
   cd infra/scripts
   ./build_images.sh  # or build_images.ps1 on Windows

   # Deploy to Azure
   azd deploy
   ```

2. **Verify Environment Variables**:
   ```bash
   # Check that verification is disabled by default
   az containerapp show -n <app-name> -g <resource-group> --query "properties.template.containers[0].env"
   ```

   Should show:
   - `APP_VERIFY_ENABLED=false` (or not set, defaults to false)
   - `APP_PROCESS_STEPS=extract,map,evaluate,save` (no "verify" step yet)

3. **Test Document Processing**:
   - Upload a TRS form through the web UI
   - Verify it processes successfully through all steps
   - Check output in Cosmos DB - should NOT have verification_metadata field
   - Verify comparison data has NO verification fields (VerificationStatus, etc.)

4. **Expected Results**:
   - ✅ Document processes normally
   - ✅ No verification fields in output
   - ✅ No errors or warnings about verification
   - ✅ Processing time unchanged

---

### Phase 2: Upload TRS Schema

**Goal**: Register the RetirementAllowanceVerificationForm schema in the system.

1. **Prepare Schema Upload**:
   ```bash
   # Navigate to schema samples
   cd src/ContentProcessorAPI/samples/schemas
   ```

2. **Upload Schema via API**:

   **Option A - Using Web UI** (if available):
   - Navigate to Schema Vault in the web interface
   - Click "Add Schema"
   - Upload: `retirement_allowance_verification.py`
   - Class Name: `RetirementAllowanceVerificationForm`
   - Description: `TRS Retirement Allowance Verification Form`

   **Option B - Using Upload Script**:
   ```bash
   # Use the schema upload script (Linux/Mac)
   ./upload_schemas.sh

   # Or PowerShell (Windows)
   .\upload_schemas.ps1
   ```

   **Option C - Using curl**:
   ```bash
   # Get API endpoint
   API_URL=$(az containerapp show -n <api-app-name> -g <resource-group> --query "properties.configuration.ingress.fqdn" -o tsv)

   # Upload schema
   curl -X POST "https://${API_URL}/api/schemavault" \
     -F "file=@retirement_allowance_verification.py" \
     -F "schema={\"Id\":\"trs-retirement-allowance-verification\",\"ClassName\":\"RetirementAllowanceVerificationForm\",\"Description\":\"TRS Retirement Allowance Verification Form\",\"FileName\":\"retirement_allowance_verification.py\",\"ContentType\":\"text/x-python\"}"
   ```

3. **Verify Schema Upload**:
   ```bash
   # List all schemas
   curl "https://${API_URL}/api/schemavault"
   ```

   Should see the TRS schema in the list.

4. **Test Schema Selection**:
   - Upload a TRS form
   - Select "TRS Retirement Allowance Verification Form" schema
   - Verify extraction works correctly with physician fields

---

### Phase 3: Enable Verification (Without Pipeline Integration)

**Goal**: Test verification configuration without modifying the pipeline.

1. **Update Environment Variables**:
   ```bash
   # Enable verification globally
   az containerapp update \
     -n <processor-app-name> \
     -g <resource-group> \
     --set-env-vars \
       APP_VERIFY_ENABLED=true \
       APP_VERIFY_CONFIDENCE_THRESHOLD=0.70 \
       APP_VERIFY_TIMEOUT=30 \
       APP_DOCTOR_NPI_API_ENDPOINT=https://npiregistry.cms.hhs.gov/api/

   # Note: Don't add "verify" to APP_PROCESS_STEPS yet
   ```

2. **Check Configuration**:
   ```bash
   # Verify environment variables
   az containerapp show -n <processor-app-name> -g <resource-group> \
     --query "properties.template.containers[0].env[?name=='APP_VERIFY_ENABLED']"
   ```

3. **Test**:
   - Process a TRS form
   - Verification is enabled but NOT in pipeline steps
   - Should process normally without verification running

---

### Phase 4: Full Verification Testing

**Goal**: Test complete verification flow with NPI lookups.

1. **Add Verify to Pipeline Steps**:
   ```bash
   az containerapp update \
     -n <processor-app-name> \
     -g <resource-group> \
     --set-env-vars \
       APP_PROCESS_STEPS=extract,map,evaluate,verify,save
   ```

2. **Prepare Test Data**:

   Get sample valid NPI numbers for testing:
   - **Valid Test NPI**: 1234567893 (example - use real one)
   - **Invalid NPI**: 0000000000
   - **Inactive NPI**: (find one from registry)

3. **Test Case 1: Valid NPI**:
   - Upload TRS form with valid physician NPI
   - Select TRS schema
   - Process document
   - **Expected Results**:
     - ✅ Document processes successfully
     - ✅ verification_metadata present in Cosmos DB
     - ✅ VerificationStatus = "verified"
     - ✅ VerificationDetails contains provider name, specialty
     - ✅ API response time logged

4. **Test Case 2: Invalid/Not Found NPI**:
   - Upload form with non-existent NPI
   - **Expected Results**:
     - ✅ Document processes (doesn't fail)
     - ✅ VerificationStatus = "not_found"
     - ✅ No VerificationDetails
     - ✅ Document still saved

5. **Test Case 3: Low Confidence Field**:
   - Upload form with poor quality NPI extraction (low confidence)
   - **Expected Results**:
     - ✅ VerificationStatus = "skipped"
     - ✅ Error message: "Confidence below threshold"
     - ✅ No API call made (check logs)

6. **Test Case 4: Multiple Physician Fields**:
   - Form with: physician_name, physician_npi, physician_license_number
   - **Expected Results**:
     - ✅ NPI verified against registry
     - ✅ License verification skipped (not configured)
     - ✅ Name extracted but not verified
     - ✅ Only physician fields verified, member fields ignored

7. **Test Case 5: API Timeout/Error**:
   - Temporarily set APP_VERIFY_TIMEOUT=1 (very short)
   - **Expected Results**:
     - ✅ Document still processes
     - ✅ VerificationStatus = "error"
     - ✅ Error message logged
     - ✅ Processing doesn't fail

---

### Phase 5: Monitoring and Validation

**Goal**: Verify system behavior in production use.

1. **Check Logs**:
   ```bash
   # View processor logs
   az containerapp logs show \
     -n <processor-app-name> \
     -g <resource-group> \
     --tail 100

   # Look for verification messages:
   # - "Verification is disabled in configuration"
   # - "No verification configured for schema"
   # - "Verification handler error: ..."
   # - API call success/failure
   ```

2. **Query Cosmos DB**:
   ```bash
   # Check verification metadata in processed documents
   az cosmosdb mongodb collection show \
     --account-name <cosmos-account> \
     --database-name <db-name> \
     --name <process-container>
   ```

3. **Verify Output Structure**:

   Check a processed document JSON:
   ```json
   {
     "process_id": "...",
     "extracted_comparison_data": {
       "items": [
         {
           "Field": "physician_npi",
           "Extracted": "1234567893",
           "Confidence": "95%",
           "IsAboveThreshold": true,
           "VerificationStatus": "verified",
           "VerificationDetails": {
             "npi": "1234567893",
             "name": "Dr. John Smith",
             "specialty": "Internal Medicine",
             "status": "Active"
           },
           "VerifiedAt": "2024-01-15T10:30:00Z",
           "VerificationResponseTime": 245.6
         }
       ]
     },
     "verification_metadata": {
       "total_fields_checked": 1,
       "verified_count": 1,
       "not_found_count": 0,
       "error_count": 0,
       "total_api_time": 245.6,
       "verifications_by_type": {
         "doctor": {"verified": 1, "not_found": 0, "error": 0}
       }
     }
   }
   ```

4. **Performance Testing**:
   - Process 10 documents with verification
   - Measure: processing time increase, API latency
   - Verify: caching works (second lookup of same NPI is faster)

---

## Troubleshooting

### Verification Not Running

**Symptoms**: No verification fields in output

**Check**:
1. Is `APP_VERIFY_ENABLED=true`?
2. Is "verify" in `APP_PROCESS_STEPS`?
3. Is schema configured for verification? (check logs)
4. Are field names matching patterns (physician*, doctor*, npi, license)?

### API Errors

**Symptoms**: VerificationStatus = "error"

**Check**:
1. Network connectivity to npiregistry.cms.hhs.gov
2. Timeout setting (increase if needed)
3. API endpoint correct in config
4. Check container app logs for detailed error

### Verification Always Skipped

**Symptoms**: All verifications show "skipped"

**Check**:
1. Confidence threshold too high? (default 0.70 = 70%)
2. Extracted confidence values from evaluate step
3. Adjust `APP_VERIFY_CONFIDENCE_THRESHOLD` if needed

---

## Rollback Plan

If issues occur, disable verification:

```bash
# Option 1: Disable verification entirely
az containerapp update \
  -n <processor-app-name> \
  -g <resource-group> \
  --set-env-vars APP_VERIFY_ENABLED=false

# Option 2: Remove verify from pipeline
az containerapp update \
  -n <processor-app-name> \
  -g <resource-group> \
  --set-env-vars APP_PROCESS_STEPS=extract,map,evaluate,save
```

System will immediately revert to pre-verification behavior.

---

## Success Criteria

✅ **Phase 1**: Existing documents process normally without verification
✅ **Phase 2**: TRS schema uploads and extracts fields correctly
✅ **Phase 3**: Configuration updates apply without errors
✅ **Phase 4**: Valid NPIs verify successfully, invalid NPIs handled gracefully
✅ **Phase 5**: Monitoring shows stable performance, no errors

---

## Next Steps After Testing

1. **Production Deployment**:
   - Merge `feature/npi-verification` to `main`
   - Deploy to production environment
   - Enable verification for TRS schema only

2. **User Training**:
   - Show verification status in UI
   - Explain verification badges
   - Document what "verified" means

3. **Future Enhancements**:
   - Add state license verification
   - Create admin UI for verification config
   - Add verification reporting/dashboards
   - Expand to other credential types (notary, identity)

# Architecture Review: Doctor Credential Verification Feature

**Review Date:** 2025-12-01
**Use Case:** Teachers' Retirement System (TRS) "Retirement Allowance Verification Form"
**Reviewer:** Senior Software Architect

---

## Executive Summary

Your planned architecture for adding doctor credential verification is **SOUND but can be optimized**. The approach aligns well with existing patterns, but I recommend a **HYBRID implementation strategy** that starts simple and evolves based on TRS requirements. Key recommendations:

1. **Start with hard-coded verification** in Evaluate handler (Option A)
2. **Plan migration path** to dedicated handler (Option B)
3. **Store verification config in Cosmos DB** schema collection
4. **Extend ExtractionComparisonItem** for verification data
5. **Address API timeout/cost concerns** with circuit breakers and caching

**Risk Level:** LOW to MEDIUM (manageable with proper implementation)
**Alignment with System:** HIGH (follows existing patterns)
**Implementation Complexity:** MEDIUM (starts simple, grows incrementally)

---

## Current System Architecture Analysis

### Existing Pipeline Pattern

The system follows a **queue-based, event-driven pipeline architecture**:

```
Pipeline Steps: ["extract", "map", "evaluate", "save"]

Flow:
1. Extract Handler → content-pipeline-extract-queue
   - Uses Azure AI Content Understanding Service
   - Outputs: ExtractedContent (ArtifactType)

2. Map Handler → content-pipeline-map-queue
   - Uses Azure OpenAI (GPT-4o)
   - Outputs: SchemaMappedData (ArtifactType)

3. Evaluate Handler → content-pipeline-evaluate-queue
   - Merges confidence scores
   - Creates comparison data (ExtractionComparisonItem)
   - Outputs: ScoreMergedData (ArtifactType)

4. Save Handler → (terminal)
   - Persists to Cosmos DB
   - Updates ContentProcess status
   - Outputs: SavedContent (ArtifactType)
```

### Key Design Patterns

1. **HandlerBase Pattern:** All handlers extend `queue_handler_base.HandlerBase`
2. **Async Queue Processing:** Each handler polls queue → processes → enqueues to next step
3. **Artifact Storage:** Intermediate results stored as typed artifacts in Blob Storage
4. **Status Tracking:** `PipelineStatus` tracks steps, results, and metadata
5. **Dead Letter Queue:** Automatic retry (5 attempts) then DLQ for failures
6. **Data Models:** Pydantic models for type safety and validation

### Configuration Management

Current configuration stored in:
- **Environment Variables:** Pipeline steps, connection strings, endpoints
- **Cosmos DB - Schema Collection:** Schema definitions (Id, ClassName, Description, FileName)
- **Blob Storage:** Actual schema files (Python classes like `pension_verification.py`)

---

## Architecture Review: Your Proposed Design

### Question 1: Does adding VerifyHandler between Evaluate and Save align with patterns?

**ANSWER: YES with caveats**

**Alignment Assessment:**
- ✅ **Pattern Match:** Adding a handler follows the existing extension pattern
- ✅ **Queue Integration:** Fits naturally into queue-based flow
- ✅ **Handler Structure:** Would properly extend HandlerBase
- ✅ **Artifact Pattern:** Can create VerifiedContent artifact type

**Concerns:**
- ⚠️ **Pipeline Complexity:** Adds another step to every document (even non-medical)
- ⚠️ **Processing Time:** External API calls will increase pipeline latency
- ⚠️ **Configuration Drift:** Pipeline steps are environment-configured (hardcoded list)

**Code Impact:**
```python
# Current: application_configuration.py
app_process_steps: Annotated[list[str], NoDecode]  # From env var

# Would become:
# Environment Variable: "extract,map,evaluate,verify,save"
# This affects ALL document types, not just medical forms
```

**Alternative to Consider:**
- Make verification **conditional within Evaluate handler** (see Option A below)
- Avoids adding global pipeline step for form-specific requirement

### Question 2: Is extending ExtractionComparisonItem the right place for verification data?

**ANSWER: YES - This is the correct approach**

**Why This Works:**
1. **Semantic Fit:** `ExtractionComparisonItem` represents field-level data about extraction quality
2. **UI Integration:** Already displayed in UI for human review
3. **Score Alignment:** Verification naturally extends confidence scoring
4. **Data Locality:** Keeps verification results with the fields they verify

**Recommended Extension:**
```python
# File: libs/pipeline/handlers/logics/evaluate_handler/comparison.py

class ExtractionComparisonItem(BaseModel):
    Field: Optional[str]
    Extracted: Optional[Any]
    Confidence: Optional[str]
    IsAboveThreshold: Optional[bool]

    # NEW: Verification fields
    VerificationStatus: Optional[str] = None  # "verified" | "not_found" | "invalid" | "error" | "skipped" | "not_applicable"
    VerificationSource: Optional[str] = None  # "npi_registry" | "state_medical_board" | "notary_db" | None
    VerificationDetails: Optional[dict] = None  # API response details
    VerificationTimestamp: Optional[str] = None  # ISO 8601 timestamp
    VerificationResponseTime: Optional[float] = None  # API latency in seconds
    VerificationError: Optional[str] = None  # Error message if status is "error"
```

**Why not a separate structure:**
- ❌ Requires parallel data structures (harder to maintain)
- ❌ Complicates UI rendering (two data sources)
- ❌ Breaks semantic relationship between extracted value and verification

**Data Model Propagation:**
The verification data flows through existing structures:
1. `ExtractionComparisonItem` (comparison.py) ✓
2. `ExtractionComparisonData` (comparison.py) - contains list of items ✓
3. `DataExtractionResult` (model.py) - has comparison_result field ✓
4. `ContentProcess` (content_process.py) - has extracted_comparison_data field ✓
5. Cosmos DB - persisted in process collection ✓

**No structural changes needed** - just extend the leaf model.

### Question 3: Where should schema verification config be stored?

**ANSWER: Cosmos DB Schema Collection (Option A with enhancement)**

**Evaluation Matrix:**

| Location | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Cosmos DB Schema** | ✅ Already exists<br>✅ Schema-specific<br>✅ Runtime queryable<br>✅ Version trackable | ⚠️ Requires schema model extension<br>⚠️ Query on every process | **RECOMMENDED** |
| **Blob Storage** | ✅ Easy to deploy<br>✅ Supports complex config | ❌ Not queryable<br>❌ Separate from schema definition<br>❌ Version management harder | Not recommended |
| **Environment Variables** | ✅ Simple deployment<br>✅ No code changes | ❌ Not schema-specific<br>❌ Requires redeploy to change<br>❌ Hard to manage complex rules | Not recommended |

**Recommended Implementation:**

**Step 1: Extend Schema Model**
```python
# File: libs/pipeline/entities/schema.py

class VerificationRule(BaseModel):
    """Defines a verification rule for a field or set of fields"""
    verification_type: str  # "doctor" | "notary" | "death_cert" | "identity"
    enabled: bool = True
    required_fields: list[str]  # Fields needed for verification
    field_mappings: dict[str, str]  # Map schema fields to verification API fields
    api_endpoint: Optional[str] = None  # Override default endpoint
    timeout_seconds: int = 30
    cache_ttl_hours: int = 24  # Cache verified credentials

class Schema(BaseModel):
    Id: str
    ClassName: str
    Description: str
    FileName: str
    ContentType: str
    Created_On: Optional[datetime.datetime] = Field(default=None)
    Updated_On: Optional[datetime.datetime] = Field(default=None)

    # NEW: Verification configuration
    verification_rules: Optional[list[VerificationRule]] = Field(default_factory=list)
```

**Step 2: Example Configuration for TRS Form**
```json
{
    "Id": "pension_verification_v1",
    "ClassName": "PensionVerification",
    "Description": "TRS Retirement Allowance Verification Form",
    "FileName": "pension_verification.py",
    "ContentType": "application/pdf",
    "verification_rules": [
        {
            "verification_type": "doctor",
            "enabled": true,
            "required_fields": ["physician_license_number", "physician_license_state"],
            "field_mappings": {
                "physician_license_number": "license_number",
                "physician_license_state": "state",
                "physician_name": "name"
            },
            "timeout_seconds": 30,
            "cache_ttl_hours": 168
        },
        {
            "verification_type": "notary",
            "enabled": true,
            "required_fields": ["notary_commission_expiration_date", "notary_state"],
            "field_mappings": {
                "notary_commission_expiration_date": "commission_expiration",
                "notary_state": "state"
            },
            "timeout_seconds": 15,
            "cache_ttl_hours": 24
        }
    ]
}
```

**Benefits:**
- Schema-driven configuration (one source of truth)
- Runtime configurable (no redeploy needed)
- Supports multiple verification types per form
- Field mapping flexibility
- Per-rule timeout and caching

### Question 4: Is queue-based approach appropriate for verification?

**ANSWER: NO - Not for initial implementation**

**Analysis:**

**Queue-Based Approach (Your Proposal):**
```
Evaluate → evaluate queue →
Verify → verify queue →
Save → (terminal)
```

Pros:
- ✅ Consistent with existing pattern
- ✅ Automatic retry and DLQ
- ✅ Horizontal scaling
- ✅ Failure isolation

Cons:
- ❌ Adds latency (queue polling + message serialization)
- ❌ More complex to debug (distributed across handlers)
- ❌ Requires new queue, handler, container deployment
- ❌ Overkill for synchronous verification API calls

**Synchronous Approach (Recommended):**
```
Evaluate Handler:
  1. Calculate confidence scores (existing)
  2. Create comparison data (existing)
  3. Check schema for verification_rules (NEW)
  4. If rules exist → call verification service (NEW)
  5. Update comparison items with verification results (NEW)
  6. Save result (existing)
```

Pros:
- ✅ Simpler implementation
- ✅ Lower latency
- ✅ Easier debugging (single handler)
- ✅ No new infrastructure
- ✅ Atomic operation (verification tied to evaluation)

Cons:
- ⚠️ Evaluation handler does more work
- ⚠️ No automatic retry (must implement manually)
- ⚠️ API timeouts block handler

**Hybrid Recommendation:**

**Start with synchronous (in Evaluate)** because:
1. TRS is your first use case (one customer, one form type)
2. Verification is logically part of data quality assessment
3. Simpler to implement and test
4. Easier to iterate based on feedback

**Migrate to separate handler later** when:
1. You have 5+ schemas with verification rules
2. Verification takes >10 seconds per document
3. You need different retry strategies per verification type
4. Verification becomes a product differentiator

**Migration path is straightforward:**
- Extract verification logic into `VerifyHandler`
- Add "verify" to `app_process_steps`
- Update `pipeline_step_helper.py` to route correctly
- Existing data models remain unchanged

### Question 5: Build full system now vs. start simpler?

**ANSWER: Hybrid Approach (Recommended)**

**Option A: Simple Start (Weeks 1-4)**

**Implementation:**
```python
# File: libs/pipeline/handlers/evaluate_handler.py

class EvaluateHandler(HandlerBase):
    async def execute(self, context: MessageContext) -> StepResult:
        # ... existing code for confidence scoring ...

        # NEW: Get schema with verification rules
        schema = Schema.get_schema(
            schema_id=context.data_pipeline.pipeline_status.schema_id,
            connection_string=self.application_context.configuration.app_cosmos_connstr,
            database_name=self.application_context.configuration.app_cosmos_database,
            collection_name=self.application_context.configuration.app_cosmos_container_schema,
        )

        # NEW: Run verifications if configured
        if schema.verification_rules:
            await self._run_verifications(
                comparison_data=result_data,
                extracted_result=gpt_evaluate_confidence_dict,
                verification_rules=schema.verification_rules
            )

        # ... rest of existing code ...

    async def _run_verifications(
        self,
        comparison_data: ExtractionComparisonData,
        extracted_result: dict,
        verification_rules: list[VerificationRule]
    ):
        """Run verification rules and update comparison items"""
        verification_service = VerificationService(self.application_context)

        for rule in verification_rules:
            if not rule.enabled:
                continue

            # Check if required fields are present
            if not all(field in extracted_result for field in rule.required_fields):
                continue

            # Extract field values
            field_values = {
                api_field: extracted_result.get(schema_field)
                for schema_field, api_field in rule.field_mappings.items()
            }

            # Call verification service
            try:
                verification_result = await verification_service.verify(
                    verification_type=rule.verification_type,
                    field_values=field_values,
                    timeout=rule.timeout_seconds
                )

                # Update comparison items with verification results
                self._apply_verification_results(
                    comparison_data=comparison_data,
                    verification_result=verification_result,
                    rule=rule
                )
            except Exception as e:
                # Log error and mark fields as verification_error
                self._mark_verification_error(comparison_data, rule, str(e))
```

**New Service Layer:**
```python
# File: libs/services/verification_service.py

class VerificationService:
    def __init__(self, app_context: AppContext):
        self.app_context = app_context
        self.cache = VerificationCache()  # Redis or memory cache

    async def verify(
        self,
        verification_type: str,
        field_values: dict,
        timeout: int = 30
    ) -> VerificationResult:
        """Route to appropriate verifier based on type"""

        # Check cache first
        cache_key = self._make_cache_key(verification_type, field_values)
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result

        # Route to verifier
        verifier = self._get_verifier(verification_type)
        result = await verifier.verify(field_values, timeout)

        # Cache successful verifications
        if result.status == "verified":
            await self.cache.set(cache_key, result, ttl_hours=168)

        return result

    def _get_verifier(self, verification_type: str):
        """Factory method for verifiers"""
        verifiers = {
            "doctor": DoctorCredentialVerifier(),
            "notary": NotaryVerifier(),
            # Future: "death_cert", "identity", etc.
        }
        return verifiers.get(verification_type)

class DoctorCredentialVerifier:
    async def verify(self, field_values: dict, timeout: int) -> VerificationResult:
        """Verify doctor credentials via NPI Registry and state boards"""
        license_number = field_values.get("license_number")
        state = field_values.get("state")

        if not license_number or not state:
            return VerificationResult(
                status="skipped",
                reason="Missing required fields"
            )

        # Call NPI Registry API
        npi_result = await self._check_npi_registry(license_number, state, timeout)

        # If NPI fails, try state medical board
        if npi_result.status != "verified":
            state_result = await self._check_state_board(license_number, state, timeout)
            return state_result

        return npi_result

    async def _check_npi_registry(self, license_number: str, state: str, timeout: int):
        """Call NPI Registry API with circuit breaker"""
        # Implementation with httpx + circuit breaker
        pass
```

**Pros:**
- ✅ Delivers TRS value quickly (4-week timeline)
- ✅ No new infrastructure (no new queues/handlers)
- ✅ Easy to test and debug
- ✅ Fits in existing evaluate step
- ✅ Schema-driven configuration (extensible)

**Cons:**
- ⚠️ Evaluate handler does more work (but still manageable)
- ⚠️ Less isolation (verification failure affects evaluation)

**Option B: Full Architecture (Months 2-3)**

When you outgrow Option A, migrate to dedicated handler:

```python
# File: libs/pipeline/handlers/verify_handler.py

class VerifyHandler(HandlerBase):
    def __init__(self, appContext: AppContext, step_name: str, **data):
        super().__init__(appContext, step_name, **data)

    async def execute(self, context: MessageContext) -> StepResult:
        # Get evaluated result
        output_file = self.download_output_file_to_json_string(
            processed_by="evaluate",
            artifact_type=ArtifactType.ScoreMergedData,
        )
        evaluated_result = DataExtractionResult(**json.loads(output_file))

        # Get schema
        schema = Schema.get_schema(...)

        # Run verifications
        verification_service = VerificationService(self.application_context)
        updated_comparison = await verification_service.verify_all(
            comparison_data=evaluated_result.comparison_result,
            extracted_result=evaluated_result.extracted_result,
            verification_rules=schema.verification_rules
        )

        # Update result
        evaluated_result.comparison_result = updated_comparison

        # Save updated result
        result_file = context.data_pipeline.add_file(
            file_name="verify_output.json",
            artifact_type=ArtifactType.VerifiedContent,  # NEW artifact type
        )
        result_file.upload_json_text(...)

        return StepResult(...)
```

**Migration Steps:**
1. Extract verification logic from Evaluate to VerifyHandler
2. Add `ArtifactType.VerifiedContent` enum
3. Update `app_process_steps` environment variable
4. Update Save handler to read from "verify" instead of "evaluate"
5. Deploy new container and queue

**Pros:**
- ✅ Separation of concerns
- ✅ Independent scaling
- ✅ Better retry logic
- ✅ Easier to add new verification types

**Cons:**
- ⚠️ More infrastructure
- ⚠️ Higher deployment complexity
- ⚠️ Longer pipeline latency

---

## Question 6: Architectural Concerns

### API Timeout Handling

**Concern: External APIs may timeout or fail**

**Recommended Mitigations:**

**1. Circuit Breaker Pattern**
```python
# File: libs/services/circuit_breaker.py

from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpen("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage in DoctorCredentialVerifier:
npi_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

async def _check_npi_registry(self, license_number: str, state: str, timeout: int):
    try:
        return await npi_circuit_breaker.call(
            self._npi_api_call,
            license_number,
            state,
            timeout
        )
    except CircuitBreakerOpen:
        return VerificationResult(status="error", reason="NPI Registry unavailable")
```

**2. Timeout Configuration**
```python
# Per-rule timeout in schema:
"verification_rules": [{
    "verification_type": "doctor",
    "timeout_seconds": 30,  # Fail fast
    ...
}]

# Implementation with httpx:
async def _npi_api_call(self, license_number, state, timeout):
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            f"https://npiregistry.cms.hhs.gov/api/",
            params={"number": license_number, "state": state}
        )
        return self._parse_npi_response(response)
```

**3. Fallback Strategy**
```python
async def verify(self, field_values: dict, timeout: int) -> VerificationResult:
    # Try primary source (NPI Registry)
    try:
        result = await self._check_npi_registry(...)
        if result.status == "verified":
            return result
    except Exception:
        pass  # Fall through to fallback

    # Fallback to state medical board
    try:
        result = await self._check_state_board(...)
        return result
    except Exception:
        pass

    # Last resort: mark as manual review needed
    return VerificationResult(
        status="error",
        reason="All verification sources unavailable",
        requires_manual_review=True
    )
```

### External API Dependencies

**Concern: NPI Registry and state boards may be unreliable**

**Recommended Mitigations:**

**1. Caching Strategy**
```python
class VerificationCache:
    """Cache verified credentials to reduce API calls"""

    def __init__(self):
        # Use Redis or in-memory cache
        self.cache = {}  # Replace with Redis client

    def _make_key(self, verification_type: str, license_number: str, state: str) -> str:
        return f"verify:{verification_type}:{state}:{license_number}"

    async def get(self, cache_key: str) -> Optional[VerificationResult]:
        # Check cache
        cached = self.cache.get(cache_key)
        if cached and not self._is_expired(cached):
            return cached["result"]
        return None

    async def set(self, cache_key: str, result: VerificationResult, ttl_hours: int):
        self.cache[cache_key] = {
            "result": result,
            "expires_at": time.time() + (ttl_hours * 3600)
        }

# Cache hits mean:
# - No API latency for repeat checks
# - No cost for duplicate verifications
# - Resilience to API outages (stale data better than none)
```

**2. Monitoring and Alerting**
```python
# Add metrics to verification service:

class VerificationService:
    def __init__(self, app_context: AppContext):
        self.metrics = VerificationMetrics()

    async def verify(self, ...):
        start_time = time.time()

        try:
            result = await verifier.verify(...)
            self.metrics.record_success(
                verification_type=verification_type,
                duration=time.time() - start_time,
                cache_hit=cached_result is not None
            )
            return result
        except Exception as e:
            self.metrics.record_failure(
                verification_type=verification_type,
                error=str(e),
                duration=time.time() - start_time
            )
            raise

# Monitor:
# - API success rate (alert if < 95%)
# - Average latency (alert if > 5 seconds)
# - Cache hit rate (optimize cache TTL)
# - Circuit breaker trips (indicates API issues)
```

**3. Graceful Degradation**
```python
# Don't fail the entire document if verification fails:

if verification_result.status == "error":
    # Mark field as needing manual review
    comparison_item.VerificationStatus = "error"
    comparison_item.VerificationError = verification_result.reason
    # But continue processing - don't throw exception

    # Optional: Lower confidence score to trigger human review
    comparison_item.Confidence = "0.00%"
    comparison_item.IsAboveThreshold = False
```

### Cost Considerations

**Concern: External API calls cost money and time**

**Cost Analysis:**

**NPI Registry:**
- API: FREE (CMS public API)
- Rate Limit: ~5 requests/second
- Latency: ~500ms average
- Reliability: High (99.5% uptime)

**State Medical Boards:**
- API: Varies by state (some free, some paid)
- Rate Limit: Varies
- Latency: ~1-3 seconds
- Reliability: Medium (varies by state)

**Cost Mitigation:**

**1. Intelligent Caching**
```python
# Cache TTL strategy:
"cache_ttl_hours": 168  # 7 days for doctor licenses (rarely change)
"cache_ttl_hours": 24   # 1 day for notary commissions
"cache_ttl_hours": 720  # 30 days for death certificates

# This means:
# - First verification: API call
# - Subsequent checks within TTL: cache hit (free)
# - For TRS: If same doctor signs 100 forms, only 1 API call
```

**2. Batch Processing**
```python
# Future optimization: Batch verify multiple documents
async def batch_verify(self, documents: list[dict]):
    """Verify multiple documents in parallel"""
    tasks = [
        self.verify(doc["verification_type"], doc["field_values"])
        for doc in documents
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Reduces total wall-clock time for large batches
```

**3. Conditional Verification**
```python
# Only verify if confidence is already high:

if comparison_item.Confidence < 0.8:
    # Don't waste API call on low-confidence extraction
    comparison_item.VerificationStatus = "skipped"
    comparison_item.VerificationDetails = {"reason": "Low extraction confidence"}
else:
    # High confidence extraction → worth verifying
    result = await verification_service.verify(...)
```

### Performance Impact

**Concern: Verification adds latency to pipeline**

**Current Pipeline Performance:**
```
Extract:  ~10-15 seconds (Content Understanding)
Map:      ~3-5 seconds (GPT-4o)
Evaluate: ~1-2 seconds (local calculation)
Save:     ~1 second (Cosmos DB write)
---
TOTAL:    ~15-23 seconds
```

**With Verification:**
```
Extract:  ~10-15 seconds
Map:      ~3-5 seconds
Evaluate: ~1-2 seconds
  + Verification: ~2-5 seconds (cached: ~10ms)
Save:     ~1 second
---
TOTAL:    ~17-28 seconds (uncached)
TOTAL:    ~15-23 seconds (cached)
```

**Impact: +2-5 seconds per document (first time)**

**Acceptable?**
- For TRS use case: **YES** (human review takes minutes, 5 seconds is negligible)
- For high-volume scenarios: Use caching and batch processing

---

## Recommended Architecture: Hybrid Approach

### Phase 1: Quick Win (Weeks 1-4)

**Goal:** Deliver doctor verification for TRS form

**Implementation:**
1. Extend `ExtractionComparisonItem` with verification fields
2. Extend `Schema` model with `verification_rules`
3. Add verification logic to `EvaluateHandler`
4. Create `VerificationService` with `DoctorCredentialVerifier`
5. Implement circuit breaker and caching
6. Update TRS schema in Cosmos DB with verification rules

**New Files:**
```
src/ContentProcessor/src/libs/
├── services/
│   ├── __init__.py
│   ├── verification_service.py       # Main service
│   ├── verifiers/
│   │   ├── __init__.py
│   │   ├── base.py                   # BaseVerifier abstract class
│   │   ├── doctor_verifier.py        # DoctorCredentialVerifier
│   │   └── notary_verifier.py        # Future: NotaryVerifier
│   ├── circuit_breaker.py
│   └── verification_cache.py
```

**Modified Files:**
```
src/ContentProcessor/src/libs/
├── pipeline/
│   ├── entities/
│   │   └── schema.py                 # Add VerificationRule model
│   ├── handlers/
│   │   ├── evaluate_handler.py       # Add _run_verifications()
│   │   └── logics/evaluate_handler/
│   │       └── comparison.py         # Extend ExtractionComparisonItem
```

**Configuration:**
```bash
# No environment variable changes needed
# Just update schema in Cosmos DB via API or direct insert
```

**Deployment:**
```bash
# No new infrastructure
azd up  # Redeploys with new code
```

### Phase 2: Scale and Separate (Months 2-3)

**Goal:** Handle multiple verification types across many schemas

**Triggers to migrate:**
- 5+ schemas using verification
- Verification latency > 10 seconds
- Need for complex retry logic
- Verification becomes product feature (marketed separately)

**Implementation:**
1. Create `VerifyHandler` extending `HandlerBase`
2. Extract verification logic from Evaluate to Verify
3. Add `ArtifactType.VerifiedContent`
4. Update `app_process_steps`: `"extract,map,evaluate,verify,save"`
5. Deploy new queue and container

**New Infrastructure:**
```
Queues:
- content-pipeline-verify-queue
- content-pipeline-verify-queue-dead-letter-queue

Container Apps:
- content-processor-verify (new)
```

**Migration Path:**
```python
# Week 1: Create VerifyHandler (feature flag disabled)
# Week 2: Test in dev environment
# Week 3: Enable feature flag for test schemas
# Week 4: Migrate all schemas, remove old code from Evaluate
```

---

## Architecture Decision Records (ADRs)

### ADR-001: Extend ExtractionComparisonItem for Verification Data

**Status:** APPROVED

**Context:**
Need to store verification results alongside extracted field data.

**Decision:**
Extend `ExtractionComparisonItem` with optional verification fields rather than creating separate data structure.

**Consequences:**
- UI can display verification status inline with extracted data
- Verification results flow through existing data pipeline
- No breaking changes to existing code
- Easy to query and filter on verification status

**Alternatives Considered:**
- Separate `VerificationResult` model → Rejected (parallel data structures)
- Store in metadata → Rejected (harder to access in UI)

---

### ADR-002: Store Verification Config in Cosmos DB Schema Collection

**Status:** APPROVED

**Context:**
Verification rules are schema-specific and should be configurable without code changes.

**Decision:**
Extend `Schema` model in Cosmos DB with `verification_rules` list.

**Consequences:**
- Schema is single source of truth
- Runtime configurable (no redeploy)
- Supports multiple verification types per form
- Versioning via Schema versioning

**Alternatives Considered:**
- Blob storage config files → Rejected (not queryable)
- Environment variables → Rejected (not schema-specific)

---

### ADR-003: Start with Synchronous Verification in Evaluate Handler

**Status:** APPROVED

**Context:**
Need to balance speed of delivery with architectural purity for initial TRS implementation.

**Decision:**
Implement verification synchronously within `EvaluateHandler` for Phase 1. Migrate to dedicated `VerifyHandler` in Phase 2 based on usage patterns.

**Consequences:**
- Faster time to value (4 weeks vs 8 weeks)
- Simpler debugging and testing
- No new infrastructure for Phase 1
- Clear migration path to queue-based handler

**Alternatives Considered:**
- Build full queue-based handler first → Rejected (over-engineering)
- Never migrate to separate handler → Rejected (technical debt)

---

### ADR-004: Use Circuit Breaker Pattern for External API Calls

**Status:** APPROVED

**Context:**
External verification APIs may fail or timeout, impacting pipeline reliability.

**Decision:**
Implement circuit breaker pattern with fallback strategies and caching.

**Consequences:**
- Graceful degradation during API outages
- Reduced cascading failures
- Better user experience (marked for manual review vs hard failure)
- Monitoring visibility into API health

**Alternatives Considered:**
- Simple timeout → Rejected (doesn't prevent cascading failures)
- Synchronous retry → Rejected (increases latency)

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| **API timeout exceeds pipeline tolerance** | MEDIUM | HIGH | Circuit breaker, 30s timeout, fallback to manual review | Backend |
| **NPI Registry rate limiting** | LOW | MEDIUM | Caching (TTL=7 days), batch processing | Backend |
| **State medical board APIs vary by state** | HIGH | MEDIUM | Fallback to NPI only, document state coverage | Product |
| **Verification adds too much latency** | LOW | LOW | Caching, conditional verification, async processing | Backend |
| **Schema config model becomes too complex** | MEDIUM | LOW | Start simple, add fields incrementally | Backend |
| **Migration to VerifyHandler breaks existing flows** | LOW | HIGH | Feature flags, gradual rollout, comprehensive testing | DevOps |
| **Cost of external API calls** | LOW | LOW | Free NPI API, caching reduces calls by 90%+ | Product |

**Overall Risk:** LOW to MEDIUM (manageable)

---

## Implementation Checklist

### Phase 1: Core Verification (Weeks 1-4)

**Week 1: Data Models**
- [ ] Extend `ExtractionComparisonItem` with verification fields
- [ ] Create `VerificationRule` model
- [ ] Extend `Schema` model with `verification_rules`
- [ ] Add unit tests for new models

**Week 2: Verification Service**
- [ ] Create `VerificationService` base class
- [ ] Implement `DoctorCredentialVerifier`
- [ ] Create `CircuitBreaker` utility
- [ ] Create `VerificationCache` utility
- [ ] Add integration tests with mock APIs

**Week 3: Handler Integration**
- [ ] Update `EvaluateHandler._run_verifications()`
- [ ] Update `EvaluateHandler.execute()` to check schema rules
- [ ] Add error handling and logging
- [ ] Update TRS schema in Cosmos DB
- [ ] End-to-end testing

**Week 4: Deployment & Validation**
- [ ] Deploy to dev environment
- [ ] Test with real TRS forms
- [ ] Monitor API latency and success rate
- [ ] Deploy to production
- [ ] User acceptance testing

### Phase 2: Separate Handler (Months 2-3)

**Month 2: Build & Test**
- [ ] Create `VerifyHandler` class
- [ ] Add `ArtifactType.VerifiedContent` enum
- [ ] Update `pipeline_step_helper.py`
- [ ] Create verify queue infrastructure (Bicep)
- [ ] Add feature flag for verify handler
- [ ] Integration testing in dev

**Month 3: Migration & Rollout**
- [ ] Deploy verify handler to staging
- [ ] Enable feature flag for test schemas
- [ ] Monitor performance and reliability
- [ ] Migrate all schemas to verify handler
- [ ] Remove verification code from Evaluate handler
- [ ] Update documentation

---

## Performance & Scale Projections

### Current TRS Volume Assumptions
- Forms per day: 100-500
- Forms per month: 3,000-15,000
- Peak hours: 9 AM - 5 PM EST

### Verification Performance

**Cold Start (No Cache):**
```
Document: 1 form with doctor certification
Verification time: 2-5 seconds
API calls: 1 (NPI Registry)
Cost: $0 (free API)
```

**Warm Cache (Repeat Doctor):**
```
Document: 1 form with known doctor
Verification time: 10-50ms
API calls: 0 (cache hit)
Cost: $0
```

**Cache Hit Rate Projection:**
```
Assumption: 50 unique doctors per month, 3,000 forms per month
Average forms per doctor: 60

Cache hit rate: 98.3%
(Only first form per doctor triggers API call)

API calls per month: ~50 (vs 3,000 without cache)
API call reduction: 98.3%
```

### Scaling Considerations

**Phase 1 (Synchronous in Evaluate):**
- **Max throughput:** ~100 docs/hour per handler instance
- **Bottleneck:** External API latency
- **Scaling strategy:** Horizontal (multiple Evaluate handler instances)

**Phase 2 (Dedicated Verify Handler):**
- **Max throughput:** ~500 docs/hour per handler instance
- **Bottleneck:** Queue processing rate
- **Scaling strategy:** Independent scaling of Verify handler

**When to scale:**
- Queue depth > 100 messages for > 5 minutes
- Handler processing time > 30 seconds average
- API timeout rate > 5%

---

## Future Enhancements

### Short Term (Months 4-6)
1. **Additional Verifiers:**
   - Notary commission verification
   - Death certificate verification (SSA Death Master File)
   - Identity verification (Experian, etc.)

2. **Advanced Caching:**
   - Redis cluster for distributed cache
   - Cache warming for common doctors
   - Cache invalidation webhooks

3. **Batch Processing:**
   - Verify multiple documents in parallel
   - Smart request batching to APIs

### Medium Term (Months 6-12)
1. **Machine Learning:**
   - Predict likelihood of verification failure
   - Skip verification for high-confidence matches
   - Anomaly detection (fraudulent credentials)

2. **Enhanced Monitoring:**
   - Real-time dashboard for verification metrics
   - Alerting for API degradation
   - Cost tracking per verification type

3. **User Features:**
   - Manual override of verification results
   - Whitelist known good credentials
   - Audit trail for verification changes

### Long Term (Year 2+)
1. **Verification Marketplace:**
   - Plugin architecture for third-party verifiers
   - API for external verification services
   - White-label verification as a service

2. **Blockchain Integration:**
   - Immutable verification records
   - Decentralized credential verification
   - Cross-organization verification sharing

---

## Conclusion

### Summary of Recommendations

1. **Architecture Approach:** Hybrid (start simple, evolve to separate handler)
2. **Data Model:** Extend `ExtractionComparisonItem` ✓
3. **Configuration Storage:** Cosmos DB Schema collection ✓
4. **Processing Pattern:** Synchronous in Evaluate (Phase 1) → Queue-based handler (Phase 2)
5. **Risk Mitigation:** Circuit breaker, caching, graceful degradation

### Why This Approach Works

**For TRS (Immediate):**
- Delivers value in 4 weeks
- No new infrastructure
- Easy to test and iterate
- Low risk

**For Scale (Future):**
- Clear migration path to dedicated handler
- Extensible to multiple verification types
- Cost-effective (caching reduces API calls by 98%+)
- Maintainable architecture

### Key Success Factors

1. **Start with real use case** (TRS) not abstract framework
2. **Measure before optimizing** (monitor API latency, cache hit rate)
3. **Build migration path early** (don't paint yourself into corner)
4. **Graceful degradation** (verification failure ≠ document failure)
5. **User-centric design** (verification results visible in UI)

### Next Steps

1. **Review this architecture** with team
2. **Prototype DoctorCredentialVerifier** (2-3 days)
3. **Test with real NPI API** (1 day)
4. **Implement Phase 1** (4 weeks)
5. **Gather feedback from TRS** (2 weeks)
6. **Decide on Phase 2 timing** based on usage

---

## Appendix: Code Samples

### Sample Schema Configuration

```json
{
    "_id": "pension_verification_v1",
    "Id": "pension_verification_v1",
    "ClassName": "PensionVerification",
    "Description": "TRS Retirement Allowance Verification Form",
    "FileName": "pension_verification.py",
    "ContentType": "application/pdf",
    "Created_On": "2025-12-01T00:00:00Z",
    "Updated_On": "2025-12-01T00:00:00Z",
    "verification_rules": [
        {
            "verification_type": "doctor",
            "enabled": true,
            "required_fields": [
                "physician_license_number",
                "physician_license_state"
            ],
            "field_mappings": {
                "physician_license_number": "license_number",
                "physician_license_state": "state",
                "physician_name": "name"
            },
            "timeout_seconds": 30,
            "cache_ttl_hours": 168
        }
    ]
}
```

### Sample API Response

```json
{
    "Field": "physician_license_number",
    "Extracted": "123456",
    "Confidence": "95.50%",
    "IsAboveThreshold": true,
    "VerificationStatus": "verified",
    "VerificationSource": "npi_registry",
    "VerificationDetails": {
        "npi_number": "1234567890",
        "name": "Dr. Karen Lee",
        "license_number": "123456",
        "license_state": "NY",
        "license_status": "active",
        "license_expiration": "2026-12-31",
        "taxonomy": "207Q00000X",
        "specialty": "Family Medicine",
        "verified_at": "2025-12-01T12:34:56Z"
    },
    "VerificationTimestamp": "2025-12-01T12:34:56Z",
    "VerificationResponseTime": 1.23,
    "VerificationError": null
}
```

---

**Document Version:** 1.0
**Last Updated:** 2025-12-01
**Next Review:** After Phase 1 completion

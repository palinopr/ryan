# Test Suite

## Active Tests

### Security Tests
- `test_campaign_security.py` - Tests campaign-level access control
- `test_security_restrictions.py` - Tests query restriction filters  
- `test_studio_security.py` - Tests LangGraph Studio security context

### Integration Tests
- `test_studio_api.py` - Tests LangGraph Studio API endpoints
- `test_studio_flow.py` - Tests complete workflow through Studio
- `test_studio_direct.py` - Direct Studio integration tests

### SDK Tests
- `test_direct_sdk.py` - Direct Meta SDK integration tests
- `test_direct_meta.py` - Meta API connection tests
- `test_meta_basic.py` - Basic Meta functionality tests
- `test_intelligent_query.py` - Tests AI query understanding

### Formatting Tests
- `test_city_formatting.py` - Tests client-friendly output formatting

### Other Tests
- `test_api.py` - General API tests
- `test_meta_connection.py` - Meta connection validation

## Archived Tests
Older tests have been moved to the `archive/` folder for reference.

## Running Tests

```bash
# Run a specific test
python tests/test_campaign_security.py

# Run all security tests
python -m pytest tests/test_*security*.py

# Run with virtual environment
source venv/bin/activate
python tests/test_studio_api.py
```
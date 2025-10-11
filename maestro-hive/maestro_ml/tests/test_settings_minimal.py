"""
Minimal test to diagnose pytest import issue
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_basic_import():
    """Test that we can import settings"""
    from maestro_ml.config.settings import get_settings
    settings = get_settings()
    assert settings is not None
    assert settings.ENVIRONMENT in ["development", "staging", "production"]
    print(f"✅ Settings loaded: Environment={settings.ENVIRONMENT}")

def test_settings_values():
    """Test settings have expected values"""
    from maestro_ml.config.settings import get_settings
    settings = get_settings()
    assert len(settings.JWT_SECRET_KEY) > 20
    assert settings.ENABLE_MULTI_TENANCY is True
    print(f"✅ JWT Secret length: {len(settings.JWT_SECRET_KEY)}")
    print(f"✅ Multi-tenancy: {settings.ENABLE_MULTI_TENANCY}")

if __name__ == "__main__":
    print("Running tests directly...")
    test_basic_import()
    test_settings_values()
    print("\n✅ All tests passed!")

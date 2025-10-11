#!/usr/bin/env python3
"""
Manual Test Suite - Database Integration
Tests database connectivity, migrations, and multi-tenancy
"""
import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_database_connection():
    """Test 1: Database connection"""
    print("\n🧪 Test 1: Database Connection")
    try:
        from maestro_ml.config.settings import get_settings
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            assert row[0] == 1
        
        await engine.dispose()
        
        print(f"  ✅ Database connection successful")
        print(f"     URL: {settings.DATABASE_URL[:50]}...")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

async def test_tenants_table():
    """Test 2: Tenants table exists"""
    print("\n🧪 Test 2: Tenants Table")
    try:
        from maestro_ml.config.settings import get_settings
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM tenants"))
            count = result.scalar()
            
            result = await conn.execute(text("SELECT id, name, slug FROM tenants LIMIT 1"))
            tenant = result.fetchone()
        
        await engine.dispose()
        
        print(f"  ✅ Tenants table exists")
        print(f"     Total tenants: {count}")
        if tenant:
            print(f"     Default tenant: {tenant[1]} ({tenant[2]})")
            print(f"     Tenant ID: {tenant[0]}")
        return True
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

async def test_tenant_id_columns():
    """Test 3: tenant_id columns in tables"""
    print("\n🧪 Test 3: Tenant ID Columns")
    try:
        from maestro_ml.config.settings import get_settings
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        
        tables_to_check = [
            'projects', 'artifacts', 'predictions', 
            'team_members', 'process_metrics', 'artifact_usage'
        ]
        
        async with engine.connect() as conn:
            results = {}
            for table in tables_to_check:
                try:
                    # Check if table exists and has tenant_id column
                    query = text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = '{table}' 
                        AND column_name = 'tenant_id'
                    """)
                    result = await conn.execute(query)
                    has_column = result.fetchone() is not None
                    results[table] = has_column
                except:
                    results[table] = False
        
        await engine.dispose()
        
        success_count = sum(results.values())
        print(f"  ✅ Checked {len(tables_to_check)} tables")
        for table, has_column in results.items():
            status = "✅" if has_column else "❌"
            print(f"     {status} {table}: {'has tenant_id' if has_column else 'missing tenant_id'}")
        
        return success_count == len(tables_to_check)
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

async def test_tenant_indexes():
    """Test 4: Tenant-related indexes"""
    print("\n🧪 Test 4: Tenant Indexes")
    try:
        from maestro_ml.config.settings import get_settings
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        settings = get_settings()
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        
        async with engine.connect() as conn:
            query = text("""
                SELECT COUNT(*) 
                FROM pg_indexes 
                WHERE indexname LIKE '%tenant%'
            """)
            result = await conn.execute(query)
            index_count = result.scalar()
        
        await engine.dispose()
        
        print(f"  ✅ Tenant indexes found")
        print(f"     Total indexes: {index_count}")
        return index_count >= 10  # Should have at least 10 tenant-related indexes
    except Exception as e:
        print(f"  ❌ Failed: {e}")
        return False

def main():
    """Run all async tests"""
    print("=" * 80)
    print("  MAESTRO ML - DATABASE INTEGRATION TEST SUITE")
    print("=" * 80)
    
    async def run_tests():
        tests = [
            test_database_connection,
            test_tenants_table,
            test_tenant_id_columns,
            test_tenant_indexes,
        ]
        
        results = []
        for test in tests:
            results.append(await test())
        
        return results
    
    results = asyncio.run(run_tests())
    
    # Summary
    print("\n" + "=" * 80)
    print("  TEST SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"\n  Passed: {passed}/{total}")
    print(f"  Failed: {total - passed}/{total}")
    print(f"  Success Rate: {(passed/total)*100:.1f}%\n")
    
    if passed == total:
        print("  ✅ ALL TESTS PASSED!")
        return 0
    else:
        print("  ❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())

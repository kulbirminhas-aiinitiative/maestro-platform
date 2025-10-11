#!/usr/bin/env python3
"""
Production Validation - Service Health Checks
Validates all services are running and healthy
"""
import subprocess
import sys
import json
from datetime import datetime

def check_service_status(service_name, command):
    """Check if a service is running"""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            shell=True,
            timeout=5
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)

def main():
    """Run all service health checks"""
    print("="*80)
    print("  SERVICE HEALTH CHECKS")
    print("="*80)
    print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    services = [
        ("PostgreSQL", "docker ps --filter 'name=maestro-postgres' --format '{{.Status}}'"),
        ("Redis", "docker ps --filter 'name=maestro-redis' --format '{{.Status}}'"),
        ("PostgreSQL Health", "docker exec maestro-postgres pg_isready -U maestro"),
        ("Redis Health", "docker exec maestro-redis redis-cli ping"),
    ]
    
    results = {}
    
    for service_name, command in services:
        print(f"🔍 Checking {service_name}...")
        is_healthy, output = check_service_status(service_name, command)
        
        results[service_name] = {
            "healthy": is_healthy,
            "output": output[:100] if output else "No output"
        }
        
        if is_healthy:
            print(f"  ✅ {service_name}: HEALTHY")
            if output:
                print(f"     Status: {output[:80]}")
        else:
            print(f"  ❌ {service_name}: UNHEALTHY")
            print(f"     Error: {output[:100]}")
        print()
    
    # Database connectivity test
    print("🔍 Testing Database Connectivity...")
    try:
        result = subprocess.run(
            ["docker", "exec", "maestro-postgres", "psql", "-U", "maestro", 
             "-d", "maestro_ml", "-c", "SELECT COUNT(*) FROM tenants;"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("  ✅ Database Query: SUCCESS")
            print(f"     Output: {result.stdout.strip()}")
            results["Database Query"] = {"healthy": True, "output": "Success"}
        else:
            print("  ❌ Database Query: FAILED")
            results["Database Query"] = {"healthy": False, "output": result.stderr}
    except Exception as e:
        print(f"  ❌ Database Query: ERROR - {e}")
        results["Database Query"] = {"healthy": False, "output": str(e)}
    
    print()
    
    # Summary
    print("="*80)
    print("  SUMMARY")
    print("="*80)
    
    healthy_count = sum(1 for r in results.values() if r["healthy"])
    total_count = len(results)
    
    print(f"\n  Healthy Services: {healthy_count}/{total_count}")
    print(f"  Health Score: {(healthy_count/total_count)*100:.1f}%\n")
    
    if healthy_count == total_count:
        print("  ✅ ALL SERVICES HEALTHY!")
        return 0
    else:
        print(f"  ⚠️  {total_count - healthy_count} service(s) unhealthy")
        return 1

if __name__ == "__main__":
    sys.exit(main())

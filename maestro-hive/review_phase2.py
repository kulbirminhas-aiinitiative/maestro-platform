#!/usr/bin/env python3
"""
Phase 2 (Society) Readiness Reviewer
Checks for the existence and basic functionality of MD-3100, MD-3104, MD-3107.
"""
import os
import sys
import importlib.util
import inspect

def check_module(module_name, class_name, methods):
    print(f"Checking {module_name} -> {class_name}...")
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"❌ Module {module_name} NOT FOUND")
            return False
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        if not hasattr(module, class_name):
            print(f"❌ Class {class_name} NOT FOUND in {module_name}")
            return False
        
        cls = getattr(module, class_name)
        print(f"✅ Class {class_name} FOUND")
        
        missing_methods = []
        for method in methods:
            if not hasattr(cls, method):
                missing_methods.append(method)
        
        if missing_methods:
            print(f"⚠️ Missing Methods in {class_name}: {missing_methods}")
            return False
        else:
            print(f"✅ All expected methods found: {methods}")
            return True

    except Exception as e:
        print(f"❌ Error checking {module_name}: {e}")
        return False

def main():
    print("=== Phase 2 (Society) Implementation Review ===\n")
    
    # MD-3100: Event Bus
    print("--- MD-3100: Event Bus ---")
    bus_ok = check_module("maestro_hive.agora.event_bus", "EventBus", ["publish", "subscribe"])
    
    # MD-3104: Identity
    print("\n--- MD-3104: Identity ---")
    id_ok = check_module("maestro_hive.agora.identity.agent_identity", "AgentIdentity", ["sign", "verify"])
    
    # MD-3107: Registry
    print("\n--- MD-3107: Registry ---")
    reg_ok = check_module("maestro_hive.agora.registry", "AgentRegistry", ["register", "find_agents"])
    
    print("\n=== Summary ===")
    print(f"Event Bus (MD-3100): {'READY' if bus_ok else 'PENDING'}")
    print(f"Identity (MD-3104):  {'READY' if id_ok else 'PENDING'}")
    print(f"Registry (MD-3107):  {'READY' if reg_ok else 'PENDING'}")

if __name__ == "__main__":
    main()

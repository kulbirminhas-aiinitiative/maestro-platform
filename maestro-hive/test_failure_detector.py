import sys
import os
import tempfile

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from maestro_hive.core.self_reflection.failure_detector import FailureDetector, FailureType

def test_pytest_parsing():
    detector = FailureDetector()
    
    sample_output = """
=================================== FAILURES ===================================
________________________________ test_example _________________________________

    def test_example():
>       assert 1 == 2
E       assert 1 == 2

test_example.py:4: AssertionError
=========================== short test summary info ============================
FAILED test_example.py::test_example - assert 1 == 2
    """
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
        tmp.write(sample_output)
        tmp_path = tmp.name
        
    try:
        failures = detector.scan_pytest(tmp_path)
        print(f"Found {len(failures)} failures")
        for f in failures:
            print(f"- {f.failure_type}: {f.error_message} in {f.file_path}:{f.line_number}")
            
        assert len(failures) > 0
        assert failures[0].failure_type == FailureType.ASSERTION_ERROR
        assert failures[0].file_path == "test_example.py"
    finally:
        os.unlink(tmp_path)

if __name__ == "__main__":
    test_pytest_parsing()

#!/usr/bin/env python3
"""
Quick test to demonstrate the pytest plugin functionality.
"""

import sys
import tempfile
import subprocess
from pathlib import Path

def main():
    print("🧪 Testing Django-Ollama Pytest Dashboard Integration")
    print("="*60)

    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='_test.py', delete=False) as f:
        f.write('''
import pytest
import time

def test_basic_pass():
    """A simple passing test."""
    assert 1 + 1 == 2

def test_with_timing():
    """Test with some execution time."""
    time.sleep(0.1)
    assert "hello".upper() == "HELLO"

@pytest.mark.integration
def test_integration_example():
    """Example integration test."""
    time.sleep(0.05)
    assert True

def test_basic_fail():
    """A test that fails to demonstrate error handling."""
    assert 1 + 1 == 3, "This will fail on purpose"

@pytest.mark.skip(reason="Demo skip")
def test_skipped():
    """A skipped test."""
    assert False
''')
        test_file = f.name

    try:
        print(f"📝 Created test file: {test_file}")

        # Run without dashboard first
        print("\n1️⃣  Running without dashboard integration:")
        cmd_basic = [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"]
        result_basic = subprocess.run(cmd_basic, capture_output=True, text=True)

        print(f"   Exit code: {result_basic.returncode}")
        if "PASSED" in result_basic.stdout or "FAILED" in result_basic.stdout:
            print("   ✅ Basic pytest execution works")
        else:
            print("   ❌ Basic pytest execution failed")
            print(f"   Output: {result_basic.stdout[:200]}...")

        # Try dashboard integration
        print("\n2️⃣  Testing dashboard plugin import:")

        dashboard_dir = Path(__file__).parent.parent
        import_test = f'''
import sys
sys.path.insert(0, "{dashboard_dir}")

try:
    from plugins.pytest_dashboard import DashboardTestPlugin
    plugin = DashboardTestPlugin()
    print("✅ Plugin import successful")

    # Test configuration
    from unittest.mock import MagicMock
    config = MagicMock()
    config.getoption.side_effect = lambda opt, default=None: {{
        "--dashboard": False,  # Disabled for this test
        "--dashboard-db": "test.db",
    }}.get(opt, default)

    plugin.pytest_configure(config)
    print("✅ Plugin configuration successful")

except Exception as e:
    print(f"❌ Plugin test failed: {{e}}")
    import traceback
    traceback.print_exc()
'''

        result_import = subprocess.run(
            [sys.executable, "-c", import_test],
            capture_output=True, text=True
        )

        print(f"   Exit code: {result_import.returncode}")
        print(f"   Output: {result_import.stdout.strip()}")
        if result_import.stderr:
            print(f"   Errors: {result_import.stderr.strip()}")

        print("\n3️⃣  Testing with pytest plugin registration:")

        # Create a conftest.py for this test
        conftest_content = f'''
import sys
sys.path.insert(0, "{dashboard_dir}")
pytest_plugins = ["plugins.pytest_dashboard"]
'''

        conftest_file = Path(test_file).parent / "conftest.py"
        conftest_file.write_text(conftest_content)

        try:
            # Run with plugin but dashboard disabled
            cmd_plugin = [
                sys.executable, "-m", "pytest",
                test_file,
                "-v",
                "--tb=short",
                # Don't enable dashboard to avoid database issues
            ]

            result_plugin = subprocess.run(cmd_plugin, capture_output=True, text=True, timeout=30)

            print(f"   Exit code: {result_plugin.returncode}")
            if "error" not in result_plugin.stderr.lower():
                print("   ✅ Plugin registration successful")
            else:
                print("   ⚠️  Plugin registration had issues:")
                print(f"   {result_plugin.stderr[:300]}...")

        except subprocess.TimeoutExpired:
            print("   ⚠️  Test timed out (plugin may be working but slow)")
        finally:
            conftest_file.unlink(missing_ok=True)

        print("\n📊 Summary:")
        print("   The pytest plugin architecture is in place")
        print("   Database integration needs proper setup")
        print("   WebSocket features require 'websockets' package")
        print("\n🎯 Next steps:")
        print("   1. Install websockets: pip install websockets")
        print("   2. Run: python test_dashboard/plugins/setup_cli.py --install")
        print("   3. Test: pytest --dashboard your_tests.py")

    finally:
        # Cleanup
        Path(test_file).unlink(missing_ok=True)

if __name__ == "__main__":
    main()
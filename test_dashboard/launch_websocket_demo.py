#!/usr/bin/env python3
"""
WebSocket Dashboard Launch Script

A simple script to launch the dashboard server and demonstrate WebSocket functionality.
"""

import asyncio
import subprocess
import sys
import time
import requests
import webbrowser
from pathlib import Path


class DashboardLauncher:
    """Launch and manage the dashboard server with WebSocket demo."""

    def __init__(self):
        self.server_process = None
        self.dashboard_dir = Path(__file__).parent
        self.server_url = "http://localhost:8080"

    def start_server(self):
        """Start the dashboard server."""
        print("🚀 Starting Django-Ollama Test Dashboard Server...")

        try:
            # Change to dashboard directory
            server_script = self.dashboard_dir / "server.py"

            if not server_script.exists():
                print(f"❌ Server script not found: {server_script}")
                return False

            # Start server process
            self.server_process = subprocess.Popen([
                sys.executable, str(server_script),
                "--host", "0.0.0.0",
                "--port", "8080",
                "--log-level", "info"
            ], cwd=str(self.dashboard_dir))

            print("⏳ Waiting for server to start...")

            # Wait for server to be ready
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    response = requests.get(f"{self.server_url}/api/health", timeout=2.0)
                    if response.status_code == 200:
                        print("✅ Dashboard server is ready!")
                        return True
                except:
                    pass

                time.sleep(1)
                print(f"   Attempt {attempt + 1}/{max_attempts}...")

            print("❌ Server failed to start within 30 seconds")
            return False

        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False

    def stop_server(self):
        """Stop the dashboard server."""
        if self.server_process:
            print("🛑 Stopping dashboard server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None

    def open_dashboard(self):
        """Open the dashboard in the default browser."""
        print(f"🌐 Opening dashboard: {self.server_url}")
        try:
            webbrowser.open(self.server_url)
            return True
        except Exception as e:
            print(f"⚠️  Could not open browser automatically: {e}")
            print(f"   Please open {self.server_url} manually")
            return False

    async def run_demo(self, demo_type="quick"):
        """Run the WebSocket demo."""
        print(f"🎬 Starting WebSocket demo: {demo_type}")

        try:
            demo_script = self.dashboard_dir / "demo_websocket.py"

            if not demo_script.exists():
                print(f"❌ Demo script not found: {demo_script}")
                return False

            # Run demo
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(demo_script), demo_type,
                cwd=str(self.dashboard_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # Stream output
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                print(line.decode().rstrip())

            await process.wait()
            return process.returncode == 0

        except Exception as e:
            print(f"❌ Failed to run demo: {e}")
            return False

    async def run_test(self):
        """Run the WebSocket tests."""
        print("🧪 Running WebSocket tests...")

        try:
            test_script = self.dashboard_dir / "websocket_test.py"

            if not test_script.exists():
                print(f"❌ Test script not found: {test_script}")
                return False

            # Run tests
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(test_script),
                cwd=str(self.dashboard_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            # Stream output
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                print(line.decode().rstrip())

            await process.wait()
            return process.returncode == 0

        except Exception as e:
            print(f"❌ Failed to run tests: {e}")
            return False

    def show_instructions(self):
        """Show usage instructions."""
        print("\n📋 WebSocket Dashboard Instructions")
        print("=" * 50)
        print(f"🌐 Dashboard URL: {self.server_url}")
        print("🔌 WebSocket Endpoint: ws://localhost:8080/ws")
        print("\n📡 Test WebSocket functionality:")
        print("   1. Open the dashboard URL in your browser")
        print("   2. Open browser developer tools (F12)")
        print("   3. Watch the Network tab for WebSocket connections")
        print("   4. Run pytest with: pytest --dashboard --dashboard-websocket")
        print("\n🎮 Manual testing:")
        print("   • Use the demo script for realistic test simulations")
        print("   • Check /api/websocket/status for connection info")
        print("   • Use /api/test/simulate-event for manual events")
        print("\n🛠️  Troubleshooting:")
        print("   • Check server logs for WebSocket connection info")
        print("   • Verify firewall allows port 8080")
        print("   • Test with: curl http://localhost:8080/api/health")

    async def interactive_mode(self):
        """Run in interactive mode with menu."""
        print("🎯 Django-Ollama WebSocket Dashboard Launcher")
        print("=" * 50)

        # Start server
        if not self.start_server():
            return False

        try:
            while True:
                print("\n📋 Available Actions:")
                print("   1. Open Dashboard in Browser")
                print("   2. Run Quick Demo")
                print("   3. Run Full Demo")
                print("   4. Run WebSocket Tests")
                print("   5. Show Instructions")
                print("   6. Exit")

                try:
                    choice = input("\n👉 Choose action (1-6): ").strip()
                except KeyboardInterrupt:
                    print("\n\n👋 Exiting...")
                    break

                if choice == "1":
                    self.open_dashboard()

                elif choice == "2":
                    print("\n" + "="*50)
                    await self.run_demo("quick")
                    print("="*50)

                elif choice == "3":
                    print("\n" + "="*50)
                    await self.run_demo("full")
                    print("="*50)

                elif choice == "4":
                    print("\n" + "="*50)
                    await self.run_test()
                    print("="*50)

                elif choice == "5":
                    self.show_instructions()

                elif choice == "6":
                    print("👋 Goodbye!")
                    break

                else:
                    print("❌ Invalid choice. Please enter 1-6.")

        finally:
            self.stop_server()

        return True

    async def quick_start(self):
        """Quick start: launch server, open browser, run demo."""
        print("⚡ Quick Start Mode")
        print("=" * 30)

        # Start server
        if not self.start_server():
            return False

        try:
            # Open browser
            self.open_dashboard()

            # Give user time to see dashboard
            print("\n⏳ Waiting 5 seconds for you to open the dashboard...")
            await asyncio.sleep(5)

            # Run quick demo
            await self.run_demo("quick")

            # Keep server running for a bit
            print("\n⏳ Server will stay running for 60 seconds...")
            print("   Use this time to explore the dashboard and WebSocket features.")
            await asyncio.sleep(60)

        finally:
            self.stop_server()

        return True


async def main():
    """Main launcher function."""
    launcher = DashboardLauncher()

    # Parse command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()

        if mode in ["quick", "fast", "q"]:
            success = await launcher.quick_start()
        elif mode in ["test", "tests", "t"]:
            if launcher.start_server():
                try:
                    success = await launcher.run_test()
                finally:
                    launcher.stop_server()
            else:
                success = False
        elif mode in ["demo", "d"]:
            demo_type = sys.argv[2] if len(sys.argv) > 2 else "quick"
            if launcher.start_server():
                try:
                    launcher.open_dashboard()
                    await asyncio.sleep(3)
                    success = await launcher.run_demo(demo_type)
                    await asyncio.sleep(10)  # Keep server running
                finally:
                    launcher.stop_server()
            else:
                success = False
        elif mode in ["help", "h", "-h", "--help"]:
            print("🎯 Django-Ollama WebSocket Dashboard Launcher")
            print("\nUsage:")
            print("  python launch_websocket_demo.py [mode]")
            print("\nModes:")
            print("  quick   - Quick start (launch, demo, exit)")
            print("  test    - Run WebSocket tests")
            print("  demo    - Run demo with dashboard")
            print("  help    - Show this help")
            print("  (none)  - Interactive mode")
            return 0
        else:
            print(f"❌ Unknown mode: {mode}")
            return 1
    else:
        # Interactive mode
        success = await launcher.interactive_mode()

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))
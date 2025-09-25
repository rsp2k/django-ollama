# 🚀 Quick Start Guide

Get the Django-Ollama Test Dashboard running in under 2 minutes!

## ⚡ Super Quick Start

```bash
# 1. Navigate to dashboard directory
cd /home/rpm/claude/django-ollama/test_dashboard/

# 2. Install dependencies (if needed)
pip install fastapi uvicorn

# 3. Generate demo data and start server
python launch_dashboard.py
```

🎉 **Done!** Your dashboard will be running at http://localhost:8080

## 🌐 Access Points

| URL | Description |
|-----|-------------|
| http://localhost:8080 | **Main Dashboard** - Beautiful overview with charts |
| http://localhost:8080/api/docs | **API Documentation** - Interactive Swagger UI |
| http://localhost:8080/api/health | **Health Check** - Server status |

## 📊 What You'll See

### Main Dashboard
- **Live Metrics**: Test runs, success rates, duration trends
- **Interactive Charts**: 7/30/90-day trend analysis
- **Recent Runs Table**: Latest test executions with details
- **Coverage Overview**: Code coverage visualization
- **Real-time Updates**: Auto-refresh every 30 seconds

### Features Highlights
- 🎨 **Beautiful Terminal Theme**: Gruvbox dark/light modes
- 📱 **Fully Responsive**: Works on mobile, tablet, desktop
- ♿ **Accessible**: WCAG compliant with keyboard navigation
- 🔍 **Interactive**: Search, filter, and drill-down capabilities
- 📄 **Print-friendly**: Professional report generation

## 🛠️ Advanced Usage

### Custom Database
```bash
# Use your own database file
python server.py --db /path/to/your/dashboard.db --port 8080
```

### Development Mode
```bash
# Run with auto-reload and debug logging
python server.py --reload --log-level debug
```

### Integration Example
```python
from test_dashboard import TestDashboardDB
from test_dashboard.models import TestResult, TestStatus

# Initialize database
db = TestDashboardDB("my_tests.db")

# Create test run
run_id = db.create_test_run(
    test_command="pytest tests/ -v",
    git_branch="main"
)

# Add test results (your test framework integration here)
result = TestResult(
    test_name="test_my_function",
    test_file="tests/test_example.py",
    test_method="test_my_function",
    status=TestStatus.PASSED,
    duration_seconds=1.23
)
db.add_test_result(run_id, result)

# Mark run as complete
db.update_test_run(run_id, status=TestStatus.PASSED)
```

## 🎯 Next Steps

1. **Integrate with your tests**: Add database calls to your test runner
2. **Customize styling**: Modify `/static/css/dashboard.css`
3. **Add features**: Extend `/server.py` with custom endpoints
4. **Configure deployment**: Set up reverse proxy for production

## 🆘 Troubleshooting

### Dependencies Missing?
```bash
pip install -r requirements.txt
```

### Port Already in Use?
```bash
python server.py --port 8081  # Use different port
```

### No Data Showing?
```bash
python demo_integration.py    # Generate sample data
```

### Database Issues?
```bash
rm demo_dashboard.db          # Reset database
python launch_dashboard.py    # Recreate with fresh data
```

## 📚 Learn More

- [Full Documentation](DASHBOARD_README.md)
- [Database Architecture](DATABASE_ARCHITECTURE.md)
- [API Examples](example_usage.py)
- [Integration Demo](demo_integration.py)

---

**Happy Testing!** 🧪 Need help? Check the logs or create an issue.
#!/bin/bash
# Install all dependencies for A2A Multi-Agent System

set -e

echo "=================================================="
echo "🔧 Installing A2A Multi-Agent System Dependencies"
echo "=================================================="

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install root dependencies
echo ""
echo "📦 Installing core dependencies..."
pip install -r requirements.txt

# Install agent-specific dependencies
echo ""
echo "📦 Installing agent dependencies..."

agents=(
    "intract-orchestrator"
    "orchestorator_agent"
    "code_logic_agent"
    "research_agent"
    "test_run_agents"
    "validation_agent"
    "shared"
)

for agent in "${agents[@]}"; do
    if [ -f "src/$agent/requirements.txt" ]; then
        echo "  → Installing $agent..."
        pip install -r "src/$agent/requirements.txt" -q
    fi
done

echo ""
echo "=================================================="
echo "✅ Installation Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "  1. Configure AWS credentials in .env file"
echo "  2. Run: ./run_all_agents.sh"
echo "  3. Visit: http://localhost:8006"
echo ""

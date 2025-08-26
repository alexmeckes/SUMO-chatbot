#!/bin/bash

echo "🚂 Railway Deployment Script for SUMO Chatbot"
echo "============================================="
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    brew install railway
else
    echo "✅ Railway CLI is installed"
fi

echo ""
echo "📝 Follow these steps:"
echo ""
echo "1. Login to Railway (will open browser):"
echo "   Run: railway login"
echo ""

echo "2. After logging in, initialize a new project:"
echo "   Run: railway init"
echo "   - Select 'Empty Project' when prompted"
echo ""

echo "3. Link to GitHub (for auto-deploy):"
echo "   Run: railway link"
echo "   - Select your new project from the list"
echo ""

echo "4. Set environment variables:"
cat << 'EOF'
   Run these commands:
   
   railway variables set OPENAI_API_KEY="your-openai-api-key-here"
   railway variables set OPENAI_MODEL="gpt-3.5-turbo"
   railway variables set PORT="8080"
   railway variables set FLASK_ENV="production"
   railway variables set CORS_ORIGIN="https://your-vercel-frontend.vercel.app"
EOF

echo ""
echo "5. Deploy the application:"
echo "   Run: railway up"
echo ""

echo "6. Get your deployment URL:"
echo "   Run: railway domain"
echo ""

echo "============================================="
echo "Quick copy-paste commands:"
echo ""
echo "# Login and create project"
echo "railway login"
echo "railway init"
echo ""
echo "# Link to existing project (if needed)"
echo "# railway link"
echo ""
echo "# Set all environment variables at once (replace with your values)"
echo 'railway variables set OPENAI_API_KEY="sk-..." OPENAI_MODEL="gpt-3.5-turbo" PORT="8080" FLASK_ENV="production" CORS_ORIGIN="https://your-app.vercel.app"'
echo ""
echo "# Deploy"
echo "railway up"
echo ""
echo "# Get domain"
echo "railway domain"
echo ""

echo "============================================="
echo "Alternative: Deploy from GitHub (Recommended)"
echo ""
echo "1. Login to Railway web dashboard: https://railway.app"
echo "2. Click 'New Project'"
echo "3. Select 'Deploy from GitHub repo'"
echo "4. Choose 'alexmeckes/SUMO-chatbot'"
echo "5. Add environment variables in the Railway dashboard"
echo "6. Railway will auto-deploy on every push to main"
echo ""
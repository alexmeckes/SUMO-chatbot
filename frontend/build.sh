#!/bin/bash
# Build script for Vercel to inject environment variables

# Replace placeholder with actual API URL
if [ ! -z "$VITE_API_URL" ]; then
    sed -i "s|VITE_API_URL_PLACEHOLDER|$VITE_API_URL|g" config.js
    echo "✅ API URL configured: $VITE_API_URL"
else
    echo "⚠️ VITE_API_URL not set, using default"
fi

echo "Build complete!"
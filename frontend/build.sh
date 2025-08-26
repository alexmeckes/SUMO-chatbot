#!/bin/bash
# Build script for Vercel to inject environment variables

# Replace placeholder with actual API URL
if [ ! -z "$VITE_API_URL" ]; then
    # Use sed that works on both Linux (Vercel) and macOS
    sed -i.bak "s|VITE_API_URL_PLACEHOLDER|$VITE_API_URL|g" config.js && rm -f config.js.bak
    echo "✅ API URL configured: $VITE_API_URL"
    echo "✅ Config file content:"
    cat config.js
else
    echo "⚠️ VITE_API_URL not set, using default"
fi

echo "Build complete!"
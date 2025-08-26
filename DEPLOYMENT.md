# SUMO Chatbot Deployment Guide

This guide will walk you through deploying the SUMO Chatbot with Railway (backend) and Vercel (frontend).

## Architecture Overview

- **Backend**: Flask API deployed on Railway
- **Frontend**: Static HTML/JS deployed on Vercel
- **Database**: ChromaDB (embedded in backend)

## Prerequisites

- GitHub account with your repository
- Railway account (https://railway.app)
- Vercel account (https://vercel.com)
- OpenAI API key

## Backend Deployment (Railway)

### Step 1: Create Railway Project

1. Go to [Railway](https://railway.app) and sign in
2. Click "New Project"
3. Choose "Deploy from GitHub repo"
4. Select your `SUMO-chatbot` repository
5. Railway will auto-detect the configuration

### Step 2: Configure Environment Variables

In Railway dashboard, add these environment variables:

```bash
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo
PORT=8080
FLASK_ENV=production
CORS_ORIGIN=https://your-vercel-app.vercel.app  # Update after Vercel deployment
```

### Step 3: Deploy

1. Railway will automatically deploy when you push to main
2. Get your deployment URL from Railway (e.g., `https://sumo-chatbot.up.railway.app`)

## Frontend Deployment (Vercel)

### Step 1: Create Vercel Project

1. Go to [Vercel](https://vercel.com) and sign in
2. Click "Add New Project"
3. Import your GitHub repository
4. Set the root directory to `frontend`

### Step 2: Configure Build Settings

In Vercel project settings:

- **Framework Preset**: Other
- **Build Command**: `echo 'No build needed'`
- **Output Directory**: `.`
- **Install Command**: Leave empty

### Step 3: Configure Environment Variables

Add this environment variable in Vercel:

```bash
VITE_API_URL=https://your-railway-app.up.railway.app  # Your Railway backend URL
```

### Step 4: Deploy

1. Click "Deploy"
2. Get your deployment URL (e.g., `https://sumo-chatbot.vercel.app`)

### Step 5: Update Backend CORS

Go back to Railway and update the `CORS_ORIGIN` environment variable:

```bash
CORS_ORIGIN=https://sumo-chatbot.vercel.app
```

## Local Development

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your OpenAI API key

# Run the backend
python app_multiturn.py
```

### Frontend

```bash
# Serve the frontend locally
cd frontend
python -m http.server 3000
# Open http://localhost:3000
```

## Testing the Deployment

1. Visit your Vercel frontend URL
2. Check the status indicator (should show "Online" or your model name)
3. Try sending a message
4. Check Railway logs if there are issues

## Troubleshooting

### Backend Issues

1. **Check Railway logs**: Dashboard → Your Project → Deployments → View Logs
2. **Common issues**:
   - Missing environment variables
   - OpenAI API key invalid
   - Port configuration issues

### Frontend Issues

1. **Check Vercel logs**: Dashboard → Your Project → Functions → Logs
2. **Common issues**:
   - CORS errors: Update `CORS_ORIGIN` in Railway
   - API URL not configured: Check `VITE_API_URL` in Vercel
   - Network errors: Ensure backend is running

### CORS Issues

If you see CORS errors in the browser console:

1. Ensure `CORS_ORIGIN` in Railway matches your Vercel URL exactly
2. Restart the Railway deployment after updating environment variables
3. Check that the frontend is using the correct API URL

## Monitoring

### Railway
- Monitor usage in Railway dashboard
- Set up alerts for downtime
- Check logs regularly for errors

### Vercel
- Monitor in Vercel dashboard
- Check Analytics for usage patterns
- Review Function logs for API endpoint issues

## Scaling

### Railway
- Adjust replica count in Railway settings
- Monitor memory/CPU usage
- Consider upgrading plan for more resources

### Vercel
- Frontend scales automatically
- Monitor bandwidth usage
- Consider Pro plan for higher limits

## Security Best Practices

1. **Never commit API keys** to the repository
2. **Use environment variables** for all sensitive data
3. **Enable HTTPS** (automatic on both Railway and Vercel)
4. **Restrict CORS** to your specific frontend domain
5. **Rotate API keys** regularly
6. **Monitor usage** for unusual patterns

## Updating the Application

### Backend Updates

```bash
git add .
git commit -m "Update backend"
git push origin main
# Railway auto-deploys
```

### Frontend Updates

```bash
git add frontend/
git commit -m "Update frontend"
git push origin main
# Vercel auto-deploys
```

## Cost Considerations

### Railway
- Free tier: $5/month credit
- Paid plans start at $20/month
- Pay for compute time and memory

### Vercel
- Free tier: Good for personal projects
- Pro: $20/month per user
- Pay for bandwidth and function invocations

### OpenAI
- Pay per API usage
- GPT-3.5-turbo: ~$0.002 per 1K tokens
- Monitor usage in OpenAI dashboard

## Support

For issues:
1. Check the logs in Railway and Vercel
2. Review environment variables
3. Test locally first
4. Check GitHub issues for similar problems

## Next Steps

1. Set up monitoring and alerts
2. Implement rate limiting
3. Add authentication if needed
4. Set up a custom domain
5. Implement caching for better performance
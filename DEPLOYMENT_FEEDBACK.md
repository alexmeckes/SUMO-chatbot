# Deploying Feedback System to Production

## Railway Setup with Persistent Volume

The feedback system uses SQLite for storage, which requires persistent storage on Railway.

### Step 1: Add Persistent Volume to Railway

1. Go to your Railway project dashboard
2. Click on your service (sumo-chatbot)
3. Go to the **Settings** tab
4. Scroll down to **Volumes**
5. Click **+ New Volume**
6. Configure the volume:
   - **Mount path**: `/data`
   - **Size**: 1GB (or adjust as needed)
7. Click **Add Volume**

### Step 2: Set Environment Variables

In Railway dashboard, add these environment variables:

```bash
# Required
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-3.5-turbo

# Optional - for custom database path
FEEDBACK_DB_PATH=/data/feedback.db

# Set production flag
PRODUCTION=true
```

### Step 3: Deploy

The application will automatically:
- Create the SQLite database at `/data/feedback.db`
- Create backup directory at `/data/feedback_backups/`
- Persist data across deployments

### Step 4: Verify Deployment

1. Check the deployment logs in Railway for:
   ```
   📊 Initializing feedback database at: /data/feedback.db
   💾 Backup directory: /data/feedback_backups
   ```

2. Test the feedback system:
   - Visit your deployed frontend
   - Send a message to the chatbot
   - Click the feedback buttons (👍/👎)
   - Check feedback stats: `https://your-railway-url.up.railway.app/api/feedback/stats`

## Vercel Frontend Configuration

The frontend is already configured to work with the feedback system. Make sure:

1. `frontend/config.js` has the correct Railway URL:
   ```javascript
   window.CONFIG = {
     API_URL: 'https://your-railway-url.up.railway.app'
   };
   ```

2. Deploy to Vercel:
   ```bash
   cd frontend
   vercel --prod
   ```

## Testing Feedback in Production

```bash
# Test feedback endpoints
curl -X POST https://your-railway-url.up.railway.app/api/session

# Get feedback statistics
curl https://your-railway-url.up.railway.app/api/feedback/stats
```

## Monitoring & Maintenance

### View Feedback Statistics
```python
# SSH into Railway or use Railway CLI
railway run python -c "
from feedback_manager_production import get_feedback_manager
fm = get_feedback_manager()
stats = fm.get_feedback_stats(7)
print(stats)
"
```

### Backup Database
The database is automatically backed up to `/data/feedback_backups/` when it reaches 100MB.

### Download Database
Use Railway CLI to download the database:
```bash
railway run cat /data/feedback.db > local_feedback_backup.db
```

## Troubleshooting

### Issue: Database not persisting
- **Solution**: Ensure volume is mounted at `/data`
- Check Railway logs for database initialization messages

### Issue: CORS errors from frontend
- **Solution**: Verify `CORS_ORIGIN` env var matches your Vercel URL
- Or keep it as `*` for development

### Issue: Feedback buttons not appearing
- **Solution**: Check browser console for session creation
- Ensure `/api/session` endpoint is accessible

## Alternative: Use Supabase (Week 3 Plan)

If you need more robust storage or analytics, consider migrating to Supabase:
1. Free tier includes 500MB database
2. Built-in REST API
3. Real-time subscriptions
4. Better for production scale

## Summary

✅ **Production Deployment Checklist:**
- [ ] Add persistent volume to Railway at `/data`
- [ ] Set environment variables (OPENAI_API_KEY, PRODUCTION)
- [ ] Deploy to Railway
- [ ] Verify database initialization in logs
- [ ] Test feedback from frontend
- [ ] Check feedback statistics endpoint
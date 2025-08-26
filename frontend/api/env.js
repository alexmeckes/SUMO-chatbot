// This serverless function provides environment variables to the frontend
export default function handler(req, res) {
  res.status(200).json({
    VITE_API_URL: process.env.VITE_API_URL || ''
  });
}
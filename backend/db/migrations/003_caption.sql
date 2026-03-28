-- Optional Instagram post caption (yt-dlp); used with transcript for better tool names.
ALTER TABLE videos ADD COLUMN IF NOT EXISTS caption TEXT;

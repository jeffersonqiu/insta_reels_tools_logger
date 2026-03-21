-- Run in Supabase SQL Editor after 001_initial.sql
ALTER TABLE videos ADD COLUMN IF NOT EXISTS processing_error TEXT;

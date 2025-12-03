import { createClient } from '@supabase/supabase-js';
import { config } from './config.js';

export const supabase = createClient(config.supabaseUrl, config.supabaseKey, {
  auth: {
    persistSession: false,
    autoRefreshToken: false
  },
  db: {
    schema: config.supabaseSchema
  },
  global: {
    headers: {
      'x-application-name': 'corsa-api'
    }
  }
});

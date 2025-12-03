import { config as loadEnv } from 'dotenv';
import { existsSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';

const __dirname = dirname(fileURLToPath(import.meta.url));
const loadEnvIfExists = (path: string) => {
  if (existsSync(path)) {
    loadEnv({ path, override: true });
  }
};

const projectRoot = resolve(__dirname, '../../..');
const apiRoot = resolve(__dirname, '..');
const rootEnv = resolve(projectRoot, '.env');
const rootLocalEnv = resolve(projectRoot, '.env.local');
const apiEnv = resolve(apiRoot, '.env');

loadEnvIfExists(rootEnv);
loadEnvIfExists(rootLocalEnv);
loadEnvIfExists(apiEnv);

const envSchema = z.object({
  SUPABASE_URL: z.string().url(),
  SUPABASE_SERVICE_ROLE_KEY: z.string().min(1),
  SUPABASE_SCHEMA: z
    .enum(['public', 'graphql_public', 'raw'])
    .optional()
    .transform((value) => value ?? 'public'),
  LISTINGS_TABLE: z.string().min(1).default('listings').transform((value) => value || 'listings'),
  PORT: z.string().optional(),
  ALLOWED_ORIGIN: z.string().optional()
});

const parsed = envSchema.parse(process.env);

export const config = {
  supabaseUrl: parsed.SUPABASE_URL,
  supabaseKey: parsed.SUPABASE_SERVICE_ROLE_KEY,
  supabaseSchema: parsed.SUPABASE_SCHEMA,
  listingsTable: parsed.LISTINGS_TABLE,
  port: Number(parsed.PORT ?? 4000),
  allowedOrigin: parsed.ALLOWED_ORIGIN ?? '*'
};

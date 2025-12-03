import cors from 'cors';
import express, { NextFunction, Request, Response } from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import { config } from './config.js';
import { apiRouter } from './routes/index.js';

const app = express();

app.use(helmet());
app.use(
  cors({
    origin: config.allowedOrigin === '*' ? undefined : config.allowedOrigin
  })
);
app.use(express.json({ limit: '1mb' }));
app.use(morgan('dev'));

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.use('/api', apiRouter);

app.use((_req, res) => {
  res.status(404).json({ message: 'Route not found' });
});

app.use((error: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error(error);
  res.status(500).json({ message: error.message || 'Unexpected server error' });
});

app.listen(config.port, () => {
  console.log(`API server listening on http://localhost:${config.port}`);
});

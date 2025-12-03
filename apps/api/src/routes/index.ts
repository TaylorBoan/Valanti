import { Router } from 'express';
import { metricsRouter } from './metrics.js';
import { modelsRouter } from './models.js';

export const apiRouter = Router();

apiRouter.use('/models', modelsRouter);
apiRouter.use('/metrics', metricsRouter);

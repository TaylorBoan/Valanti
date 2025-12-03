import { Router } from 'express';
import { getSummaryMetrics } from '../services/listings.js';

export const metricsRouter = Router();

metricsRouter.get('/summary', async (_req, res, next) => {
  try {
    const metrics = await getSummaryMetrics();
    res.json(metrics);
  } catch (error) {
    next(error);
  }
});

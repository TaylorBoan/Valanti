import { Router } from 'express';
import { getSummaryMetrics } from '../services/listings.js';

export const metricsRouter = Router();

metricsRouter.get('/summary', async (req, res, next) => {
  try {
    const modelKey = typeof req.query.modelKey === 'string' ? req.query.modelKey : undefined;
    const metrics = await getSummaryMetrics(modelKey);
    res.json(metrics);
  } catch (error) {
    next(error);
  }
});

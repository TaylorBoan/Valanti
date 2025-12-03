import { Router } from 'express';
import { getPriceHistoryForModel, listModels } from '../services/listings.js';

export const modelsRouter = Router();

modelsRouter.get('/', async (_req, res, next) => {
  try {
    const models = await listModels();
    res.json({ data: models });
  } catch (error) {
    next(error);
  }
});

modelsRouter.get('/:key/price-history', async (req, res, next) => {
  try {
    const { key } = req.params;
    const history = await getPriceHistoryForModel(key);
    res.json(history);
  } catch (error) {
    if (error instanceof Error && error.message.startsWith('Unknown model')) {
      res.status(404).json({ message: error.message });
      return;
    }

    next(error);
  }
});

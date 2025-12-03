import { ModelDefinition } from '../types/index.js';

const slugify = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');

const makeModel = (make: string, label: string, pattern?: string): ModelDefinition => ({
  key: slugify(`${make}-${label}`),
  make,
  label,
  filters: [
    { column: 'make', operator: 'eq', value: make },
    { column: 'model', operator: 'ilike', value: pattern ?? `${label}%` }
  ]
});

export const modelDefinitions: ModelDefinition[] = [
  makeModel('McLaren', '650S', '650%'),
  makeModel('McLaren', '720S', '720%'),
  makeModel('McLaren', 'GT'),
  makeModel('McLaren', 'Artura'),
  makeModel('McLaren', '765LT', '765%'),
  makeModel('McLaren', 'Senna'),
  makeModel('McLaren', 'Elva'),
  makeModel('McLaren', 'Speedtail'),
  makeModel('McLaren', 'P1'),
  makeModel('McLaren', '570S', '570%'),
  makeModel('McLaren', '600LT', '600%'),
  makeModel('Porsche', '911 Turbo S', '911 Turbo%'),
  makeModel('Porsche', '911 GT3 RS', '911 GT3%'),
  makeModel('Porsche', '911 Targa', '911 Targa%'),
  makeModel('Porsche', '911 Carrera GTS', '911 Carrera%'),
  makeModel('Porsche', '918'),
  makeModel('Bugatti', 'Chiron'),
  makeModel('Bugatti', 'Veyron'),
  makeModel('Bugatti', 'Divo'),
  makeModel('Bugatti', 'Bolide'),
  makeModel('Aston Martin', 'Vantage'),
  makeModel('Aston Martin', 'DB11'),
  makeModel('Aston Martin', 'Superleggera'),
  makeModel('Aston Martin', 'Vanquish'),
  makeModel('Aston Martin', 'Valkyrie'),
  makeModel('Pagani', 'Zonda'),
  makeModel('Pagani', 'Huayra'),
  makeModel('Pagani', 'Roadster'),
  makeModel('Koenigsegg', 'Agera'),
  makeModel('Koenigsegg', 'Jesko'),
  makeModel('Koenigsegg', 'Regera'),
  makeModel('Audi', 'R8'),
  makeModel('Dodge', 'Viper'),
  makeModel('Ford', 'GT'),
  makeModel('Mercedes-AMG', 'GTR', 'GTR'),
  makeModel('Mercedes-AMG', 'SLS', 'SLS'),
  makeModel('Nissan', 'GTR', 'GTR'),
  makeModel('Acura', 'NSX'),
  makeModel('Lamborghini', 'Huracan'),
  makeModel('Lamborghini', 'Aventador', 'Aventador%'),
  makeModel('Lamborghini', 'Aventador SV', 'Aventador%'),
  makeModel('Lamborghini', 'Aventador SVJ', 'Aventador%'),
  makeModel('Lamborghini', 'Gallardo'),
  makeModel('Lamborghini', 'Urus'),
  makeModel('Lamborghini', 'Murcielago'),
  makeModel('Lamborghini', 'Sian'),
  makeModel('Lamborghini', 'Countach'),
  makeModel('Ferrari', '458'),
  makeModel('Ferrari', '488 Pista', '488%'),
  makeModel('Ferrari', '812'),
  makeModel('Ferrari', 'SF90'),
  makeModel('Ferrari', 'LaFerrari'),
  makeModel('Ferrari', 'California'),
  makeModel('Ferrari', 'F430'),
  makeModel('Ferrari', 'F8'),
  makeModel('Ferrari', 'Portofino'),
  makeModel('Ferrari', 'Roma')
];

export const getModelByKey = (key: string) => modelDefinitions.find((definition) => definition.key === key);

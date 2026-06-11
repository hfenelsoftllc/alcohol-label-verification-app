// The six TTB label fields compared between the label image and the
// application data, plus the Government Warning (checked separately, exactly
// — see GovernmentWarningCheck). Keys match `LABEL_FIELD_NAMES` in
// backend/app/models.py and the `field` values on each FieldComparison.
export const COMPARISON_FIELDS = [
  { key: 'brand', label: 'Brand Name' },
  { key: 'class_type', label: 'Class / Type' },
  { key: 'abv', label: 'Alcohol Content' },
  { key: 'net_contents', label: 'Net Contents' },
  { key: 'name_address', label: 'Name & Address' },
  { key: 'country_of_origin', label: 'Country of Origin' },
];

export const GOVERNMENT_WARNING_LABEL = 'Government Warning';

// Fields rendered on the application data form, in order.
export const APPLICATION_FORM_FIELDS = [
  ...COMPARISON_FIELDS.map((field) => ({ ...field, type: 'text' })),
  { key: 'government_warning', label: GOVERNMENT_WARNING_LABEL, type: 'textarea' },
];

// Mirrors the `max_length` constraints on ApplicationData in
// backend/app/models.py.
export const FIELD_MAX_LENGTH = {
  brand: 255,
  class_type: 255,
  abv: 64,
  net_contents: 64,
  name_address: 512,
  country_of_origin: 255,
  government_warning: 2000,
};

export const FIELD_PLACEHOLDERS = {
  abv: 'e.g. 40% Alc. by Vol.',
  net_contents: 'e.g. 750 mL',
};

// The standard 27 CFR 16.21 text — most applications use this verbatim, so
// it's pre-filled and editable rather than left for the user to retype.
export const DEFAULT_GOVERNMENT_WARNING =
  'GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink alcoholic ' +
  'beverages during pregnancy because of the risk of birth defects. (2) Consumption of alcoholic ' +
  'beverages impairs your ability to drive a car or operate machinery, and may cause health problems.';

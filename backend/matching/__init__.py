"""Label-vs-application matching package.

`engine.compare` is the entry point: it scores extracted label fields against
the submitted application data using fuzzy matching for text fields and
numeric tolerance for ABV and Net Contents.

`exact_validator.validate_government_warning` separately validates the
Government Warning, which must match the application data verbatim.
"""
